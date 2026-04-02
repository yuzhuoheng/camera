# Camera Server (云相机后端)

这是一个基于 FastAPI 构建的云相机应用后端服务，提供照片存储、相册管理、用户认证及分享功能。

## 技术栈

- **Web 框架**: [FastAPI](https://fastapi.tiangolo.com/)
- **数据库**: PostgreSQL (使用 SQLAlchemy ORM)
- **对象存储**: MinIO (用于存储照片文件)
- **认证**: JWT (JSON Web Tokens)
- **其他**: Pydantic, Pillow (图片处理)

## 功能特性

- **用户认证**: 支持账号密码注册/登录，以及微信小程序集成。
- **相册管理**: 创建、修改、删除相册。
- **照片管理**:
  - 图片上传至 MinIO 对象存储。
  - 支持按相册浏览照片。
  - 自动生成缩略图（计划中/依赖前端或服务端处理）。
- **分享功能**: 生成相册或照片的分享链接。

## 快速开始

### 1. 环境准备

确保本地已安装 Python 3.8+，并准备好 PostgreSQL 和 MinIO 服务（推荐使用 Docker 部署）。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

*注意：如果连接 PostgreSQL，可能还需要安装 `psycopg2-binary` 或相关驱动。*

### 3. 配置环境变量

复制 `.env.example` 文件为 `.env`，并填入实际配置：

```ini
# Database
POSTGRES_SERVER=localhost
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=camera_db
POSTGRES_PORT=5432

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=camera-server-photos
MINIO_SECURE=False

# Security
SECRET_KEY=your_super_secret_key_change_this

# App Base URL (Optional)
# 用于构建静态资源的完整访问路径 (如头像)
# 如果不设置，默认尝试使用 MINIO_EXTERNAL_ENDPOINT 或返回相对路径
# 示例: https://api.example.com
APP_BASE_URL=http://localhost:8000
```

### 4. 运行服务

```bash
uvicorn app.main:app --reload
```

服务启动后，可以访问 API 文档：

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Admin UI: [http://localhost:8000/cs-server/admin-ui](http://localhost:8000/cs-server/admin-ui)
- Admin (sqladmin 兜底): [http://localhost:8000/cs-server/admin](http://localhost:8000/cs-server/admin)

### 5. 管理后台
服务内置了新版管理页面，访问 `/cs-server/admin-ui` 即可进入。
- 管理员账号环境变量：`ADMIN_USERNAME`（默认 `yuzhuoheng`）
- 管理员密码环境变量：`ADMIN_PASSWORD`（默认 `jx665389=`）
- 当前页面以只读查看为主，包含：
  - 用户列表：OpenID、昵称、最近登录时间、相册数、照片数、已使用空间、配额上限。
  - 相册列表：可进入相册详情查看该相册下全部照片。
  - 用户维度：可查看该用户的配额日志记录。

### 6. 运维工具
**存储配额修正**：
如果发现用户存储空间显示异常（例如删除了相册但空间未释放），可运行修复脚本：
```bash
python fix_storage_quota.py
```

在服务器容器内运行：

```bash
docker exec -it camera-server python fix_storage_quota.py
```

**批量替换图片地址前缀**：
如果数据库中保存的图片链接需要批量替换前缀，可运行脚本。会自动处理用户头像、相册封面、照片原图及缩略图地址。

脚本名：`replace_url_prefix.py`。

1) 协议切换（默认 `https:// -> http://`）：
```bash
docker exec -it camera-server python replace_url_prefix.py
```

2) 切换为 `https://`：
```bash
docker exec -it camera-server python replace_url_prefix.py --to https
```

3) 自定义前缀替换（例如域名补 `www`）：
```bash
docker exec -it camera-server python replace_url_prefix.py --from-prefix "https://yuzhuoheng.xyz" --to-prefix "https://www.yuzhuoheng.xyz"
```

4) 仅预览将更新数量（不写库）：
```bash
docker exec -it camera-server python replace_url_prefix.py --from-prefix "https://yuzhuoheng.xyz" --to-prefix "https://www.yuzhuoheng.xyz" --dry-run
```

本地环境用法一致：
```bash
python replace_url_prefix.py --help
```

### 7. Docker 部署

构建镜像：

```bash
docker build -t camera-server .
```

运行容器：

```bash
docker run -d --name camera-server --network host -p 8000:8000 --env-file .env  camera-server
```

### 6. 数据重置

如果你需要清空所有数据（数据库和 MinIO 文件），可以使用 `reset_all.py` 脚本。

**警告：此操作不可恢复，请谨慎使用！**

在服务器容器内运行：

```bash
docker exec -it camera-server python reset_all.py
```

或者在本地环境运行：

```bash
python reset_all.py
```

执行后建议重启服务以重新初始化数据库表结构。

## 目录结构

```
app/
├── core/       # 核心配置 (Config, Database, Security)
├── models/     # 数据库模型 (SQLAlchemy)
├── routers/    # API 路由 (Auth, Albums, Photos, Shares)
├── schemas/    # Pydantic 数据模型 (Request/Response schemas)
├── services/   # 外部服务集成 (MinIO Storage)
└── utils/      # 工具函数
```
