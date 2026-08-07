"""共享加密/哈希工具 - 节点 token、API Key 等的一致性哈希与验证"""

import hashlib
import hmac
import secrets


def sha256_hex(text: str) -> str:
    """对字符串进行 SHA-256 哈希，返回 64 位十六进制字符串"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_node_token(token: str) -> str:
    """对节点 token 进行 SHA-256 哈希（DB 中只存哈希，不存明文）"""
    return sha256_hex(token)


def verify_node_token(token: str, stored_hash: str) -> bool:
    """时序安全地校验节点 token（hmac.compare_digest 防时序攻击）"""
    if not token or not stored_hash:
        return False
    expected = hash_node_token(token)
    return hmac.compare_digest(expected, stored_hash)


def generate_node_token() -> tuple[str, str]:
    """生成随机节点 token，返回 (raw_token, token_hash) 元组。

    raw_token 仅在创建时返回一次给调用方，DB 中只存 token_hash。
    """
    raw_token = secrets.token_urlsafe(32)
    return raw_token, hash_node_token(raw_token)
