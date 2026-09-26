"""YOLO 可用性诊断（detection/yolo_detector.py）回归测试。

背景：生产上 ultralytics 明明装了，却因为 opencv 缺 libGL 之类的系统库 import 失败，
旧代码统一报"ultralytics 未安装 (pip install ultralytics)"，把人带偏；
而且每张图都会重新 import、重复刷同一条 warning。
"""

from detection import yolo_detector as yd


def test_describe_missing_system_lib():
    exc = OSError("libGL.so.1: cannot open shared object file: No such file or directory")
    msg = yd._describe_import_error(exc)
    assert "libGL.so.1" in msg
    assert "libgl1" in msg
    assert "opencv-python-headless" in msg


def test_describe_missing_python_dependency():
    exc = ModuleNotFoundError("No module named 'cpuinfo'")
    exc.name = "cpuinfo"
    msg = yd._describe_import_error(exc)
    assert "cpuinfo" in msg and "pip install cpuinfo" in msg


def test_describe_plain_ultralytics_missing():
    exc = ModuleNotFoundError("No module named 'ultralytics'")
    exc.name = "ultralytics"
    msg = yd._describe_import_error(exc)
    assert "requirements.txt" in msg


def test_describe_cv2_import_error():
    exc = ImportError("DLL load failed while importing cv2")
    msg = yd._describe_import_error(exc)
    assert "opencv" in msg


def test_availability_is_cached(monkeypatch):
    calls = {"n": 0}

    def fake_import(name, *args, **kwargs):
        calls["n"] += 1
        if name == "cv2":
            raise OSError("libGL.so.1: cannot open shared object file")
        return __import__(name, *args, **kwargs)

    monkeypatch.setattr(yd, "_AVAILABILITY", {"checked": False, "ok": False, "reason": ""})
    monkeypatch.setattr("builtins.__import__", lambda name, *a, **k: fake_import(name, *a, **k))
    ok, reason = yd.check_yolo_available()
    assert ok is False and "libGL" in reason

    # 再问一次不该重新探测（避免每张图刷日志 / 重复付 import 代价）
    before = calls["n"]
    ok2, reason2 = yd.check_yolo_available()
    assert ok2 is False and reason2 == reason and calls["n"] == before


def test_detector_stops_retrying_after_failure(monkeypatch):
    monkeypatch.setattr(yd, "_AVAILABILITY", {"checked": True, "ok": False, "reason": "opencv 不可用（YOLO 依赖）：缺少系统库 libGL.so.1"})
    det = yd.YoloDetector()
    assert det._load_model() is False
    assert det.load_error and "libGL" in det.load_error
    assert det._load_failed is True

    # 第二次调用直接返回，不再走探测
    def boom():
        raise AssertionError("不应重新探测")
    monkeypatch.setattr(yd, "check_yolo_available", boom)
    assert det._load_model() is False
