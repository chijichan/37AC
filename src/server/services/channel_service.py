# services/channel_service.py
"""多通道识别结果（37ac / llm / human）的解析、合并与状态判定。

设计（2026-09-25 与需求方确认）：
- **一个上传入口**（POST /upload），一次请求可请求多个通道：channels=37ac,llm,human
- 结果按通道**分段存放**在 task_results.result 里：result["37ac"] / result["llm"] / result["human"]，
  前端分区域展示，不做加权融合
- 人工通道：可在上传请求里内联提交（human_name），也可稍后由匿名页面补投（POST /upload/human）
- 兼容：顶层仍保留旧字段（success/class_probs/characters/crop_method/image），取值 37ac 优先、其次 llm

节点任务 id：单通道时沿用父 task_id；多通道时用 "<父id>:<通道>"（例：abc-123:llm），
节点只当它是普通 id，服务端收到结果后按前缀拆回父任务。
"""

import threading
import time

CHANNEL_37AC = "37ac"
CHANNEL_LLM = "llm"
CHANNEL_HUMAN = "human"

# 会走节点推理的通道（human 由人提交，不经节点）
NODE_CHANNELS = (CHANNEL_37AC, CHANNEL_LLM)
ALL_CHANNELS = (CHANNEL_37AC, CHANNEL_LLM, CHANNEL_HUMAN)

CHANNEL_TO_RECOGNITION = {CHANNEL_37AC: "local", CHANNEL_LLM: "llm"}
RECOGNITION_TO_CHANNEL = {"local": CHANNEL_37AC, "llm": CHANNEL_LLM}
CHANNEL_TO_MODEL = {CHANNEL_37AC: "37ac", CHANNEL_LLM: "llm"}

# 结果里的「回退」标记：节点被要求走某个通道，但实际用的是另一种推理方式
FALLBACK_KEY = "fallback"

_ALIASES = {
    "37ac": CHANNEL_37AC,
    "local": CHANNEL_37AC,
    "resnet": CHANNEL_37AC,
    "llm": CHANNEL_LLM,
    "human": CHANNEL_HUMAN,
    "manual": CHANNEL_HUMAN,
    "人工": CHANNEL_HUMAN,
    "人": CHANNEL_HUMAN,
}

# 顶层兼容字段：从主通道结果里透传
LEGACY_KEYS = (
    "success", "class_probs", "characters", "character_count",
    "crop_method", "image", "recognition_type", "features_used", "yolo_detected",
)

_SEP = ":"


def parse_channels(raw=None, model=None):
    """解析请求里的通道列表。

    - raw 形如 "37ac,llm,human"（也兼容中文逗号与空格、别名 local/manual）
    - 未给 raw 时按旧参数 model 推导：37ac -> [37ac]，llm -> [llm]，auto -> [auto]（保持旧分流行为）
    返回去重后的通道列表；无法识别时回退 ["37ac"]。
    """
    if raw:
        text = str(raw).replace("，", ",")
        picked = []
        for piece in text.split(","):
            key = piece.strip().lower()
            if not key:
                continue
            channel = _ALIASES.get(key)
            if channel and channel not in picked:
                picked.append(channel)
        if picked:
            return picked

    legacy = (model or "").strip().lower()
    if legacy == "llm":
        return [CHANNEL_LLM]
    if legacy == "auto":
        return ["auto"]          # 让节点按自身能力分流（旧行为）
    return [CHANNEL_37AC]


def node_channels(channels):
    """从通道列表里挑出需要发给节点的通道。"""
    return [c for c in channels if c in NODE_CHANNELS]


def sub_task_id(task_id, channel, total_node_channels):
    """多通道时给节点任务 id 加通道后缀，避免与父任务/其它通道互相覆盖。"""
    if total_node_channels <= 1:
        return task_id
    return f"{task_id}{_SEP}{channel}"


def split_task_id(raw_task_id):
    """把节点回来的 task_id 拆成 (父 task_id, 通道)。无后缀时通道为 None。"""
    text = str(raw_task_id or "")
    if _SEP in text:
        parent, _, suffix = text.rpartition(_SEP)
        channel = _ALIASES.get(suffix.strip().lower())
        if parent and channel in NODE_CHANNELS:
            return parent, channel
    return text, None


def initial_result(task_id, channels):
    """新建任务时的 result 骨架：三个通道各自的状态占位。"""
    payload = {
        "task_id": task_id,
        "requested_channels": list(channels),
    }
    for channel in channels:
        if channel == CHANNEL_HUMAN:
            payload[CHANNEL_HUMAN] = {"status": "awaiting", "votes": []}
        elif channel in NODE_CHANNELS:
            payload[channel] = {"status": "queued"}
        else:
            payload[channel] = {"status": "queued"}     # auto 等透传通道
    return payload


def human_entry(name, character_index=None, bbox=None, bbox_percent=None,
                note=None, source="upload", voter=None):
    """构造人工通道的一条标注。"""
    entry = {
        "name": str(name or "").strip(),
        "status": "completed",
        "source": source,
        "at": int(time.time()),
    }
    if character_index is not None:
        try:
            entry["character_index"] = int(character_index)
        except (TypeError, ValueError):
            pass
    if isinstance(bbox, dict):
        entry["bbox"] = bbox
    if isinstance(bbox_percent, dict):
        entry["bbox_percent"] = bbox_percent
    if note:
        entry["note"] = str(note)[:200]
    if voter:
        entry["voter"] = voter
    return entry


def add_human_vote(payload, entry, voter_key=None):
    """把一条人工标注写进 payload["human"]；同一 voter 重复提交则覆盖（可改票）。"""
    section = payload.get(CHANNEL_HUMAN)
    if not isinstance(section, dict):
        section = {"status": "completed", "votes": []}
    votes = [v for v in (section.get("votes") or []) if isinstance(v, dict)]

    if voter_key:
        votes = [v for v in votes if v.get("voter") != voter_key]
        entry = dict(entry)
        entry["voter"] = voter_key

    votes.append(entry)
    votes.sort(key=lambda v: v.get("at") or 0)
    section["votes"] = votes
    section["status"] = "completed"
    section["count"] = len(votes)
    payload[CHANNEL_HUMAN] = section
    return payload


def set_human_votes(payload, entries, voter_key=None):
    """用一整套人工标注替换某个 voter 之前的票（支持"一张图多个角色"）。

    - entries：本次提交的角色列表，每项由 human_entry() 构造
    - voter_key 非空时：先删掉该 voter 在此任务上的全部旧票，再整批写入
      （语义：某个浏览器对某张图的标注集合 = 它最后一次提交的内容，仍算改票）
    - 未给 voter_key 时按追加处理
    """
    section = payload.get(CHANNEL_HUMAN)
    if not isinstance(section, dict):
        section = {"status": "completed", "votes": []}
    votes = [v for v in (section.get("votes") or []) if isinstance(v, dict)]

    if voter_key:
        votes = [v for v in votes if v.get("voter") != voter_key]

    for entry in entries or []:
        item = dict(entry)
        if voter_key:
            item["voter"] = voter_key
        votes.append(item)

    votes.sort(key=lambda v: (v.get("voter") or "", v.get("at") or 0))
    section["votes"] = votes
    section["count"] = len(votes)
    section["status"] = "completed" if votes else "awaiting"
    payload[CHANNEL_HUMAN] = section
    payload["human"] = section
    return payload


def expected_recognition(channel):
    """该通道本来应该用哪种推理方式（37ac→local，llm→llm）。"""
    return CHANNEL_TO_RECOGNITION.get(channel)


def resolve_result_channel(parent_id, raw_task_id, payload=None, reported_channel=None,
                           assigned_tasks=None, inferred_type=None):
    """判定节点回传的结果属于哪个通道。

    生产环境里网络抖动可能让节点回传的 id 丢掉 "<父id>:<通道>" 后缀，或把同一个结果
    重复回传；以前是直接按 recognition_type 猜通道，猜错就会把 37ac 的结果写进 llm
    （表现为两个通道一模一样的概率）。这里按可靠性依次判定，并且**任何一步都必须落在
    requested_channels 里**，否则返回 None —— 调用方应当丢弃并记日志，绝不能硬塞。

    判定顺序：
      1) task_id 自带的后缀（最可靠，节点原样回传）
      2) 节点消息里显式上报的 channel
      3) 该节点上分配给这个父任务的子任务（只对应唯一通道时）
      4) 父任务只请求了一个节点通道
      5) 最后才按 recognition_type 推断，且必须是唯一对应的通道
    """
    payload = payload if isinstance(payload, dict) else {}
    requested_all = payload.get("requested_channels")
    requested = [c for c in (requested_all or []) if c in NODE_CHANNELS]
    if isinstance(requested_all, list) and requested_all and not requested:
        # 只请求了人工通道：节点结果没有归属，直接丢弃
        return None

    def accept(channel):
        if not channel or channel not in NODE_CHANNELS:
            return None
        if requested and channel not in requested:
            return None
        return channel

    _, suffix_channel = split_task_id(raw_task_id)
    if suffix_channel:
        return accept(suffix_channel)

    reported = _ALIASES.get(str(reported_channel or "").strip().lower())
    if reported:
        return accept(reported)

    found = set()
    for tid in (assigned_tasks or []):
        pid, ch = split_task_id(tid)
        if pid == parent_id and ch:
            found.add(ch)
    if len(found) == 1:
        return accept(next(iter(found)))

    if len(requested) == 1:
        return requested[0]

    if inferred_type:
        wanted = str(inferred_type).strip().lower()
        matches = [c for c in (requested or list(NODE_CHANNELS))
                   if CHANNEL_TO_RECOGNITION.get(c) == wanted]
        if len(matches) == 1:
            return accept(matches[0])
    return None


def is_duplicate_channel_result(payload, channel, node_result):
    """同一通道的结果重复回传（节点重试/网络重发）→ 视为重复。

    已经 completed 且识别方式与结果完全一致时返回 True，调用方应忽略这次回传，
    避免重复合并（更避免重复结果被误判到别的通道）。
    """
    section = (payload or {}).get(channel)
    if not isinstance(section, dict) or section.get("status") != "completed":
        return False
    incoming = node_result or {}
    if (incoming.get("recognition_type") or None) != (section.get("recognition_type") or None):
        return False
    if bool(incoming.get("success")) != bool(section.get("success")):
        return False
    return ((incoming.get("class_probs") or []) == (section.get("class_probs") or [])
            and (incoming.get("characters") or []) == (section.get("characters") or []))


def merge_channel_result(payload, channel, node_result):
    """把节点回传的通道结果写进 payload，并维护顶层兼容字段。"""
    payload = payload if isinstance(payload, dict) else {}
    section = dict(node_result or {})
    section["status"] = "completed"
    section["submitted_at"] = int(time.time())

    # 节点实际用的推理方式与通道本来该用的不一致 → 记下回退，别让人以为是这个通道自己的结果
    expected = expected_recognition(channel)
    actual = str(section.get("recognition_type") or "").strip().lower() or None
    if expected and actual and actual != expected:
        section[FALLBACK_KEY] = {
            "requested": expected,
            "actual": actual,
        }
    else:
        section.pop(FALLBACK_KEY, None)

    payload[channel] = section

    requested = payload.get("requested_channels") or []
    if channel not in requested:
        payload["requested_channels"] = requested + [channel]

    # 顶层兼容字段：37ac 优先；若 37ac 不在本次请求里，则由 llm 填
    primary = CHANNEL_37AC if CHANNEL_37AC in (payload.get("requested_channels") or []) else CHANNEL_LLM
    if channel == primary or "characters" not in payload:
        for key in LEGACY_KEYS:
            if key in section:
                payload[key] = section[key]
    return payload


def channel_status(payload, channel):
    section = (payload or {}).get(channel)
    if not isinstance(section, dict):
        return "missing"
    return section.get("status") or "unknown"


def overall_status(payload):
    """整体状态：node 通道都完成 -> completed；完成一部分 -> partial；都没完成 -> pending。"""
    payload = payload or {}
    requested = [c for c in (payload.get("requested_channels") or []) if c in NODE_CHANNELS]
    if not requested:
        # 只有人工通道
        human = payload.get(CHANNEL_HUMAN) or {}
        if (human.get("votes") or human.get("name")):
            return "completed"
        return "pending"
    done = [c for c in requested if channel_status(payload, c) == "completed"]
    if len(done) == len(requested):
        return "completed"
    if done:
        return "partial"
    if any(channel_status(payload, c) in ("waiting", "queued") for c in requested):
        return "pending"
    return "failed"


def resolve_human_bbox(payload):
    """读时补全：人工标注只给了 character_index 时，从模型通道的 characters 里取框。"""
    payload = payload or {}
    section = payload.get(CHANNEL_HUMAN)
    if not isinstance(section, dict):
        return payload

    source_characters = None
    for channel in (CHANNEL_37AC, CHANNEL_LLM):
        candidate = (payload.get(channel) or {}).get("characters")
        if candidate:
            source_characters = candidate
            break

    changed = False
    for vote in (section.get("votes") or []):
        if not isinstance(vote, dict) or vote.get("bbox") or vote.get("character_index") is None:
            continue
        index = vote["character_index"]
        if source_characters and 0 <= index < len(source_characters):
            item = source_characters[index] or {}
            vote["bbox"] = item.get("bbox")
            vote["bbox_percent"] = item.get("bbox_percent")
            if item.get("class_probs"):
                vote["model_guess"] = item["class_probs"][0].get("name")
            changed = True
    if changed:
        payload[CHANNEL_HUMAN] = section
        payload["human"] = section
    return payload


# ------------------------------------------------------------------
# 匿名投票的按 IP 限流（内存滑动窗口）
# ------------------------------------------------------------------

_vote_windows = {}
_vote_lock = threading.Lock()
_vote_cleanup_at = [0.0]


def vote_allowed(ip, limit_per_hour):
    """按 IP 限制人工投票次数（默认每小时 limit_per_hour 次）。limit<=0 表示不限。"""
    if not limit_per_hour or limit_per_hour <= 0:
        return True
    now = time.time()
    window_start = now - 3600
    with _vote_lock:
        from collections import deque
        bucket = _vote_windows.setdefault(ip or "unknown", deque())
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= limit_per_hour:
            return False
        bucket.append(now)

        # 顺手清理长时间不活跃的 key，避免内存无限增长
        if now - _vote_cleanup_at[0] > 600:
            _vote_cleanup_at[0] = now
            for key in [k for k, v in _vote_windows.items() if not v or v[-1] < window_start]:
                _vote_windows.pop(key, None)
    return True
