# 后端设计文档 (Backend Design Document)

## 1. 概述 (Overview)

### 1.1 项目简介
本项目是一个基于微信小程序的“随拍随存”云相册服务。后端采用 FastAPI + PostgreSQL + MinIO 架构，提供照片上传、存储、管理、相册归档以及社交裂变扩容功能。

### 1.2 技术栈
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (SQLAlchemy ORM)
- **Object Storage**: MinIO (S3 Compatible)
- **Authentication**: WeChat Login (OpenID) + JWT
- **Deployment**: Docker / Uvicorn

---

## 2. 数据库设计 (Database Schema)

### 2.1 用户 (User)
- `users`
    - `id` (PK, String): 微信 OpenID
    - `nickname` (String): 微信昵称
    - `avatar_url` (String): 头像 URL
    - `storage_used` (BigInteger): 已用存储空间 (bytes)
    - `storage_limit` (BigInteger): 总存储配额 (bytes)
    - `created_at`: 注册时间

### 2.2 相册 (Album)
- `albums`
    - `id` (PK, UUID)
    - `name` (String): 相册名称
    - `owner_id` (FK -> users.id)
    - `cover_url` (String): 封面 URL (逻辑动态计算，非硬存储)
    - `is_default` (Integer): 是否为默认相册 (1=是, 0=否)
    - `created_at`: 创建时间

### 2.3 照片 (Photo)
- `photos`
    - `id` (PK, UUID)
    - `url` (String): 原图 MinIO URL
    - `thumbnail_url` (String): 缩略图 MinIO URL
    - `filename` (String): 原始文件名
    - `size` (Integer): 文件大小 (bytes)
    - `owner_id` (FK -> users.id)
    - `album_id` (FK -> albums.id, Nullable)
    - `created_at`: 上传时间

### 2.4 分享 (Share)
- `shares`
    - `id` (PK, UUID)
    - `token` (Unique String): 分享令牌
    - `album_id` (FK -> albums.id)
    - `permission` (String): 权限 (`read_only`, `allow_upload`)
    - `expires_at` (DateTime): 过期时间
    - `created_at`: 创建时间

### 2.5 扩容日志 (UserQuotaLog)
- `user_quota_logs`
    - `id` (PK, UUID)
    - `user_id` (FK -> users.id)
    - `change_amount` (BigInteger): 变动量 (+/-)
    - `reason`: 变动原因 (`invite_reward`, `initial`)
    - `created_at`: 记录时间

### 2.6 邀请记录 (UserInvite)
- `user_invites`
    - `id` (PK, UUID)
    - `inviter_id` (FK -> users.id): 邀请人
    - `invitee_id` (FK -> users.id): 被邀请人 (Unique)
    - `status`: 状态 (`completed`)
    - `reward_granted`: 奖励是否发放

---

## 3. 核心业务逻辑 (Core Business Logic)

### 3.1 用户认证与邀请裂变
- **登录流程**: 
    1. 前端 `wx.login()` 获取 `code`。
    2. 后端调用微信 `jscode2session` 换取 `openid`。
    3. 如果是新用户，初始化存储配额（500MB）。
- **邀请奖励**:
    1. 新用户登录时携带 `invite_code` (即邀请人的 openid)。
    2. 校验邀请人是否存在。
    3. **被邀请人**：立即获得 100MB 扩容。
    4. **邀请人**：获得 100MB 扩容（受每日 1GB、总计 5GB 上限限制）。
    5. 记录 `UserInvite` 和 `UserQuotaLog`。

### 3.2 照片上传与配额控制
- **上传流程**:
    1. 接收文件流。
    2. **原子性检查配额**: `UPDATE users SET storage_used = storage_used + size WHERE storage_used + size <= limit`。如果更新行数为 0，则拒绝上传 (403)。
    3. 上传原图至 MinIO。
    4. 生成并上传缩略图至 MinIO。
    5. 写入数据库 `Photo` 记录。
    6. 若上传失败，回滚数据库存储占用。

### 3.3 相册管理与级联删除
- **默认相册**: 系统自动创建，`is_default=1`，不可删除。
- **级联删除**: 删除相册时，自动执行清理操作：
    1. 遍历相册内所有照片。
    2. 从 MinIO 物理删除原图和缩略图。
    3. 释放用户已用存储空间 (`storage_used`)。
    4. 删除数据库照片记录。
    5. 删除相册记录。

### 3.4 相册分享与权限
- **Token机制**: 每个分享链接对应唯一的 Token。
- **权限控制**: 
    - `read_only`: 仅允许 `GET` 操作。
    - `allow_upload`: 允许访客调用上传接口（需携带 Token）。
- **有效期**: 支持设置过期时间，过期后 Token 失效 (410 Gone)。
- **管理**: 相册所有者可以查看活跃分享列表，并随时撤销（删除）分享。

---

## 4. API 接口概览 (API Summary)

详细接口定义请参考 `docs/API_ALBUM_DOCS.md` 和 `docs/API_PHOTO_DOCS.md`。

### Auth
- `POST /auth/login`: 微信登录/注册
- `POST /auth/avatar`: 更新头像
- `PUT /auth/me`: 更新用户信息

### Albums
- `POST /albums`: 创建相册
- `GET /albums`: 获取相册列表 (按时间倒序)
- `GET /albums/{id}`: 获取详情
- `PUT /albums/{id}`: 修改相册
- `DELETE /albums/{id}`: 删除相册 (级联删除照片)
- `POST /albums/{id}/share`: 创建分享
- `GET /albums/{id}/shares`: 获取活跃分享列表
- `DELETE /albums/shares/{token}`: 撤销分享

### Shares
- `GET /shares/{token}`: 校验分享/获取相册信息

### Photos
- `POST /photos`: 上传照片 (支持指定 `album_id` 或分享 Token)
- `GET /photos`: 获取照片列表 (支持按 `album_id` 筛选)
- `GET /photos/{id}`: 照片详情
- `DELETE /photos/{id}`: 删除照片

---

## 5. 目录结构 (Project Structure)

```
app/
├── core/
│   ├── config.py      # 配置加载
│   ├── database.py    # 数据库连接
│   ├── security.py    # JWT 工具
│   └── deps.py        # 依赖注入 (CurrentUser等)
├── models/
│   └── models.py      # SQLAlchemy 模型定义
├── routers/
│   ├── auth.py        # 认证相关接口
│   ├── albums.py      # 相册相关接口
│   ├── photos.py      # 照片相关接口
│   └── shares.py      # 分享相关接口
├── schemas/           # Pydantic 数据验证模型
├── services/
│   └── storage.py     # MinIO 封装
└── main.py            # 入口文件
```
