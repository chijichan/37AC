"""共享 JSON 消息通信协议（CLI 节点与 Server 服务端共用）

自定义消息头长度前缀协议：
    "<header>@<content_length>" + JSON 内容
发送方 header 与期望接收的 header 由构造参数指定：
- 服务端: send_header="server", expected_headers=["node"]
- 节点端: send_header="node",   expected_headers=["server"]
"""

import json
import struct

from common.constants import (
    MAX_MARKER_ITERATIONS,
    MAX_MESSAGE_CONTENT_LENGTH,
    PROTOCOL_HEADER_NODE,
    PROTOCOL_HEADER_SERVER,
    RECV_CHUNK_SIZE,
    RECV_FULL_CHUNK_SIZE,
)
from common.log_config import get_logger

logger = get_logger("json_protocol")


class JsonProtocol:
    """JSON 消息发送和接收类，使用自定义消息头长度前缀协议"""

    def __init__(self, send_header: str = PROTOCOL_HEADER_NODE,
                 expected_headers: list[str] | None = None):
        self.send_header = send_header
        self.expected_headers = expected_headers or [PROTOCOL_HEADER_SERVER]
        self._recv_buffer = b""  # 保存 recv 未消费完的溢出数据

    def send_json(self, sock, msg_dict: dict):
        """发送一条 JSON 消息到 socket"""
        try:
            json_str = json.dumps(msg_dict)
            json_bytes = json_str.encode("utf-8")

            content_length = len(json_bytes)
            header_str = f"{self.send_header}@{content_length}"
            header_bytes = header_str.encode("utf-8")

            full_message = header_bytes + json_bytes
            sock.sendall(full_message)

            logger.debug(
                "发送成功: 头部='%s', 内容长度=%s", header_str, content_length
            )
        except Exception as e:
            logger.error("发送失败: %s", e)
            raise

    def recv_json(self, sock):
        """从 socket 接收一条完整的 JSON 消息"""
        try:
            # 1. 查找消息标记
            found_marker, found_header, buffer = self._find_message_marker(sock)
            if not found_marker:
                return None

            # 2. 解析内容长度
            content_length, content_start = self._parse_content_length(
                found_marker, buffer
            )
            if content_length is None:
                return None

            # 3. 接收完整内容
            data = self._receive_full_content(
                sock, buffer, content_start, content_length
            )
            if data is None:
                return None

            # 4. 解码并返回 JSON
            return self._decode_json(data, found_header)

        except (ConnectionError, ValueError, struct.error) as e:
            logger.debug(
                "接收 JSON 失败 (期望标记: %s): %s", self.expected_headers, e
            )
            return None
        # socket.timeout 不在此处捕获，由主循环 except socket.timeout 统一处理

    def _find_message_marker(self, sock):
        """查找消息标记（带最大迭代保护，防止垃圾数据导致无限循环）"""
        expected_markers = [
            f"{header}@".encode("utf-8") for header in self.expected_headers
        ]
        # 从余留缓冲区开始，避免上次未消费完的数据丢失
        buffer = self._recv_buffer
        self._recv_buffer = b""
        max_marker_len = max(len(marker) for marker in expected_markers)
        max_iterations = MAX_MARKER_ITERATIONS
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            chunk = sock.recv(RECV_CHUNK_SIZE)
            if not chunk:
                return None, None, None

            buffer += chunk

            # 检查所有可能的标记
            for marker in expected_markers:
                marker_pos = buffer.find(marker)
                if marker_pos != -1:
                    buffer = buffer[marker_pos:]
                    found_header = marker[:-1].decode("utf-8")
                    return marker, found_header, buffer

            # 缓冲区过大仍未找到标记，丢弃已接收数据重新搜索。
            # 保留末尾可能存在的半截 marker，避免 header 跨 chunk 时被清掉。
            if len(buffer) > max_marker_len * 2:
                logger.debug(
                    "未找到期望标记 %s，清空缓冲区重新搜索", self.expected_headers
                )
                keep = max_marker_len - 1
                buffer = buffer[-keep:] if keep > 0 else b""

        logger.warning(
            "连续 %s 次未找到期望标记 %s，放弃并返回 None",
            max_iterations, self.expected_headers,
        )
        return None, None, None

    def _parse_content_length(self, marker, buffer):
        """解析内容长度"""
        length_start = len(marker)
        num_buffer = b""

        for i in range(length_start, len(buffer)):
            char_byte = buffer[i : i + 1]
            try:
                char = char_byte.decode("utf-8")
                if char.isdigit():
                    num_buffer += char_byte
                else:
                    break
            except UnicodeDecodeError:
                break

        if not num_buffer:
            logger.error(
                "无法解析长度数字，找到标记: '%s@'",
                marker[:-1].decode("utf-8"),
            )
            return None, None

        content_length = int(num_buffer.decode("utf-8"))
        content_start = length_start + len(num_buffer)
        return content_length, content_start

    def _receive_full_content(self, sock, buffer, content_start, content_length):
        """接收完整内容，余留数据存入 _recv_buffer 供下次使用"""
        if content_length > MAX_MESSAGE_CONTENT_LENGTH:
            raise ValueError(f"消息内容长度过大: {content_length}")

        data = buffer[content_start:]

        while len(data) < content_length:
            remaining = content_length - len(data)
            part = sock.recv(min(remaining, RECV_FULL_CHUNK_SIZE))
            if not part:
                raise ConnectionError("连接中断，未能接收完整 JSON 数据")
            data += part

        # 保存本次未消费完的溢出数据，防止丢失后续消息头
        self._recv_buffer = data[content_length:]
        return data[:content_length]

    def _decode_json(self, data, found_header):
        """解码 JSON 并添加来源信息"""
        text = data.decode("utf-8")
        result = json.loads(text)
        result["_source_header"] = found_header
        return result


# 模块级全局实例：服务端与节点端各一个
server_json_protocol = JsonProtocol(
    send_header=PROTOCOL_HEADER_SERVER,
    expected_headers=[PROTOCOL_HEADER_NODE],
)
node_json_protocol = JsonProtocol(
    send_header=PROTOCOL_HEADER_NODE,
    expected_headers=[PROTOCOL_HEADER_SERVER],
)
