-- =============================================
-- 37AC 数据库变更脚本
-- 1. nodes 表添加 user_id 字段
-- 2. nodes 表添加 capabilities 字段
-- 3. 创建 api_keys 表
-- 4. task_results 表添加 user_id 和 api_key_id 字段
-- 5. 创建 password_reset_tokens 表
-- 6. users 表添加 token_version 字段（单端登录）
-- =============================================

-- 6. users 表添加 token_version 字段
-- 单端登录：每次登录将 token_version 自增 1，写入 JWT payload，
-- 验证时比对，版本不一致则旧令牌立即失效（旧登录被踢下线）
ALTER TABLE users
    ADD COLUMN token_version INT(11) NOT NULL DEFAULT 0 COMMENT '令牌版本号，用于单端登录（每次登录自增）';

-- 1. nodes 表添加 user_id 字段
ALTER TABLE nodes
    ADD COLUMN user_id INT(11) DEFAULT NULL COMMENT '所属用户ID' AFTER id,
    ADD INDEX idx_user_id (user_id);

-- 2. nodes 表添加 capabilities 字段（节点能力标识，如 "local,llm"）
ALTER TABLE nodes
    ADD COLUMN capabilities JSON DEFAULT NULL COMMENT '节点能力列表，JSON 数组，如 ["local","llm"]' AFTER token;

-- 3. 创建 api_keys 表
CREATE TABLE IF NOT EXISTS api_keys (
    id INT(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    user_id INT(11) NOT NULL COMMENT '所属用户ID',
    name VARCHAR(100) NOT NULL COMMENT '密钥名称',
    key_hash VARCHAR(64) NOT NULL COMMENT '密钥哈希值(SHA-256)',
    permission ENUM('read', 'write', 'admin') NOT NULL DEFAULT 'read' COMMENT '权限级别',
    status ENUM('active', 'paused', 'revoked') NOT NULL DEFAULT 'active' COMMENT '状态',
    usage_count INT(11) NOT NULL DEFAULT 0 COMMENT '已使用次数',
    max_usage INT(11) NOT NULL DEFAULT 10000 COMMENT '最大使用次数(0表示无限制)',
    last_used_at TIMESTAMP NULL DEFAULT NULL COMMENT '最后使用时间',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    INDEX idx_user_id (user_id),
    INDEX idx_key_hash (key_hash),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='API密钥表';

-- 5. task_results 表添加 user_id 和 api_key_id 字段
ALTER TABLE task_results
    ADD COLUMN user_id INT(11) DEFAULT NULL COMMENT '所属用户ID' AFTER task_id,
    ADD COLUMN api_key_id INT(11) DEFAULT NULL COMMENT '使用的API密钥ID' AFTER user_id,
    ADD INDEX idx_user_id (user_id),
    ADD INDEX idx_api_key_id (api_key_id);

-- 6. 创建 password_reset_tokens 表
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INT(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    user_id INT(11) NOT NULL COMMENT '用户ID',
    token VARCHAR(128) NOT NULL COMMENT '重置令牌 (SHA-256)',
    expires_at DATETIME NOT NULL COMMENT '过期时间',
    used TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已使用 (0=未使用, 1=已使用)',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    INDEX idx_user_id (user_id),
    INDEX idx_token (token),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='密码重置令牌表';

-- 7. 创建 models 表（泛化识别模型管理）
CREATE TABLE IF NOT EXISTS models (
    id INT(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    model_id VARCHAR(50) NOT NULL COMMENT '模型标识（如 37ac）',
    display_name VARCHAR(100) NOT NULL DEFAULT '' COMMENT '展示名称',
    type ENUM('local','llm') NOT NULL DEFAULT 'local' COMMENT '模型类型：local/llm',
    version VARCHAR(64) NOT NULL COMMENT '版本号',
    config_url VARCHAR(1024) NOT NULL COMMENT '配置文件(config.json)下载地址',
    config_hash VARCHAR(64) NULL COMMENT '配置文件 SHA-256（可选）',
    notes TEXT COMMENT '模型说明/更新日志',
    status ENUM('active','inactive') NOT NULL DEFAULT 'inactive' COMMENT '是否当前激活',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_name_version (name, version),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='识别模型表';
