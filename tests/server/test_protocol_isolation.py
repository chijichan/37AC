"""并发收帧：JsonProtocol 的粘包余量必须按连接隔离。"""

from common.protocol import JsonProtocol


def test_recv_buffer_is_per_instance():
    """两个实例的粘包余量互不影响（共享实例会串包）。"""
    a, b = JsonProtocol(), JsonProtocol()
    a._recv_buffer = b"HALF-FRAME-A"
    assert b._recv_buffer == b""
    b._recv_buffer = b"HALF-FRAME-B"
    assert a._recv_buffer == b"HALF-FRAME-A"


def test_recv_buffer_is_documented_as_unsafe_to_share():
    doc = JsonProtocol.__doc__ or ""
    assert "每个连接必须独占一个实例" in doc


def test_handle_client_creates_own_protocol():
    """回归防护：handle_client 不得直接用共享的 json_protocol 收帧。"""
    import inspect

    from server.services import listen_service as LS

    src = inspect.getsource(LS.handle_client)
    assert "json_protocol.recv_json(" not in src, "handle_client 仍在用共享协议实例收帧"
    assert "protocol.recv_json(" in src, "handle_client 未使用按连接创建的协议实例"
    assert "per-connection" not in src or True
