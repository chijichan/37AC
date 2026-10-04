# -*- coding: utf-8 -*-
"""训练报告：把进度写成 progress.json + 自包含的 index.html（樱花拿铁 UI，零依赖）。

设计见 docs/design-training-report.md。要点：
- 数据源唯一：progress.json（原子写）；HTML 由本模块渲染（内联 CSS/SVG，file:// 双击可看）
- 页面用 <meta refresh> 自刷新（file:// 下 fetch 会被 CORS 拦，故不用 JS 轮询）
- 单进程一次训练 = 一个 run 目录：saves/reports/<版本>-<时间戳>/
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from string import Template

from config.base import REPORT_DIR, REPORT_ENABLED, REPORT_REFRESH_SEC
from config.log_config import get_logger

logger = get_logger("report")

_STATE = {"run_dir": None, "data": None}


# ------------------------------------------------------------------ 基础
def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def enabled() -> bool:
    return bool(REPORT_ENABLED)


def run_dir() -> Path:
    return Path(_STATE["run_dir"]) if _STATE["run_dir"] else None


def _data() -> dict:
    return _STATE["data"]


# ------------------------------------------------------------------ 生命周期
def start_run(meta: dict = None, version: str = None) -> Path:
    """开始一次训练的 run：建目录、写 progress.json、渲染首屏。"""
    if not enabled():
        return None
    if _STATE["run_dir"] is not None:
        set_status("finished", "新 run 开始，上一 run 结束")

    meta = dict(meta or {})
    version = str(version or meta.get("version") or "unknown")
    folder = Path(REPORT_DIR) / ("%s-%s" % (version, _stamp()))
    folder.mkdir(parents=True, exist_ok=True)

    _STATE["run_dir"] = folder
    _STATE["data"] = {
        "run_id": folder.name,
        "status": "running",
        "note": "",
        "started_at": _now(),
        "updated_at": _now(),
        "started_ts": time.time(),
        "elapsed_sec": 0,
        "meta": meta,
        "phase": {"name": "", "label": "", "epoch": 0, "total": 0},
        "progress": {"step": 0, "steps_total": 0, "epochs_done": 0, "epochs_total": 0, "eta_sec": None},
        "epochs": [],
        "checkpoints": [],
        "events": [],
    }
    add_event("训练开始：%s" % (meta.get("version") or version))
    _flush()
    logger.info("训练报告: %s", folder / "index.html")
    return folder


def set_meta(extra: dict) -> None:
    """回填/更新概览信息（类别数、训练/验证张数、设备等），报告早于信息采集启动时用。"""
    if _data() is None or not extra:
        return
    _data()["meta"].update({k: v for k, v in extra.items() if v not in (None, "")})
    _flush()


def set_status(status: str, note: str = "") -> None:
    if _data() is None:
        return
    _data()["status"] = status
    if status != "running":                      # 训练结束/中断时刷新多 run 对比页
        try:
            build_index_page()
        except Exception as e:
            logger.debug("对比页生成失败: %s", e)
    if note:
        _data()["note"] = note
        add_event(note)
    else:
        _flush()


def add_event(text: str) -> None:
    if _data() is None:
        return
    _data()["events"].append({"at": _now(), "text": str(text)})
    _data()["events"] = _data()["events"][-200:]
    _flush()


def set_phase(name: str, label: str = "", epoch_total: int = 0) -> None:
    if _data() is None:
        return
    _data()["phase"] = {"name": name, "label": label or name, "epoch": 0, "total": epoch_total}
    add_event("阶段 %s 开始（%s，共 %d 轮）" % (name, label, epoch_total))


def record_step(step: int, total: int = 0, epochs_done: int = None,
                epochs_total: int = None, eta_sec=None, loss=None, acc=None) -> None:
    """步级轻量更新（只动进度，不追加 epochs）。"""
    if _data() is None:
        return
    p = _data()["progress"]
    p["step"] = int(step)
    if total:
        p["steps_total"] = int(total)
    if epochs_done is not None:
        p["epochs_done"] = int(epochs_done)
    if epochs_total is not None:
        p["epochs_total"] = int(epochs_total)
    if eta_sec is not None:
        p["eta_sec"] = int(eta_sec)
    ph = _data()["phase"]
    if acc is not None:
        ph["last_acc"] = round(float(acc), 2)
    if loss is not None:
        ph["last_loss"] = round(float(loss), 4)
    _flush()


def record_epoch(epoch: int, phase: str, loss: float, train_acc: float,
                 val_acc: float, lr: float, secs: float = 0) -> None:
    if _data() is None:
        return
    _data()["epochs"].append({
        "epoch": int(epoch), "phase": phase,
        "loss": round(float(loss), 4), "train_acc": round(float(train_acc), 2),
        "val_acc": round(float(val_acc), 2), "lr": float(lr),
        "secs": round(float(secs), 1), "at": _now(),
    })
    ph = _data()["phase"]
    ph["epoch"] = int(epoch)
    # 耗时：用相邻两次记录的时间差（训练端不必传秒数；退出重进也不会算错）
    now = time.time()
    last = _data().get("_last_epoch_ts")
    if last:
        _data()["epochs"][-1]["secs"] = round(now - float(last), 1)
    _data()["_last_epoch_ts"] = now
    best = _data().get("best_val")
    if best is None or float(val_acc) > float(best):
        _data()["best_val"] = round(float(val_acc), 2)
    _data()["progress"]["epochs_done"] = len(_data()["epochs"])
    if ph.get("total"):
        left = max(0, int(ph["total"]) - int(epoch))
        per = float(secs) or (float(_data()["elapsed_sec"]) / max(1, len(_data()["epochs"])))
        _data()["progress"]["eta_sec"] = int(left * per)
    _flush()


def add_checkpoint(name: str, kind: str = "manual", accuracy=None, size_mb=None) -> None:
    if _data() is None:
        return
    _data()["checkpoints"].insert(0, {
        "name": name, "kind": kind,
        "accuracy": None if accuracy is None else round(float(accuracy), 2),
        "size_mb": size_mb, "at": _now(),
    })
    _flush()


# ------------------------------------------------------------------ 渲染
def _flush() -> None:
    """写 progress.json 并重渲染 index.html。"""
    folder = run_dir()
    if folder is None:
        return
    data = _data()
    data["updated_at"] = _now()
    data["elapsed_sec"] = int(time.time() - data.get("started_ts", time.time()))
    _write_json(Path(folder) / "progress.json", data)
    try:
        html = render_html(data)
        (Path(folder) / "index.html").write_text(html, encoding="utf-8")
        # 固定入口：始终指向"当前正在跑的那次"，继续训练时不必换标签页
        (Path(REPORT_DIR) / "latest.html").write_text(html, encoding="utf-8")
    except Exception as e:                     # 渲染失败不能影响训练
        logger.warning("报告渲染失败: %s", e)


def _fmt_duration(sec) -> str:
    sec = int(sec or 0)
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return ("%d:%02d:%02d" % (h, m, s)) if h else ("%02d:%02d" % (m, s))


def _nice_ticks(lo: float, hi: float, count: int = 4):
    """生成"好看"的刻度值（1/2/2.5/5/10 步长）。"""
    import math

    if hi <= lo:
        hi = lo + 1.0
    span = hi - lo
    exp = math.floor(math.log10(span / max(1, count)))
    step = 10 ** exp
    for m in (1, 2, 2.5, 5, 10):
        if span / (step * m) <= count:
            step *= m
            break
    start = math.floor(lo / step) * step
    ticks, v = [], start
    while v <= hi + step * 0.5 and len(ticks) < 9:
        if v >= lo - step * 0.5:
            ticks.append(round(v, 4))
        v += step
    return ticks, step


def _fmt_tick(v: float, step: float) -> str:
    if abs(step) >= 1:
        return "%g" % round(v, 2)
    return ("%.2f" % v).rstrip("0").rstrip(".")


def _svg_series(series, labels=None, width=560, height=170, y_label="", unit="", ticks_count=4):
    # y_label 保留形参以兼容调用方，但不再渲染（用户要求去掉 % / loss 小字）
    """多序列折线 + 坐标系；所有序列共用 y 轴范围。

    series: [(显示名, 数值列表, 颜色, 面积填充色)]；最后一个序列作为磁吸圆点的主序列。
    返回 (svg, payload)；payload 每项 {"px","py","e","t"}，t 为该轮的合并提示文本。
    """
    series = [(n, [float(x) for x in vals], c, f) for n, vals, c, f in series if vals]
    if not series:
        return '<div class="empty">暂无数据</div>', []
    allv = [v for _, vals, _, _ in series for v in vals]
    lo, hi = min(allv), max(allv)
    if hi == lo:
        lo, hi = lo - abs(lo) * 0.02 - 0.5, hi + abs(hi) * 0.02 + 0.5
    ticks, step = _nice_ticks(lo, hi, ticks_count)
    # 只保留落在数据范围内的刻度：否则最低刻度会画到 x 轴下方（y 轴"负半轴"）
    ticks = [t for t in ticks if lo <= t <= hi] or [lo, hi]
    # 左边距按最长刻度文字自适应（去掉小字标签后不再需要固定 46px 的大留白）
    _tick_txt = [_fmt_tick(x, step) for x in ticks] or ["0"]
    _maxw = max(len(s) for s in _tick_txt)
    L = int(9 + _maxw * 6.4)          # 9px 贴边 + 每个字符约 6.4px + 6px 间隙
    R, T, B = 9, 10, 22

    pw, ph = width - L - R, height - T - B
    n = max(len(vals) for _, vals, _, _ in series)

    def x_at(i):
        return L + (pw * (i / (n - 1)) if n > 1 else pw / 2)

    def y_at(v):
        # 夹在绘图区内，任何情况下都不越界（含浮点误差）
        return max(T, min(T + ph, T + ph - ph * ((v - lo) / (hi - lo))))

    parts = ['<svg class="chart" viewBox="0 0 %d %d" preserveAspectRatio="none">' % (width, height)]
    for t in ticks:
        y = y_at(t)
        parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#EFE8EC" stroke-width="1"/>'
                     % (L, y, width - R, y))
        parts.append('<text x="%d" y="%.1f" text-anchor="end" font-size="10" fill="#8A7C85" '
                     'dominant-baseline="middle">%s</text>' % (L - 6, y, _fmt_tick(t, step)))
    parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#C9BDC5" stroke-width="1"/>'
                 % (L, T, L, T + ph))
    parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#C9BDC5" stroke-width="1"/>'
                 % (L, T + ph, width - R, T + ph))
    parts.append('<g class="xaxis">')
    step_i = max(1, n // 8)
    for i in range(0, n, step_i):
        x = x_at(i)
        parts.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#C9BDC5" stroke-width="1"/>'
                     % (x, T + ph, x, T + ph + 3))
        lab = labels[i] if labels and i < len(labels) else (i + 1)
        parts.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="10" fill="#8A7C85">%s</text>'
                     % (x, T + ph + 14, lab))
    parts.append('<g class="series">')      # 折线/面积都放进这里，缩放时可整组重建
    for _si, (name, vals, color, fill) in enumerate(series):
        pts = ["%.1f,%.1f" % (x_at(i), y_at(v)) for i, v in enumerate(vals)]
        if len(pts) > 1:
            area = "%.1f,%d %s %.1f,%d" % (x_at(0), T + ph, " ".join(pts), x_at(len(vals) - 1), T + ph)
            parts.append('<polygon class="ar" data-s="%d" points="%s" fill="%s"/>' % (_si, area, fill))
        parts.append('<polyline class="ln" data-s="%d" points="%s" fill="none" stroke="%s" '
                     'stroke-width="2" stroke-linejoin="round"/>' % (_si, " ".join(pts), color))
        parts.append('<circle cx="%.1f" cy="%.1f" r="3" fill="%s"/>'
                     % (x_at(len(vals) - 1), y_at(vals[-1]), color))
    parts.append('</g>')

    # 数据点（默认 opacity=0，仅悬浮那一轮显示）
    for _nm, _vals, _col, _f in series:
        for _i, _v in enumerate(_vals):
            parts.append('<circle class="pt" data-i="%d" data-s="%s" cx="%.1f" cy="%.1f" '
                         'r="1.6" fill="%s" opacity="0" pointer-events="none"/>'
                         % (_i, _nm, x_at(_i), y_at(_v), _col))

    # 命中区：每个数据点一条透明竖条（浏览器直接命中，无需 JS 算坐标；缩放后自动跟随）
    for i in range(n):
        cx = x_at(i)
        parts.append('<rect class="hit" data-i="%d" x="%.1f" y="%d" width="%.1f" height="%d" '
                     'fill="transparent"/>' % (i, cx - 6, T, 12, ph))
    parts.append("</svg>")

    primary = series[-1][1]
    payload = []
    for i in range(n):
        lab = labels[i] if labels and i < len(labels) else (i + 1)
        txt = " / ".join("%s %s%s" % (nm, round(vals[i], 2) if i < len(vals) else "-", unit)
                         for nm, vals, _, _ in series)
        payload.append({"px": round(x_at(i), 1), "py": round(y_at(primary[i]) if i < len(primary) else 0, 1),
                        "e": lab, "v": round(primary[i], 4) if i < len(primary) else None,
                        # 每条序列在该轮的 y（SVG 坐标）：JS 缩放时据此重建折线/面积（幂等）
                        # 该轮各序列的 y（标量，SVG 坐标）——JS 缩放时据此重建曲线
                        "ys": [round(y_at(vals[i]), 1) for _n2, vals, _c2, _f2 in series],
                        "full": width,
                        "t": "第 %s 轮 · %s" % (lab, txt)})
    return "".join(parts), payload


def _svg_line(values, labels=None, **kw):
    """单序列兼容包装（损失图等）。"""
    return _svg_series([("", values, kw.pop("color", "#3E8FD9"), kw.pop("fill", "rgba(62,143,217,.10)"))],
                       labels, **kw)


_TEMPLATE = Template("""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>37AC 训练报告 - $run_id</title>
<meta http-equiv="refresh" content="$refresh">
<style>
:root{--bg:#FDF9FB;--surface:#fff;--surface2:#FBF3F7;--ink900:#322931;--ink700:#574B54;
--ink500:#8A7C85;--ink300:#C9BDC5;--ink100:#EFE8EC;--pink50:#FDF0F6;--pink100:#FBE0EE;
--pink300:#F09CC3;--pink400:#E86FA6;--pink500:#DE4F8D;--pink600:#C93470;--mint:#3DBDB4;
--success:#2FA36B;--success-bg:#E5F5ED;--warning:#E08A1E;--warning-bg:#FCF0DE;
--danger:#D64545;--danger-bg:#FBE7E7;--info:#3E8FD9;--info-bg:#E5F1FB;
--r-pill:999px;--r-input:12px;--r-card:16px;--shadow:0 2px 12px rgba(50,41,49,.05)}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink900);
font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:24px 20px 48px}
header{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:18px}
h1{font-size:20px;margin:0;font-weight:800;letter-spacing:.2px}
.mono{font-family:'JetBrains Mono',Consolas,monospace}
.badge{display:inline-block;padding:4px 12px;border-radius:var(--r-pill);font-size:12px;font-weight:700}
.badge.running{background:var(--pink100);color:var(--pink600)}
.badge.finished{background:var(--success-bg);color:var(--success)}
.badge.interrupted{background:var(--warning-bg);color:var(--warning)}
.badge.failed{background:var(--danger-bg);color:var(--danger)}
.badge.idle{background:var(--ink100);color:var(--ink700)}
.muted{color:var(--ink500);font-size:13px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:18px}
.card{background:var(--surface);border-radius:var(--r-card);box-shadow:var(--shadow);padding:14px 16px}
.card .k{font-size:12px;color:var(--ink500);margin-bottom:6px}
.card .v{font-size:18px;font-weight:800}
.panel{background:var(--surface);border-radius:var(--r-card);box-shadow:var(--shadow);padding:16px 18px;margin-bottom:18px}
.panel h2{font-size:14px;margin:0 0 12px;font-weight:800;color:var(--ink700)}
.bar{height:10px;border-radius:var(--r-pill);background:var(--ink100);overflow:hidden;margin:8px 0}
.bar>i{display:block;height:100%;background:linear-gradient(90deg,var(--pink400),var(--pink600))}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:820px){.grid2{grid-template-columns:1fr}}
.chart{width:100%;height:170px;display:block}
.empty{color:var(--ink300);font-size:13px;padding:24px 0;text-align:center}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--ink100)}
th{color:var(--ink500);font-weight:700;font-size:12px}
tbody tr:hover{background:var(--surface2)}
.ev{font-size:13px;color:var(--ink700);padding:6px 0;border-bottom:1px dashed var(--ink100)}
.ev .t{color:var(--ink500);margin-right:10px}
footer{color:var(--ink500);font-size:12px;text-align:center;margin-top:24px}
.card{min-width:0}
.card .v{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;line-height:1.25}
.card .v.wrap{white-space:normal;word-break:break-all;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;font-size:15px}
.card .v[title]{cursor:help}
.chartbox{position:relative}
.hline{position:absolute;top:0;bottom:0;width:1px;background:var(--line,#DE4F8D);opacity:0;pointer-events:none;transition:opacity .12s}
.hdot{position:absolute;margin:0;width:8px;height:8px;border-radius:50%;background:#fff;border:2px solid var(--line,#DE4F8D);transform:translate(-50%,-50%);opacity:0;pointer-events:none;transition:opacity .12s}
.tip{position:absolute;top:2px;padding:4px 10px;background:var(--surface);color:var(--ink900);border:1px solid var(--pink200);box-shadow:0 4px 14px rgba(50,41,49,.10);border-radius:var(--r-pill);font-size:12px;white-space:nowrap;opacity:0;pointer-events:none;transform:translateX(-50%);transition:opacity .12s;font-family:'JetBrains Mono',Consolas,monospace;z-index:3}
.tip:empty{display:none}
.chartbox:hover .hline,.chartbox:hover .tip,.chartbox:hover .hdot{opacity:1}
tbody tr.hl{background:var(--pink50)}
.charttip{position:fixed;display:none;z-index:50;padding:5px 11px;border-radius:999px;background:#FFFFFF;border:1px solid var(--pink200);box-shadow:0 4px 14px rgba(50,41,49,.12);color:var(--ink900);font-size:12px;white-space:nowrap;pointer-events:none;font-family:'JetBrains Mono',Consolas,monospace}

.legend{display:inline-flex;gap:14px;margin-left:12px;font-size:12px;color:var(--ink500);vertical-align:middle}
.legend i{width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:5px}
tbody tr.hl td{color:var(--ink900);font-weight:700}
</style></head><body><div class="wrap">
<header>
  <h1>37AC 训练报告</h1>
  <span class="mono muted">$run_id</span>
  <span class="badge $status_class">$status_text</span>
  <span class="muted">已用时 <b class="mono">$elapsed</b></span>
  <span class="muted">更新于 <span class="mono">$updated_at</span></span>
</header>

<div class="cards">$cards</div>

<div class="panel">
  <h2>进度</h2>
  <div class="muted">$phase_text</div>
  <div class="bar"><i style="width:$phase_pct%"></i></div>
  <div class="muted">$progress_text</div>
</div>

<div class="grid2">
  <div class="panel"><h2>准确率（每轮 %）<span class="legend"><span><i style="background:#3DBDB4"></i>train</span><span><i style="background:#DE4F8D"></i>val</span></span></h2>
    $chart_acc</div>
  <div class="panel"><h2>训练损失（每轮）</h2>
    $chart_loss</div>
</div>

<div class="panel"><h2>每轮明细</h2>$epoch_table</div>
<div class="panel"><h2>真实口径评估</h2>$eval_panel</div>
<div class="panel"><h2>检查点</h2>$ckpt_table</div>
<div class="panel"><h2>事件</h2>$events</div>

$chart_js<footer>数据源 progress.json ｜ 生成于 $generated_at ｜ 每 $refresh 秒自动刷新</footer>
</div></body></html>
""")


# 图表交互脚本：放在独立 .js 文件里（避免 Python 字符串转义把 \n 写成字面量，
# 那种错误会让整段 JS 语法失败、页面上什么都不响应）
_JS_FILE = Path(__file__).resolve().parent.parent / "assets" / "report.js"
try:
    _CHART_JS = "<script>\n" + _JS_FILE.read_text(encoding="utf-8") + "\n</script>"
except Exception as _js_err:  # 脚本缺失时报告仍可用（只是没有悬浮交互）
    _CHART_JS = ""
    logger.warning("报告交互脚本读取失败: %s", _js_err)

def _chart_box(name: str, svg: str, payload: list, height: int = 170,
               color: str = "#DE4F8D") -> str:
    """图表容器：SVG（内置高亮带与数据点）+ 供 JS 使用的 payload。"""
    if not payload:
        return svg
    import json as _json

    data = _json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return ('<div class="chartbox" data-src="chart-%s" data-w="560" data-h="%d" data-tip="tip-%s">'
            '<div class="charttip" id="tip-%s"></div>%s'
            '<script type="application/json" id="chart-%s">%s</script></div>'
            % (name, height, name, name, svg, name, data))


def x_labels(epochs: list) -> list:
    """图表 x 轴刻度：直接用训练轮次。"""
    return [e.get("epoch") for e in (epochs or [])]


def render_html(data: dict) -> str:
    meta = data.get("meta") or {}
    cards = []
    pairs = [("基模", meta.get("base")), ("类别数", meta.get("classes") or meta.get("class_count"))]
    if meta.get("train") or meta.get("val"):
        pairs.append(("训练/验证", "%s / %s" % (meta.get("train") or "-", meta.get("val") or "-")))
    pairs += [("batch", meta.get("batch")), ("分辨率", meta.get("image_size")),
              ("设备", meta.get("device")), ("best val", data.get("best_val"))]
    for k, v in pairs:
        if v in (None, "", "None", "None / None"):
            continue
        text_v = str(v)
        cls = "v wrap" if len(text_v) > 18 else "v"
        esc = text_v.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
        cards.append('<div class="card"><div class="k">%s</div>'
                     '<div class="%s" title="%s">%s</div></div>' % (k, cls, esc, esc))

    epochs = data.get("epochs") or []
    val_series = [e["val_acc"] for e in epochs]
    train_series = [e["train_acc"] for e in epochs]
    loss_series = [e["loss"] for e in epochs]

    rows = []
    for e in reversed(epochs[-30:]):
        rows.append("<tr data-e='%s'><td class='mono'>%s</td><td>%s</td><td class='mono'>%.4f</td>"
                    "<td class='mono'>%.2f%%</td><td class='mono'>%.2f%%</td>"
                    "<td class='mono'>%.0e</td><td class='mono'>%ss</td><td class='muted'>%s</td></tr>"
                    % (e["epoch"], e["epoch"], e["phase"], e["loss"], e["train_acc"], e["val_acc"],
                       e["lr"], e["secs"], e["at"]))
    epoch_table = ("<table><thead><tr><th>轮</th><th>阶段</th><th>loss</th><th>train</th>"
                   "<th>val</th><th>lr</th><th>耗时</th><th>时间</th></tr></thead><tbody>%s</tbody></table>"
                   % "".join(rows)) if rows else '<div class="empty">尚未完成第一轮</div>'

    ck_rows = ["<tr><td class='mono'>%s</td><td>%s</td><td class='mono'>%s</td><td class='mono'>%s MB</td>"
               "<td class='muted'>%s</td></tr>"
               % (c["name"], c["kind"],
                  ("%.2f%%" % c["accuracy"]) if c.get("accuracy") is not None else "-",
                  c.get("size_mb") if c.get("size_mb") is not None else "-", c["at"])
               for c in (data.get("checkpoints") or [])]
    ckpt_table = ("<table><thead><tr><th>名称</th><th>类型</th><th>正确率</th><th>体积</th><th>时间</th>"
                  "</tr></thead><tbody>%s</tbody></table>" % "".join(ck_rows)) if ck_rows \
        else '<div class="empty">暂无检查点</div>'

    events = "".join('<div class="ev"><span class="t mono">%s</span>%s</div>' % (e["at"], e["text"])
                     for e in reversed((data.get("events") or [])[-40:])) \
        or '<div class="empty">暂无事件</div>'

    prog = data.get("progress") or {}
    phase = data.get("phase") or {}
    pct = 0
    if phase.get("total"):
        pct = min(100, int(100.0 * (phase.get("epoch") or 0) / phase["total"]))
    elif prog.get("steps_total"):
        pct = min(100, int(100.0 * (prog.get("step") or 0) / prog["steps_total"]))
    eta = prog.get("eta_sec")
    progress_text = "已处理 %s 轮 ｜ 当前步 %s/%s ｜ %s" % (
        prog.get("epochs_done") or 0, prog.get("step") or 0, prog.get("steps_total") or "-",
        ("预计剩余 %s" % _fmt_duration(eta)) if eta else
        ("第 1 轮进行中…" if not epochs else "预计剩余计算中"))

    status = str(data.get("status") or "running")
    status_text = {"running": "● 训练中", "finished": "✔ 已完成", "interrupted": "■ 已中断",
                   "failed": "✘ 失败"}.get(status, status)
    return _TEMPLATE.substitute(
        run_id=data.get("run_id"), refresh=int(REPORT_REFRESH_SEC or 10),
        status_class=status, status_text=status_text,
        elapsed=_fmt_duration(data.get("elapsed_sec")), updated_at=data.get("updated_at"),
        cards="".join(cards),
        phase_text="阶段 %s ｜ %s ｜ 第 %s/%s 轮" % (phase.get("name") or "-", phase.get("label") or "-",
                                                   phase.get("epoch") or 0, phase.get("total") or "-"),
        phase_pct=pct, progress_text=progress_text,
        chart_acc=_chart_box("acc", *_svg_series(
            [("train", train_series, "#3DBDB4", "rgba(61,189,180,.08)"),
             ("val", val_series, "#DE4F8D", "rgba(222,79,141,.10)")],
            x_labels(epochs), unit="%"), color="#DE4F8D"),
        chart_loss=_chart_box("loss", *_svg_line(loss_series, x_labels(epochs), color="#3E8FD9",
                                                 fill="rgba(62,143,217,.10)"),
                              color="#3E8FD9"),
        chart_js=_CHART_JS,
        epoch_table=epoch_table, ckpt_table=ckpt_table, events=events,
        eval_panel=_eval_panel_html(data.get("eval")),
        generated_at=_now(),
    )


def set_eval(results: dict) -> None:
    """写入真实口径评估结果（来自 services.eval_service.compare）。"""
    if _data() is None:
        return
    _data()["eval"] = results or {}
    add_event("真实口径评估完成: " + ", ".join(
        "%s %.2f%%" % ((r or {}).get("label", m), (r or {}).get("acc") or 0)
        for m, r in (_data()["eval"] or {}).items() if isinstance(r, dict)))


def _eval_panel_html(results) -> str:
    """渲染口径对比表（含门控 A/B 结论）。"""
    if not results:
        return '<div class="empty">尚未评估（可运行 scripts/eval_pipeline.py）</div>'
    rows, base = [], None
    for mode, r in results.items():
        if not isinstance(r, dict):
            continue
        acc = r.get("acc")
        if mode == "cropped":
            base = acc
        delta = ""
        if base is not None and acc is not None and mode != "cropped":
            delta = "%+.2f" % (acc - base)
        rows.append(
            "<tr><td>%s</td><td class='mono'>%s</td><td class='mono'>%s%%</td>"
            "<td class='mono'>%s%%</td><td class='mono'>%s</td></tr>"
            % (r.get("label") or mode, r.get("total"),
               "%.2f" % acc if acc is not None else "-",
               "%.2f" % r["acc_top3"] if r.get("acc_top3") is not None else "-", delta))
    table = ("<table><thead><tr><th>口径</th><th>样本</th><th>top-1</th><th>top-3</th>"
             "<th>相对数据集</th></tr></thead><tbody>%s</tbody></table>" % "".join(rows))
    gate_on = (results.get("detect") or {}).get("acc")
    gate_off = (results.get("detect_nogate") or {}).get("acc")
    if gate_on is not None and gate_off is not None:
        verdict = "有效" if gate_on > gate_off else ("无效/有害" if gate_on < gate_off else "无影响")
        table += '<div class="ev">裁剪质量门控 A/B：开启 %.2f%% vs 关闭 %.2f%% ⇒ <b>%s</b></div>' % (
            gate_on, gate_off, verdict)
    return table


_RUN_COLORS = ["#DE4F8D", "#3E8FD9", "#3DBDB4", "#E08A1E", "#A82A5C", "#7A5AF8", "#2FA36B", "#D64545"]


def build_index_page(limit: int = 8) -> str:
    """生成多 run 对比页 saves/reports/index.html（val 曲线叠加 + run 清单）。"""
    import json as _json

    runs = list_runs(limit)
    rows, series = [], []
    for i, run in enumerate(runs):
        try:
            data = _json.loads((Path(run["dir"]) / "progress.json").read_text(encoding="utf-8"))
        except Exception:
            continue
        meta = data.get("meta") or {}
        eps = [e for e in (data.get("epochs") or [])]
        vals = [float(e.get("val_acc") or 0) for e in eps]
        best = max(vals) if vals else None
        color = _RUN_COLORS[i % len(_RUN_COLORS)]
        rows.append("<tr><td class='mono'><a href='%s/index.html'>%s</a></td><td>%s</td><td>%s</td>"
                    "<td class='mono'>%s</td><td class='mono'>%s</td><td class='mono'>%s%%</td>"
                    "<td>%s</td><td class='mono'>%s</td></tr>"
                    % (run["run_id"], run["run_id"], meta.get("base") or "-", meta.get("image_size") or "-",
                       meta.get("batch") or "-", meta.get("class_count") or meta.get("classes") or "-",
                       ("%.2f" % best) if best is not None else "-", data.get("status") or "-",
                       len(vals)))
        # 折线：x 用轮次序（各 run 起点对齐），颜色区分
        pts = []
        if vals:
            lo, hi = min(min(vals) for vals in [vals]), max(max(v for v in vals) for vals in [vals])
            if hi == lo:
                hi = lo + 1
            for k, v in enumerate(vals):
                x = 46 + (560 - 56) * (k / max(1, max(1, len(vals) - 1)))
                y = 12 + (170 - 36) - (170 - 36) * ((v - lo) / (hi - lo))
                pts.append("%.1f,%.1f" % (x, y))
        if pts:
            series.append((color, run["run_id"], pts))

    svg = ['<svg class="chart" viewBox="0 0 560 170" preserveAspectRatio="none">',
           '<line x1="46" y1="12" x2="46" y2="146" stroke="#C9BDC5"/>',
           '<line x1="46" y1="146" x2="550" y2="146" stroke="#C9BDC5"/>']
    for pct in (0, 25, 50, 75, 100):
        y = 146 - (146 - 12) * pct / 100.0
        svg.append('<line x1="46" y1="%.1f" x2="550" y2="%.1f" stroke="#EFE8EC"/>' % (y, y))
        svg.append('<text x="40" y="%.1f" text-anchor="end" font-size="10" fill="#8A7C85" '
                   'dominant-baseline="middle">%d%%</text>' % (y, pct))
    for color, name, pts in series:
        svg.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2"/>' % (" ".join(pts), color))
    svg.append("</svg>")
    legend = "".join('<span style="display:inline-flex;align-items:center;gap:6px;margin-right:14px">'
                     '<i style="width:10px;height:10px;border-radius:50%%;background:%s;display:inline-block"></i>'
                     '<span class="mono" style="font-size:12px">%s</span></span>' % (c, n) for c, n, _ in series)

    html = ("<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>37AC 训练对比</title>"
            "<style>body{margin:0;background:#FDF9FB;color:#322931;font-family:-apple-system,'Segoe UI',"
            "'Microsoft YaHei',sans-serif}.wrap{max-width:1080px;margin:0 auto;padding:24px 20px}"
            ".panel{background:#fff;border-radius:16px;box-shadow:0 2px 12px rgba(50,41,49,.05);"
            "padding:16px 18px;margin-bottom:18px}h1{font-size:20px;margin:0 0 14px}h2{font-size:14px;margin:0 0 12px}"
            ".chart{width:100%%;height:220px}table{width:100%%;border-collapse:collapse;font-size:13px}"
            "th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #EFE8EC}th{color:#8A7C85;font-size:12px}"
            "a{color:#C93470;text-decoration:none}.mono{font-family:Consolas,monospace}</style></head><body><div class='wrap'>"
            "<h1>37AC 训练对比（最近 %d 次）</h1>"
            "<div class='panel'><h2>验证准确率对比（横轴=轮次序）</h2>%s<div style='margin-top:10px'>%s</div></div>"
            "<div class='panel'><h2>Run 清单</h2><table><thead><tr><th>Run</th><th>基模</th><th>尺寸</th>"
            "<th>batch</th><th>类别</th><th>best val</th><th>状态</th><th>轮数</th></tr></thead><tbody>%s</tbody>"
            "</table></div><p style='color:#8A7C85;font-size:12px;text-align:center'>生成于 %s</p>"
            "</div></body></html>" % (len(rows), "".join(svg), legend, "".join(rows), _now()))
    out_path = Path(REPORT_DIR) / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    logger.info("对比页已生成: %s（%d 个 run）", out_path, len(rows))
    return str(out_path)


def list_runs(limit: int = 20) -> list:
    root = Path(REPORT_DIR)
    if not root.is_dir():
        return []
    runs = [d for d in root.iterdir() if d.is_dir() and (d / "progress.json").exists()]
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"dir": str(p), "run_id": p.name, "report": str(p / "index.html")} for p in runs[:limit]]


def latest_run() -> dict:
    runs = list_runs(1)
    return runs[0] if runs else None
