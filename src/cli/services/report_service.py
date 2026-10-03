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


def set_status(status: str, note: str = "") -> None:
    if _data() is None:
        return
    _data()["status"] = status
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
        (Path(folder) / "index.html").write_text(render_html(data), encoding="utf-8")
    except Exception as e:                     # 渲染失败不能影响训练
        logger.warning("报告渲染失败: %s", e)


def _fmt_duration(sec) -> str:
    sec = int(sec or 0)
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return ("%d:%02d:%02d" % (h, m, s)) if h else ("%02d:%02d" % (m, s))


def _svg_line(values, width=560, height=140, color="#DE4F8D", fill="rgba(222,79,141,.10)"):
    """把一串数值画成内联 SVG 折线（零依赖）→ 返回 svg 字符串。"""
    if not values:
        return '<div class="empty">暂无数据</div>'
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = 8 + (width - 16) * (i / max(1, n - 1))
        y = height - 8 - (height - 16) * ((v - lo) / span)
        pts.append("%.1f,%.1f" % (x, y))
    area = "8,%.1f %s %.1f,%.1f" % (height - 8, " ".join(pts), width - 8, height - 8)
    return (
        '<svg class="chart" viewBox="0 0 %d %d" preserveAspectRatio="none">'
        '<polygon points="%s" fill="%s"/>'
        '<polyline points="%s" fill="none" stroke="%s" stroke-width="2"/>'
        "</svg>" % (width, height, area, fill, " ".join(pts), color)
    )


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
.chart{width:100%;height:140px;display:block}
.empty{color:var(--ink300);font-size:13px;padding:24px 0;text-align:center}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--ink100)}
th{color:var(--ink500);font-weight:700;font-size:12px}
tbody tr:hover{background:var(--surface2)}
.ev{font-size:13px;color:var(--ink700);padding:6px 0;border-bottom:1px dashed var(--ink100)}
.ev .t{color:var(--ink500);margin-right:10px}
footer{color:var(--ink500);font-size:12px;text-align:center;margin-top:24px}
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
  <div class="panel"><h2>验证准确率（每轮 %）</h2>$chart_val</div>
  <div class="panel"><h2>训练损失（每轮）</h2>$chart_loss</div>
</div>

<div class="panel"><h2>每轮明细</h2>$epoch_table</div>
<div class="panel"><h2>真实口径评估</h2>$eval_panel</div>
<div class="panel"><h2>检查点</h2>$ckpt_table</div>
<div class="panel"><h2>事件</h2>$events</div>

<footer>数据源 progress.json ｜ 生成于 $generated_at ｜ 每 $refresh 秒自动刷新</footer>
</div></body></html>
""")


def render_html(data: dict) -> str:
    meta = data.get("meta") or {}
    cards = []
    for k, v in (("基模", meta.get("base")), ("类别数", meta.get("classes")),
                 ("训练/验证", "%s / %s" % (meta.get("train"), meta.get("val"))),
                 ("batch", meta.get("batch")), ("分辨率", meta.get("image_size")),
                 ("设备", meta.get("device")), ("best val", data.get("best_val"))):
        if v in (None, ""):
            continue
        cards.append('<div class="card"><div class="k">%s</div><div class="v">%s</div></div>' % (k, v))

    epochs = data.get("epochs") or []
    val_series = [e["val_acc"] for e in epochs]
    loss_series = [e["loss"] for e in epochs]

    rows = []
    for e in reversed(epochs[-30:]):
        rows.append("<tr><td class='mono'>%s</td><td>%s</td><td class='mono'>%.4f</td>"
                    "<td class='mono'>%.2f%%</td><td class='mono'>%.2f%%</td>"
                    "<td class='mono'>%.0e</td><td class='mono'>%ss</td><td class='muted'>%s</td></tr>"
                    % (e["epoch"], e["phase"], e["loss"], e["train_acc"], e["val_acc"],
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
        ("预计剩余 %s" % _fmt_duration(eta)) if eta else "预计剩余计算中")

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
        chart_val=_svg_line(val_series, color="#DE4F8D", fill="rgba(222,79,141,.10)"),
        chart_loss=_svg_line(loss_series, color="#3E8FD9", fill="rgba(62,143,217,.10)"),
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
