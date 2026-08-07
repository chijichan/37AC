"""共享常量 - CLI 与 Server 统一使用，避免各模块重复定义魔术字符串"""

# ── 图片扩展名 ──
# 预测/检测/验证用的基础扩展名（与原各模块行为保持一致）
IMAGE_EXTENSIONS_BASIC = (".jpg", ".jpeg", ".png", ".jfif")

# 上传/保存白名单（node_service 与 upload_routes 的并集）
ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".jfif",
    ".bmp",
    ".gif",
}

# ── 协议相关 ──
# JSON 消息头前缀
PROTOCOL_HEADER_SERVER = "server"
PROTOCOL_HEADER_NODE = "node"

# 接收缓冲块大小
RECV_CHUNK_SIZE = 1024
RECV_FULL_CHUNK_SIZE = 4096
# 查找消息标记的最大迭代次数（防止垃圾数据导致无限循环）
MAX_MARKER_ITERATIONS = 50

# ── 节点服务 ──
# 节点默认能力（JSON 数组字符串，与 DB 存储格式一致）
DEFAULT_CAPABILITIES = '["local"]'
# 节点默认最大任务数
DEFAULT_MAX_TASKS = 5
