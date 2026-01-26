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




### 5. Docker 部署

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
