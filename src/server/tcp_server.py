import socket
import threading
import logging
import json
import time
import os
from datetime import datetime
import pymysql
from pymysql import Error
import config
import struct  # ✅ 新增：用于长度前缀打包与解包

# =============================================
# 0. 日志配置
# =============================================
logger = logging.getLogger("tcp_server_logger")
if config.TSAC_DEBUG:
    log_level = logging.DEBUG
else:
    log_level = logging.INFO
logger.setLevel(log_level)

file_handler = logging.FileHandler("./logs/tcp_server_logger.log")
console_handler = logging.StreamHandler()

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# =============================================
# 1. 数据库配置
# =============================================
DB_CONFIG = config.DB_CONFIG

# =============================================
# 2. 节点管理器
# =============================================
class NodeManager:
    def __init__(self):
        self.nodes = {}  # node_id -> dict
        self.lock = threading.Lock()

    def register_node(self, node_id, addr, socket_obj=None):
        with self.lock:
            self.nodes[node_id] = {
                'addr': addr,
                'socket': socket_obj,
                'last_heartbeat': time.time(),
                'status': 'idle'
            }
            logger.debug(f"[节点注册] 节点 {node_id} ({addr}) 已注册，状态：空闲")
            return True

    def update_heartbeat(self, node_id):
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id]['last_heartbeat'] = time.time()
                return True
            return False

    def set_node_busy(self, node_id):
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id]['status'] = 'busy'
                return True
            return False

    def set_node_idle(self, node_id):
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id]['status'] = 'idle'
                return True
            return False

    def get_idle_node(self):
        with self.lock:
            for node_id, info in self.nodes.items():
                if info['status'] == 'idle' and info.get('socket') is not None:
                    return node_id, info
        return None, None

    def get_node_socket(self, node_id):
        with self.lock:
            node = self.nodes.get(node_id)
            if node and node.get('socket'):
                return node['socket']
        return None

    def cleanup_nodes(self, timeout=30):
        current_time = time.time()
        to_remove = []
        with self.lock:
            for node_id, info in self.nodes.items():
                if current_time - info['last_heartbeat'] > timeout:
                    logger.debug(f"[节点清理] 节点 {node_id} 超时未心跳，将被移除")
                    to_remove.append(node_id)
            for node_id in to_remove:
                del self.nodes[node_id]

    def show_all_nodes(self):
        with self.lock:
            logger.debug("\n" + "="*50)
            logger.debug("[节点监控] 当前所有节点信息:")
            logger.debug("="*50)
            for node_id, info in self.nodes.items():
                addr = info.get('addr', ('Unknown', 0))
                ip, port = addr
                status = info.get('status', 'N/A')
                last_hb = info.get('last_heartbeat', 'N/A')
                ts_str = datetime.fromtimestamp(last_hb).strftime('%Y-%m-%d %H:%M:%S') if isinstance(last_hb, (int, float)) else str(last_hb)
                logger.debug(f"     节点ID: {node_id} | 地址: {ip}:{port} | 状态: {status} | 最后心跳: {ts_str}")
            logger.debug("="*50 + "\n")

# =============================================
# 3. 全局节点管理器
# =============================================
node_manager = NodeManager()

# =============================================
# 4. 数据库工具
# =============================================
def get_db_connection():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"[DB] 数据库连接失败: {e}")
        return None

# =============================================
# 5. 工具函数：JSON 长度前缀协议
# =============================================
def send_json(sock, msg_dict):
    """
    发送一条 JSON 消息到 socket，使用长度前缀协议
    """
    try:
        json_str = json.dumps(msg_dict)
        json_bytes = json_str.encode('utf-8')
        length_prefix = struct.pack('>I', len(json_bytes))  # 大端序 uint32，4 字节
        sock.sendall(length_prefix + json_bytes)
    except Exception as e:
        print(f"[send_json] 发送失败: {e}")
        raise

def recv_json(sock):
    """
    从 socket 接收一条完整的 JSON 消息（长度前缀协议）
    返回解析后的字典，如果失败或连接断开，返回 None
    """
    try:
        # 1. 接收 4 字节，表示 body 长度
        raw_len = sock.recv(4)
        if not raw_len:
            return None

        length = struct.unpack('>I', raw_len)[0]

        # 2. 按长度接收完整 body
        data = b''
        while len(data) < length:
            part = sock.recv(length - len(data))
            if not part:
                raise ConnectionError("连接中断，未能接收完整 JSON 数据")
            data += part

        # 3. 解码并解析
        text = data.decode('utf-8')
        return json.loads(text)

    except (ConnectionError, json.JSONDecodeError, UnicodeDecodeError, struct.error) as e:
        print(f"[recv_json] 接收 JSON 失败: {e}")
        return None

# =============================================
# 6. 任务分发（供外部调用，如 views.py）
# =============================================
def dispatch_task(image_path: str, image_data, task_id: str):
    """
    优先通过 TCP 将 image_file（图片二进制）发送给节点，
    同时保留将图片保存到 ./uploads/ 的逻辑（备用）
    """
    # === 可选：备份逻辑 ===
    # 如果您想把图片也保存到服务端的 ./uploads/，可以取消下面的注释
    """
    import os
    uploads_dir = './uploads'
    os.makedirs(uploads_dir, exist_ok=True)
    backup_image_path = os.path.join(uploads_dir, os.path.basename(image_path))
    with open(backup_image_path, 'wb') as f:
        if hasattr(image_file, 'read'):  # 比如 request.files 的 FileStorage 对象
            f.write(image_file.read())
        else:  # 如果是二进制数据，比如 bytes
            f.write(image_file)
    print(f"[服务端] 图片已备份到本地: {backup_image_path}")
    """

    # === 优先：通过 TCP 传输图片给节点 ===
    node_id, node_info = node_manager.get_idle_node()
    if not node_id:
        return {'status': 'waiting', 'task_id': task_id, 'message': '没有空闲节点'}

    socket_obj = node_info.get('socket')
    if not socket_obj:
        node_manager.set_node_idle(node_id)
        return {'status': 'failed', 'task_id': task_id, 'error': '节点未连接'}

    try:
        # 1. 构造任务消息头部（JSON）
        image_filename = os.path.basename(image_path)  # 如 '6a67fa40-de07-41d6-a21f-2a8479d7747e.jpg'

        task_msg = {
            'type': 'task',
            'task_id': task_id,
            'has_image': True,
            'image_filename': image_filename,  # 告诉节点图片保存时的文件名
            'image_size': len(image_data)
        }

        # 2. 发送任务消息 JSON
        send_json(socket_obj, task_msg)
        # socket_obj.sendall(json.dumps(task_msg).encode('utf-8'))

        # 3. 发送图片二进制数据
        socket_obj.sendall(image_data)

        # 4. 标记节点为忙碌
        node_manager.set_node_busy(node_id)

        return {
            'status': 'dispatched',
            'task_id': task_id,
            'node_id': node_id
        }

    except Exception as e:
        node_manager.set_node_idle(node_id)
        return {
            'status': 'failed',
            'task_id': task_id,
            'error': str(e)
        }

# =============================================
# 7. TCP 服务端核心逻辑
# =============================================
def handle_client(conn, addr):
    print(f"[TCP] 新连接来自: {addr}")
    node_id = None

    try:
        while True:
            msg = recv_json(conn)  # ✅ 使用安全的 recv_json()，替代 conn.recv + json.loads
            if msg is None:
                break  # 客户端断开或数据错误

            msg_type = msg.get('type')

            if msg_type == 'register':
                node_id = msg.get('node_id')
                token = msg.get('token')
                if not node_id or not token:
                    # conn.sendall(json.dumps({'type': 'register_ack', 'status': 'error', 'message': 'node_id 和 token 必须提供'}).encode('utf-8'))
                    register_ack = {
                        'type': 'register_ack', 'status': 'error', 'message': 'node_id 和 token 必须提供'
                    }
                    send_json(conn, register_ack)
                    continue

                conn_db = get_db_connection()
                if not conn_db:
                    # conn.sendall(json.dumps({'type': 'register_ack', 'status': 'error', 'message': '数据库错误'}).encode('utf-8'))
                    register_ack = {
                        'type': 'register_ack', 'status': 'error', 'message': '数据库错误'
                    }
                    send_json(conn, register_ack)
                    continue

                try:
                    cursor = conn_db.cursor(pymysql.cursors.DictCursor)
                    query = """
                        SELECT * FROM nodes 
                        WHERE id = %s AND token = %s AND status = 'online'
                    """
                    cursor.execute(query, (node_id, token))
                    result = cursor.fetchone()

                    if result:
                        node_manager.register_node(node_id, addr, conn)
                        node_manager.set_node_idle(node_id)
                        # conn.sendall(json.dumps({'type': 'register_ack', 'status': 'success', 'message': '节点注册成功'}).encode('utf-8'))
                        register_ack = {
                            'type': 'register_ack', 'status': 'success', 'message': '节点注册成功'
                        }
                        send_json(conn, register_ack)
                        print(f"[注册成功] node_id={node_id}, addr={addr}")
                    else:
                        register_ack = {
                            'type': 'register_ack', 'status': 'error', 'message': '节点未激活或凭证无效'
                        }
                        # conn.sendall(json.dumps({'type': 'register_ack', 'status': 'error', 'message': '节点未激活或凭证无效'}).encode('utf-8'))
                finally:
                    if conn_db:
                        cursor.close()
                        conn_db.close()

            elif msg_type == 'heartbeat':
                if node_id:
                    node_manager.update_heartbeat(node_id)
                    # conn.sendall(json.dumps({'type': 'heartbeat_ack', 'status': 'success', 'message': '心跳已更新'}).encode('utf-8'))
                    heartbeat_ack = {
                        'type': 'heartbeat_ack', 'status': 'success', 'message': '心跳已更新'
                    }
                    send_json(conn, heartbeat_ack)
                else:
                    # conn.sendall(json.dumps({'type': 'heartbeat_ack', 'status': 'error', 'message': '未注册的节点'}).encode('utf-8'))
                    heartbeat_ack = {
                        'type': 'heartbeat_ack', 'status': 'error', 'message': '未注册的节点'
                    }
                    send_json(conn, heartbeat_ack)

            elif msg_type == 'task':
                if not node_id:
                    # conn.sendall(json.dumps({'type': 'task', 'status': 'error', 'message': '未注册的节点无法接收任务'}).encode('utf-8'))
                    task = {
                        'type': 'task', 'status': 'error', 'message': '未注册的节点无法接收任务'
                    }
                    send_json(conn, task)
                    continue
                task_id = msg.get('task_id')
                image_path = msg.get('image_path')
                if not task_id or not image_path:
                    # conn.sendall(json.dumps({'type': 'task', 'status': 'error', 'message': '任务参数不完整'}).encode('utf-8'))
                    task = {
                        'type': 'task', 'status': 'error', 'message': '任务参数不完整'
                    }
                    send_json(conn, task)
                    continue
                if node_manager.set_node_busy(node_id):
                    response_msg = {'type': 'task', 'task_id': task_id, 'image_path': image_path}
                    send_json(conn, response_msg)
                    # conn.sendall(json.dumps(response_msg).encode('utf-8'))
                    print(f"[任务分发] 任务 {task_id} -> 节点 {node_id}")
                else:
                    # conn.sendall(json.dumps({'type': 'task', 'status': 'error', 'message': '节点繁忙'}).encode('utf-8'))
                    task = {
                        'type': 'task', 'status': 'error', 'message': '节点繁忙'
                    }
                    send_json(conn, task)

            elif msg_type == 'task_result':
                node_id = msg.get('node_id')
                task_id = msg.get('task_id')
                result = msg.get('result')

                print(f"[TCP服务端] 收到任务结果: task_id={task_id}, result={result}")

                try:
                    mysql_conn = get_db_connection()
                    with mysql_conn.cursor() as cursor:
                        sql = """
                        INSERT INTO task_results (task_id, result, status)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            result = VALUES(result),
                            status = VALUES(status),
                            updated_at = CURRENT_TIMESTAMP
                        """
                        cursor.execute(sql, (task_id, json.dumps(result), 'completed'))
                    mysql_conn.commit()
                    print(f"[MySQL] 任务结果已保存: task_id={task_id}")

                    node_manager.set_node_idle(node_id)
                except Exception as e:
                    print(f"[MySQL] 保存任务结果失败: {e}")
                finally:
                    if mysql_conn:
                        mysql_conn.close()

            else:
                conn.sendall(json.dumps({'type': 'msg', 'status': 'error', 'message': '未知消息类型'}).encode('utf-8'))

    except ConnectionResetError:
        print(f"[连接断开] {addr}")
    finally:
        if node_id:
            with node_manager.lock:
                if node_id in node_manager.nodes:
                    node_manager.nodes[node_id]['status'] = 'offline'
        conn.close()
        print(f"[TCP] 连接关闭: {addr}")

# =============================================
# 8. 启动 TCP 服务
# =============================================
def start_tcp_server(host='0.0.0.0', port=config.TCP_PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(5)
        print(f"[TCP] 服务启动，监听 {host}:{port}")

        def cleanup_loop():
            while True:
                time.sleep(30)
                node_manager.cleanup_nodes()

        threading.Thread(target=cleanup_loop, daemon=True).start()

        def monitor_nodes():
            monitor_counter = 0
            while True:
                time.sleep(5)
                monitor_counter += 1
                logger.debug(f"[MONITOR] 第 {monitor_counter} 次节点监控")
                node_manager.show_all_nodes()

        threading.Thread(target=monitor_nodes, daemon=True).start()

        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

# =============================================
# 9. 启动入口（测试用，可直接注释）
# =============================================
# if __name__ == '__main__':
#     start_tcp_server()