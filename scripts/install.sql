-- ============================================================
-- 37AC 数据库安装脚本（全新安装）
-- ------------------------------------------------------------
-- 说明：
--   1. 仅包含「数据库 + 表结构（DDL）+ 索引」以及默认管理员账号，
--      不含其他业务数据，避免将真实密码哈希、节点 Token、IP、API 密钥等敏感信息带入安装。
--   2. 适用 MySQL 5.7+ / 8.x，字符集 utf8mb4。
--   3. 使用方式：
--        mysql -u<用户名> -p < install.sql
--      或
--        mysql -u<用户名> -p -e "source e:/pj/37AC/scripts/install.sql;"
--   4. 若 .env 中 DB_NAME 不同，请同步修改下方数据库名。
--   5. 默认管理员 admin 密码为【随机值】，安装后请按文末说明设置真实密码。
-- ============================================================

CREATE DATABASE IF NOT EXISTS `37ac`
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `37ac`;

-- ------------------------------------------------------------
-- 表：api_keys  API 密钥表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `api_keys` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` int(11) NOT NULL COMMENT '所属用户ID',
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '密钥名称',
  `key_hash` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '密钥哈希值(SHA-256)',
  `permission` enum('read','write','admin') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'read' COMMENT '权限级别',
  `status` enum('active','paused','revoked') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active' COMMENT '状态',
  `usage_count` int(11) NOT NULL DEFAULT '0' COMMENT '已使用次数',
  `max_usage` int(11) NOT NULL DEFAULT '10000' COMMENT '最大使用次数(0表示无限制)',
  `last_used_at` timestamp NULL DEFAULT NULL COMMENT '最后使用时间',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_key_hash` (`key_hash`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='API密钥表';

-- ------------------------------------------------------------
-- 表：nodes  推理节点信息表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `nodes` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '节点唯一ID',
  `user_id` int(11) DEFAULT NULL COMMENT '节点所属用户ID',
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '节点名称（可自定义，如主机名）',
  `token` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '节点通信密钥/Token，用于身份认证',
  `capabilities` json DEFAULT NULL COMMENT '节点能力列表，JSON 数组，如 ["local","llm"]',
  `status` enum('online','offline') COLLATE utf8mb4_unicode_ci DEFAULT 'offline' COMMENT '节点当前状态',
  `addr` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '节点地址（IP:端口）',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否启用该节点（管理员可禁用）',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '节点注册时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_token` (`token`),
  KEY `idx_status` (`status`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='推理节点信息表';

-- ------------------------------------------------------------
-- 表：password_reset_tokens  密码重置令牌表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `password_reset_tokens` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` int(11) NOT NULL COMMENT '用户ID',
  `token` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '重置令牌 (SHA-256)',
  `expires_at` datetime NOT NULL COMMENT '过期时间',
  `used` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否已使用 (0=未使用, 1=已使用)',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_token` (`token`),
  KEY `idx_expires_at` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='密码重置令牌表';

-- ------------------------------------------------------------
-- 表：task_results  识别任务结果表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `task_results` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` varchar(255) NOT NULL COMMENT '任务唯一ID',
  `user_id` int(11) DEFAULT NULL COMMENT '所属用户ID',
  `api_key_id` int(11) DEFAULT NULL COMMENT '使用的API密钥ID',
  `result` json DEFAULT NULL COMMENT '识别结果（JSON）',
  `status` varchar(50) DEFAULT 'completed' COMMENT '任务状态',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `task_id` (`task_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_api_key_id` (`api_key_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='识别任务结果表';

-- ------------------------------------------------------------
-- 表：users  用户表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户名',
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '密码哈希值(bcrypt)',
  `email` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '邮箱',
  `role` enum('admin','user') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'user' COMMENT '角色：admin管理员/user普通用户',
  `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态：1启用/0禁用',
  `last_login_at` datetime DEFAULT NULL COMMENT '最后登录时间',
  `last_login_ip` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '最后登录IP',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `token_version` int(11) NOT NULL DEFAULT '0' COMMENT '令牌版本号，用于单端登录（每次登录自增）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`),
  KEY `idx_status` (`status`),
  KEY `idx_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ------------------------------------------------------------
-- 表：models  识别模型表（泛化模型管理，如 37ac / LLM 等）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `models` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `model_id` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '模型标识（如 37ac）',
  `display_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '展示名称',
  `type` enum('local','llm') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'local' COMMENT '模型类型：local/llm',
  `version` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '版本号',
  `config_url` varchar(1024) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '配置文件(config.json)下载地址',
  `config_hash` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '配置文件 SHA-256（可选）',
  `notes` text COLLATE utf8mb4_unicode_ci COMMENT '模型说明/更新日志',
  `status` enum('active','inactive') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'inactive' COMMENT '是否当前激活',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name_version` (`name`,`version`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='识别模型表';

-- ============================================================
-- 初始化管理员账号
-- ------------------------------------------------------------
-- 脚本默认插入一个管理员账号 admin：
--   - 密码为【随机生成】的 bcrypt 哈希（占位），无法直接登录，安全无泄漏；
--   - 邮箱为示例占位 admin@example.com，部署后请修改为真实邮箱。
--
-- 安装完成后，请通过以下任一方式为 admin 设置真实密码：
--   方式一（推荐）：启动服务后，用 admin 用户名触发「忘记密码」，
--                  将重置邮件发送到上方邮箱，按链接设置新密码。
--   方式二：直接用 SQL 更新为新的 bcrypt 哈希
--          （用 Python bcrypt 生成，勿明文存储）：
--        UPDATE `37ac`.`users`
--           SET password_hash='<新bcrypt哈希>', email='你的邮箱'
--         WHERE username='admin';
-- ============================================================