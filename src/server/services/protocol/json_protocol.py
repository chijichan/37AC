"""
JSON 消息通信协议模块（兼容层）

实现已统一提取到 src/common/protocol.py，此处仅 re-export 服务端实例，
保持既有 import 路径（services.protocol.json_protocol）不变。
"""

from common.protocol import JsonProtocol, server_json_protocol as json_protocol

__all__ = ["JsonProtocol", "json_protocol"]

