"""
JSON 消息通信协议模块
提供基于自定义消息头长度前缀协议的 JSON 消息发送和接收功能
"""

import json
import struct
from config.log_config import get_logger

logger = get_logger("json_protocol")


class JsonProtocol:
    """JSON 消息发送和接收类，使用自定义消息头长度前缀协议"""

    def __init__(self):
        self.send_header = "server"
        self.expected_headers = ["node"]
        self._recv_buffer = b""

    def send_json(self, sock, msg_dict):
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
            found_marker, found_header, buffer = self._find_message_marker(sock)
            if not found_marker:
                return None

            content_length, content_start = self._parse_content_length(found_marker, buffer)
            if content_length is None:
                return None

            data = self._receive_full_content(sock, buffer, content_start, content_length)
            if data is None:
                return None

            return self._decode_json(data, found_header)
        except (ConnectionError, ValueError, struct.error) as e:
            logger.debug("接收 JSON 失败 (期望标记: %s): %s", self.expected_headers, e)
            return None

    def _find_message_marker(self, sock):
        """查找消息标记"""
        expected_markers = [f"{header}@".encode("utf-8") for header in self.expected_headers]
        # 从余留缓冲区开始，避免上次未消费完的数据丢失
        buffer = self._recv_buffer
        self._recv_buffer = b""
        max_marker_len = max(len(marker) for marker in expected_markers)
        max_iterations = 50
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            chunk = sock.recv(1024)
            if not chunk:
                return None, None, None

            buffer += chunk

            for marker in expected_markers:
                marker_pos = buffer.find(marker)
                if marker_pos != -1:
                    buffer = buffer[marker_pos:]
                    found_header = marker[:-1].decode("utf-8")
                    return marker, found_header, buffer

            if len(buffer) > max_marker_len * 2:
                logger.warning("未找到期望标记 %s，清空缓冲区重新搜索", self.expected_headers)
                buffer = b""

        logger.warning("连续 %s 次未找到期望标记 %s，放弃", max_iterations, self.expected_headers)
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
            logger.error("无法解析长度数字，找到标记: '%s@'", marker[:-1].decode("utf-8"))
            return None, None

        content_length = int(num_buffer.decode("utf-8"))
        content_start = length_start + len(num_buffer)
        return content_length, content_start

    def _receive_full_content(self, sock, buffer, content_start, content_length):
        """接收完整内容，余留数据存入 _recv_buffer 供下次使用"""
        data = buffer[content_start:]

        while len(data) < content_length:
            remaining = content_length - len(data)
            part = sock.recv(min(remaining, 4096))
            if not part:
                raise ConnectionError("连接中断，未能接收完整 JSON 数据")
            data += part

        # 保存本次未消费完的溢出数据
        self._recv_buffer = data[content_length:]
        return data[:content_length]

    def _decode_json(self, data, found_header):
        """解码JSON并添加来源信息"""
        text = data.decode("utf-8")
        result = json.loads(text)
        result["_source_header"] = found_header
        return result


# 模块级全局实例
json_protocol = JsonProtocol()
