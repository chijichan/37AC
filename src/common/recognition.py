# common/recognition.py
"""识别结果统一结构（CLI / Server 共享的规范定义与归一化层）

整个项目只有三种相关结构，均在《识别结果结构》约定内：

1. 类别对象（Class）— classes.json 条目，类别名 = 整个对象：
       { "IP/角色": {"id": 角色名, "ip": 作品名, "name_zh": 备用中文名,
                     "features_used": [...], "tags": [...]} }
   "IP/角色" 字符串仅作为唯一标识（数据集路径参考 / 模型索引 / JSON 键）。

2. 候选角色项（Candidate）— class_probs 中的每一项 = 类别对象 + 排名信息：
       {"name": "IP/角色", "prob": 0-100,
        "id", "ip", "name_zh", "features_used", "tags"}
   name 为唯一标识，prob 为 0-100 百分数。

3. 识别结果（Result）— 推理引擎的统一返回：
       {"success": bool,
        "class_probs": [Candidate, ...],      # 按 prob 降序，[0] 即最佳结果
        "image_path": str,
        "recognition_type": "local" | "llm",
        "error": null | str,
        "features_used": [...], "tags": [...]}  # LLM 主结论的冗余快照（本地模型为空）

本模块提供候选项的归一化解析，历史/外部格式（名称字段 name/label、
概率字段 prob/confidence/probability、字符串百分比）统一在此处理，
其余代码只消费上面的规范结构。
"""

from typing import Optional


def to_prob(value) -> Optional[float]:
    """把概率值归一化为 0-100 浮点数。

    支持：数值、字符串（"93.5" / "93.5%"）；无法解析时返回 None。
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().rstrip("%"))
        except (TypeError, ValueError):
            return None
    return None


def parse_candidate_entry(entry) -> Optional[dict]:
    """把任意候选条目归一化为规范 Candidate。

    兼容字段：
      - 名称：name / label
      - 概率：prob / confidence / probability（数值或字符串百分比）

    Args:
        entry: 候选条目 dict

    Returns:
        dict: 规范候选 {"name": ..., "prob"?: ..., 其余类别对象字段透传}；
        条目无效（无名称）时返回 None。
    """
    if not isinstance(entry, dict):
        return None
    name = str(entry.get("name") or entry.get("label") or "").strip()
    if not name:
        return None

    raw_prob = entry.get("prob")
    if raw_prob is None:
        raw_prob = entry.get("confidence", entry.get("probability"))
    prob = to_prob(raw_prob)

    candidate = {"name": name}
    if prob is not None:
        candidate["prob"] = prob
    # 透传类别对象字段（类别名 = 整个对象）
    for field in ("id", "ip", "name_zh", "features_used", "tags"):
        if entry.get(field) not in (None, ""):
            candidate[field] = entry[field]
    return candidate


def parse_top_candidate(result) -> Optional[dict]:
    """从识别结果中提取规范化的最佳候选（class_probs 第一项）。

    Args:
        result: 识别结果 dict

    Returns:
        dict: 规范候选；无 class_probs / 结果无效时返回 None
    """
    if not isinstance(result, dict):
        return None
    class_probs = result.get("class_probs")
    if isinstance(class_probs, list) and class_probs:
        return parse_candidate_entry(class_probs[0])
    return None


def result_top_name(result) -> Optional[str]:
    """识别结果最佳候选的名称（"IP/角色"）。"""
    top = parse_top_candidate(result)
    return top.get("name") if top else None


def result_top_prob(result) -> Optional[float]:
    """识别结果最佳候选的置信度（0-100）。"""
    top = parse_top_candidate(result)
    return top.get("prob") if top else None
