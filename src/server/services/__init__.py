"""服务模块 - 提供各类业务服务的统一访问入口"""

from services.auth import (
    hash_password,
    verify_password,
    create_jwt_token,
    decode_jwt_token,
    validate_email,
    validate_username,
    validate_password,
)
from services.user_service import (
    get_user_by_id,
    update_profile,
    get_users,
    create_user,
    update_user,
    delete_user,
    update_user_role,
    update_user_status,
)
from services.protocol import json_protocol
from services.node_manager import NodeManager, get_db_connection, node_manager
from services.task_manager import TaskManager, task_manager
from services.async_processor import (
    AsyncTaskProcessor,
    MessageTypeProcessor,
    async_processor,
    message_type_processor,
)
from services.message_handlers import (
    async_handle_register,
    async_handle_heartbeat,
    async_handle_task_result,
    async_handle_unknown_message,
)
from services.task_dispatcher import dispatch_task
from services.email_service import (
    send_email,
    send_password_reset_email,
    is_configured,
)
from services.sse_bus import SSEBus, sse_bus

__all__ = [
    # auth
    "hash_password",
    "verify_password",
    "create_jwt_token",
    "decode_jwt_token",
    "validate_email",
    "validate_username",
    "validate_password",
    # user
    "get_user_by_id",
    "update_profile",
    "get_users",
    "create_user",
    "update_user",
    "delete_user",
    "update_user_role",
    "update_user_status",
    # protocol
    "json_protocol",
    # node
    "NodeManager",
    "node_manager",
    "get_db_connection",
    # task
    "TaskManager",
    "task_manager",
    # async
    "AsyncTaskProcessor",
    "MessageTypeProcessor",
    "async_processor",
    "message_type_processor",
    # message handlers
    "async_handle_register",
    "async_handle_heartbeat",
    "async_handle_task_result",
    "async_handle_unknown_message",
    # dispatcher
    "dispatch_task",
    # email
    "send_email",
    "send_password_reset_email",
    "is_configured",
    # sse
    "SSEBus",
    "sse_bus",
]
