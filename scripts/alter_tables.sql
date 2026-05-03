-- =============================================
-- 37AC 数据库变更脚本
-- 1. nodes 表添加 user_id 字段
-- 2. 创建 api_keys 表
-- 3. task_results 表添加 user_id 和 api_key_id 字段
-- =============================================

-- 1. nodes 表添加 user_id 字段
ALTER TABLE nodes
    ADD COLUMN user_id INT(11) DEFAULT NULL COMMENT '所属用户ID' AFTER id,
    ADD INDEX idx_user_id (user_id);

-- 2. 创建 api_keys 表
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

-- 3. task_results 表添加 user_id 和 api_key_id 字段
ALTER TABLE task_results
    ADD COLUMN user_id INT(11) DEFAULT NULL COMMENT '所属用户ID' AFTER task_id,
    ADD COLUMN api_key_id INT(11) DEFAULT NULL COMMENT '使用的API密钥ID' AFTER user_id,
    ADD INDEX idx_user_id (user_id),
    ADD INDEX idx_api_key_id (api_key_id);

-- 4. 创建 password_reset_tokens 表
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
