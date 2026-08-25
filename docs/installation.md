# 安装与运行

### 1. 克隆仓库

```bash
git clone https://github.com/chijichan/37AC.git
cd 37AC
```

### 2. 创建并激活虚拟环境（推荐 Python 3.12）

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r src/cli/requirements.txt
pip install -r src/server/requirements.txt
```

> **AMD GPU (RX 580) 用户**：额外安装 DirectML 加速：
> ```bash
> pip install torch-directml
> # 然后在 .env 中设置 USE_DIRECTML=True
> ```

### 4. 配置数据库

```bash
mysql -u root -p < scripts/alter_tables.sql
```

编辑 `src/server/config/base.py`，配置数据库连接、JWT 密钥等。

也可通过 `src/server/.env` 文件配置（推荐）：

```env
# 服务端配置
DB_HOST=your_db_host
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name
JWT_SECRET=your-jwt-secret-key-change-this-in-production

# 节点配置（src/cli/.env）
NODE_ID=1
TOKEN=your_node_token
LLM_RECOGNITION_ENABLED=false
LLM_API_KEY=your_api_key

# PHP Web 配置（src/www/.env）
API_BASE_URL=http://127.0.0.1:13138
UPLOAD_API_KEY=your_upload_api_key   # 与后端 UPLOAD_API_KEYS 一致，仅存服务端
APP_DEBUG=false                      # 生产必须为 false
```

### 5. 启动 Flask 服务端

```bash
python src/server/runserver.py
```

