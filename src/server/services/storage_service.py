# services/storage_service.py
"""图片缓存与临时文件系统。

目录布局（默认值，可在 .env 或后台「系统设置」覆盖）：

    saves/tmp     上传原图（在途/短期；任务完成或超时后按 TTL 清理）
    saves/cache   留存副本（不需要压缩就原样存，需要压缩则存 JPEG）

回收策略（tmp / cache 各自独立，按容量上限）：

    1) 过期清理：mtime 早于 TTL 的删除（tmp 中保护窗口内的新文件不动，避免删掉在途任务）
    2) 优先压缩：仍超限 -> 压缩「最长边 > image_compress_max_side」的最大文件
    3) 按权重淘汰：仍超限 -> weight = size * exp(-age / half_life), half_life = max(60, ttl/2)
       升序删除（越老权重越低 -> 先删旧文件；同年龄下大文件权重更高 -> 优先靠压缩解决）

文件命名：<task_id><ext>；task_id 只允许 [A-Za-z0-9._-]，杜绝目录穿越。
"""

import io
import math
import re
import threading
import time
from pathlib import Path

from PIL import Image

from config import base as cfg
from config.log_config import get_logger
from services import settings_service

logger = get_logger("storage_service")

# 只接受这类文件名（task_id 是 uuid，扩展名白名单与上传校验保持一致）
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_ALLOWED_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".gif": "image/gif",
}

# 目录名 -> (配置路径属性, 容量上限键, TTL 键, 是否保护新文件)
_DIRS = {
    "tmp": ("IMAGE_TMP_PATH", "image_tmp_max_mb", "image_tmp_ttl_sec", True),
    "cache": ("IMAGE_CACHE_PATH", "image_cache_max_mb", "image_cache_ttl_sec", False),
}

_cleanup_lock = threading.Lock()
_async_guard = threading.Lock()
_cleanup_stop = threading.Event()
_cleanup_thread = None


# ------------------------------------------------------------------
# 基础工具
# ------------------------------------------------------------------

def _int_setting(key: str, default: int) -> int:
    """优先读后台「系统设置」，异常时回退 .env 默认值。"""
    try:
        return settings_service.get_int(key, default)
    except Exception:
        return default


def normalize_task_id(task_id) -> str:
    """校验并归一化 task_id；非法返回空串。"""
    text = str(task_id or "").strip()
    if not text or not _SAFE_ID.match(text):
        return ""
    if ".." in text:
        return ""
    return text


def safe_ext(name) -> str:
    """从文件名或扩展名里取出白名单内的扩展名，否则给 .jpg。

    注意要同时接受 ".png"（纯扩展名）与 "a.png"（文件名）两种写法：
    Path(".png").suffix 是空串，不能直接拿来判断。
    """
    text = str(name or "").strip().lower()
    if text.startswith(".") and text.count(".") == 1:
        return text if text in _ALLOWED_EXT else ".jpg"
    ext = Path(text).suffix.lower()
    return ext if ext in _ALLOWED_EXT else ".jpg"


def mimetype_for(name) -> str:
    """按扩展名给出 MIME 类型（供补拉回来的图片使用）。"""
    return _MIME_BY_EXT.get(safe_ext(name), "application/octet-stream")


def _dir(label: str) -> Path:
    path = Path(getattr(cfg, _DIRS[label][0]))
    if path.resolve() == Path(cfg.ROOT_PATH).resolve().parent.parent:
        raise ValueError("图片缓存/临时目录不能直接指向项目根目录")
    return path


def _limits(label: str) -> dict:
    """该目录的运行参数（容量、TTL、保护窗口、压缩参数）。"""
    protect = _int_setting("image_tmp_protect_sec", cfg.IMAGE_TMP_PROTECT_SEC) if _DIRS[label][3] else 0
    return {
        "path": _dir(label),
        "max_bytes": max(0, _int_setting(_DIRS[label][1], getattr(cfg, _DIRS[label][1].upper()))) * 1024 * 1024,
        "ttl": _int_setting(_DIRS[label][2], getattr(cfg, _DIRS[label][2].upper())),
        "protect": max(0, protect),
        "compress_max_side": _int_setting("image_compress_max_side", cfg.IMAGE_COMPRESS_MAX_SIDE),
        "quality": _int_setting("image_compress_quality", cfg.IMAGE_COMPRESS_QUALITY),
    }


def ensure_dirs() -> tuple:
    """确保两个目录存在，返回 (tmp, cache)。"""
    paths = []
    for label in ("tmp", "cache"):
        path = _dir(label)
        path.mkdir(parents=True, exist_ok=True)
        paths.append(path)
    return tuple(paths)


def _list_files(path: Path) -> list:
    """列出目录内的候选图片文件（跳过子目录与非法扩展名）。"""
    items = []
    try:
        for entry in path.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix.lower() not in _ALLOWED_EXT:
                continue
            try:
                stat = entry.stat()
            except OSError:
                continue
            items.append((entry, stat.st_size, stat.st_mtime))
    except FileNotFoundError:
        return []
    return items


def _find(label: str, task_id: str):
    """按 task_id 查找文件，返回 (Path, size, mtime) 或 None（多个时取最新）。"""
    task_id = normalize_task_id(task_id)
    if not task_id:
        return None
    candidates = [item for item in _list_files(_dir(label)) if item[0].stem == task_id]
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[2], reverse=True)
    return candidates[0]


def find_image(task_id: str, prefer: str = "cache"):
    """查找任务图片，返回 (Path | None, source)，source ∈ {cache, tmp, ''}。"""
    order = ("cache", "tmp") if prefer != "tmp" else ("tmp", "cache")
    for label in order:
        found = _find(label, task_id)
        if found:
            return found[0], label
    return None, ""


# ------------------------------------------------------------------
# 写入
# ------------------------------------------------------------------

def _atomic_write(path: Path, data: bytes) -> bool:
    tmp = path.with_name(path.name + ".part")
    try:
        with open(tmp, "wb") as handle:
            handle.write(data)
        tmp.replace(path)
        return True
    except Exception as e:
        logger.error("写入图片失败 %s: %s", path, e)
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        return False


def _max_side_of(data_or_path) -> int:
    try:
        if isinstance(data_or_path, (bytes, bytearray)):
            with Image.open(io.BytesIO(data_or_path)) as img:
                return max(img.size)
        with Image.open(data_or_path) as img:
            return max(img.size)
    except Exception:
        return 0


def encode_jpeg(image: Image.Image, max_side: int, quality: int) -> bytes:
    """按最长边缩放并编码为 JPEG（带 alpha 的铺白底）。"""
    work = image
    if max_side and max(work.size) > max_side:
        work = work.copy()
        work.thumbnail((max_side, max_side), Image.LANCZOS)

    if work.mode in ("RGBA", "LA", "P"):
        work = work.convert("RGBA")
        background = Image.new("RGB", work.size, (255, 255, 255))
        background.paste(work, mask=work.split()[-1])
        work = background
    elif work.mode != "RGB":
        work = work.convert("RGB")

    buf = io.BytesIO()
    work.save(buf, format="JPEG", quality=max(1, min(100, quality)), optimize=True)
    return buf.getvalue()


def compress_bytes(data: bytes, max_side: int = None, quality: int = None) -> bytes:
    """压缩图片字节；失败时原样返回。"""
    limits = _limits("cache")
    max_side = limits["compress_max_side"] if max_side is None else max_side
    quality = limits["quality"] if quality is None else quality
    try:
        with Image.open(io.BytesIO(data)) as img:
            return encode_jpeg(img, max_side, quality)
    except Exception as e:
        logger.warning("压缩失败，保留原图: %s", e)
        return data


def save_temp(task_id: str, data: bytes, ext: str = None) -> Path:
    """保存上传原图到 tmp（不做任何压缩），返回路径或 None。"""
    task_id = normalize_task_id(task_id)
    if not task_id or not data:
        return None
    ensure_dirs()
    path = _dir("tmp") / (task_id + safe_ext(ext))
    if not _atomic_write(path, data):
        return None
    _trigger_cleanup_if_needed("tmp")
    return path


def save_cache(task_id: str, data: bytes, ext: str = None, compress: bool = True) -> Path:
    """保存留存副本到 cache。

    不需要压缩时原样落盘（避免二次有损编码）；需要压缩时转成 JPEG
    （最长边按 image_compress_max_side 缩放），并清理同一 task 的旧文件。
    """
    task_id = normalize_task_id(task_id)
    if not task_id or not data:
        return None
    ensure_dirs()
    limits = _limits("cache")
    max_side = limits["compress_max_side"]
    ext = safe_ext(ext)
    needs = bool(compress and max_side and _max_side_of(data) > max_side)

    if needs:
        payload, target_ext = compress_bytes(data, max_side, limits["quality"]), ".jpg"
    else:
        payload, target_ext = data, ext

    path = _dir("cache") / (task_id + target_ext)
    if not _atomic_write(path, payload):
        return None

    for other in _list_files(_dir("cache")):
        if other[0].stem == task_id and other[0] != path:
            try:
                other[0].unlink()
            except OSError:
                pass

    _trigger_cleanup_if_needed("cache")
    return path


def read_bytes(task_id: str, prefer: str = "cache", max_side: int = None):
    """读取任务图片，返回 (data, source, mimetype)；找不到返回 (None, '', '')。"""
    path, source = find_image(task_id, prefer=prefer)
    if not path:
        return None, "", ""
    try:
        data = path.read_bytes()
    except OSError as e:
        logger.error("读取图片失败 %s: %s", path, e)
        return None, "", ""

    mimetype = _MIME_BY_EXT.get(path.suffix.lower(), "application/octet-stream")
    if max_side and _max_side_of(data) > max_side:
        try:
            with Image.open(io.BytesIO(data)) as img:
                data = encode_jpeg(img, max_side, _limits("cache")["quality"])
            mimetype = "image/jpeg"
        except Exception as e:
            logger.warning("即时缩放失败，返回原图: %s", e)
    return data, source, mimetype


# ------------------------------------------------------------------
# 回收
# ------------------------------------------------------------------

def _weight(size: int, age: float, ttl: int) -> float:
    """淘汰权重：越老越低；同年龄下大文件更高（优先靠压缩而不是删除解决）。"""
    half_life = max(60.0, (ttl or 86400) / 2.0)
    return size * math.exp(-max(0.0, age) / half_life)


def _cleanup_dir(label: str) -> dict:
    limits = _limits(label)
    path, max_bytes, ttl, protect = limits["path"], limits["max_bytes"], limits["ttl"], limits["protect"]
    max_side, quality = limits["compress_max_side"], limits["quality"]
    now = time.time()
    result = {"files": 0, "bytes": 0, "expired": 0, "compressed": 0, "evicted": 0, "freed_bytes": 0}

    total = sum(item[1] for item in _list_files(path))

    # 1) 过期清理
    if ttl > 0:
        for entry, size, mtime in _list_files(path):
            age = now - mtime
            if age > ttl and age > protect:
                try:
                    entry.unlink()
                    total -= size
                    result["expired"] += 1
                    result["freed_bytes"] += size
                except OSError:
                    pass

    # 2) 超限时优先压缩大文件
    if max_bytes and total > max_bytes and max_side:
        candidates = [item for item in _list_files(path) if _max_side_of(item[0]) > max_side]
        candidates.sort(key=lambda item: item[1], reverse=True)
        for entry, size, _mtime in candidates:
            if total <= max_bytes:
                break
            try:
                with Image.open(entry) as img:
                    payload = encode_jpeg(img, max_side, quality)
                target = entry.with_suffix(".jpg")
                if not _atomic_write(target, payload):
                    continue
                if target != entry:
                    entry.unlink()
                total -= (size - len(payload))
                result["compressed"] += 1
                result["freed_bytes"] += max(0, size - len(payload))
            except Exception as e:
                logger.debug("压缩 %s 失败: %s", entry, e)

    # 3) 仍超限 -> 按权重升序淘汰
    if max_bytes and total > max_bytes:
        weighted = []
        for entry, size, mtime in _list_files(path):
            age = now - mtime
            if age < protect:          # 保护窗口内的文件不淘汰
                continue
            weighted.append((_weight(size, age, ttl), size, entry))
        weighted.sort(key=lambda item: item[0])
        for _w, size, entry in weighted:
            if total <= max_bytes:
                break
            try:
                entry.unlink()
                total -= size
                result["evicted"] += 1
                result["freed_bytes"] += size
            except OSError:
                pass

    remaining = _list_files(path)
    result["files"] = len(remaining)
    result["bytes"] = sum(item[1] for item in remaining)
    return result


def cleanup(force: bool = False) -> dict:
    """执行一次回收。force=False 时若已有清理在跑就直接返回。"""
    if not _cleanup_lock.acquire(blocking=bool(force)):
        return {"skipped": True}
    try:
        ensure_dirs()
        outcome = {label: _cleanup_dir(label) for label in ("tmp", "cache")}
        moved = sum(item["freed_bytes"] for item in outcome.values())
        if moved:
            logger.info("图片回收完成: %s", outcome)
        return outcome
    finally:
        _cleanup_lock.release()


def _trigger_cleanup_if_needed(label: str) -> None:
    """写入后如果该目录超限，异步触发一次回收（不阻塞请求）。"""
    limits = _limits(label)
    if not limits["max_bytes"]:
        return
    if sum(item[1] for item in _list_files(limits["path"])) <= limits["max_bytes"]:
        return
    if not _async_guard.acquire(blocking=False):
        return

    def _run():
        try:
            cleanup()
        finally:
            _async_guard.release()

    threading.Thread(target=_run, name="image-cleanup", daemon=True).start()


# ------------------------------------------------------------------
# 统计与后台线程
# ------------------------------------------------------------------

def stats() -> dict:
    """两个目录的占用统计（供后台/调试）。"""
    result = {}
    for label in ("tmp", "cache"):
        limits = _limits(label)
        items = _list_files(limits["path"])
        result[label] = {
            "path": str(limits["path"]),
            "files": len(items),
            "bytes": sum(item[1] for item in items),
            "max_bytes": limits["max_bytes"],
            "ttl": limits["ttl"],
            "protect": limits["protect"],
            "compress_max_side": limits["compress_max_side"],
            "quality": limits["quality"],
        }
    return result


def start_cleanup_thread() -> bool:
    """启动后台回收线程（幂等）。"""
    global _cleanup_thread
    if _cleanup_thread and _cleanup_thread.is_alive():
        return False
    ensure_dirs()
    _cleanup_stop.clear()

    def _loop():
        while not _cleanup_stop.wait(max(10, cfg.IMAGE_CLEAN_INTERVAL_SEC)):
            try:
                cleanup()
            except Exception as e:
                logger.error("回收线程异常: %s", e)

    _cleanup_thread = threading.Thread(target=_loop, name="image-cleanup-loop", daemon=True)
    _cleanup_thread.start()
    logger.info("图片回收线程已启动（间隔 %ss）", cfg.IMAGE_CLEAN_INTERVAL_SEC)
    return True


def stop_cleanup_thread() -> None:
    _cleanup_stop.set()
