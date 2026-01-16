# 相册服务 API 接口文档

## 1. 概述
本文档基于《随拍随存 · 功能设计》编写，定义了相册（Albums）模块的后端接口。
Base URL: `/api/v1` (具体取决于后端配置 `API_V1_STR`)

## 2. 数据模型

### Album (相册)
| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| id | string | UUID, 主键 |
| name | string | 相册名称 |
| cover_url | string | 封面图片 URL (由最新收纳的照片决定，后端自动更新) |
| owner_id | string | 所属用户 ID (OpenID) |
| created_at | datetime | 创建时间 |
| photo_count | integer | 照片数量 (统计字段，非数据库原生字段) |
| size | integer | 占用空间大小 (单位: bytes) |
| is_default | integer | 是否为系统默认相册 (1=是, 0=否) |

### Share (共享)
| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| id | string | UUID |
| token | string | 共享令牌 (唯一索引) |
| album_id | string | 关联相册 ID |
| permission | string | 权限类型: `read_only` (仅查看), `allow_upload` (支持上传) |
| expires_at | datetime | 过期时间 (可选) |
| created_at | datetime | 创建时间 |

---

## 3. 业务流程说明

### 3.1 相册共享流程
相册共享分为两个阶段：**生成共享**（房主操作）和 **访问共享**（客人操作）。

#### 第一阶段：发起共享（房主视角）
1.  **选择与设置**：
    *   用户在“相册详情页”点击“共享”按钮。
    *   **关键决策**：用户选择权限模式。
        *   **模式 A（默认）**：`read_only` —— “大家只能看，不能乱动我的相册。”
        *   **模式 B**：`allow_upload` —— “这是聚会相册，大家都可以把照片传上来。”
    *   用户选择有效期（例如：7天有效、永久有效）。
2.  **生成钥匙**：
    *   前端调用 `POST /albums/{id}/share` 接口。
    *   后端生成一个唯一的 **Share Token**（例如 `abc-123-xyz`），并将其与相册 ID、权限规则绑定存储。
3.  **分发**：
    *   后端返回 Token 和拼接好的小程序路径（如 `/pages/share?token=abc-123-xyz`）。
    *   用户直接通过微信转发给好友或群聊。

#### 第二阶段：访问与互动（客人视角）
1.  **敲门（校验）**：
    *   好友点击链接进入小程序 `Share` 页面。
    *   前端第一时间提取 URL 中的 `token`，调用 `GET /shares/{token}`。
    *   **后端工作**：检查 Token 是否存在？是否过期？
        *   如果通过：返回相册的基础信息（封面、名称）以及**您被授予的权限**（`read_only` 或 `allow_upload`）。
2.  **进门（浏览）**：
    *   校验通过后，客人进入相册详情页。
    *   **浏览照片**：前端请求 `GET /photos?album_id=xxx`。
    *   **鉴权细节**：此时客人并不是相册的主人。前端需要在请求中带上刚才的 `token`。后端看到 Token，确认它有效且对应当前相册，于是**放行**查看请求。
3.  **互动（根据权限分流）**：
    *   **如果是 `read_only`**：前端隐藏“上传”按钮，客人只能看图、保存图。
    *   **如果是 `allow_upload`**：
        *   前端显示“上传照片”按钮。
        *   客人上传照片时，调用 `POST /photos`。
        *   **鉴权细节**：同样，请求携带 `token`。后端检查这个 Token 是否拥有 `allow_upload` 权限。如果有，允许照片入库。

---

## 4. 接口列表

### 4.1 相册管理

#### 4.1.1 创建相册
创建新的相册。

- **URL**: `POST /albums`
- **Content-Type**: `application/json`
- **Request Body**:
    ```json
    {
      "name": "我的旅行"
    }
    ```
- **Response**: `201 Created`
    ```json
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "我的旅行",
      "cover_url": null,
      "owner_id": "user_openid_123",
      "created_at": "2024-01-14T10:00:00Z",
      "photo_count": 0
    }
    ```

#### 4.1.2 获取相册列表
分页获取当前登录用户的相册列表。

- **URL**: `GET /albums`
- **Query Parameters**:
    - `skip`: integer (默认 0)
    - `limit`: integer (默认 100)
    - `keyword`: string (可选，用于按名称搜索)
- **Response**: `200 OK`
    ```json
    [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "我的旅行",
        "cover_url": "http://example.com/latest_photo_thumb.jpg",
        "photo_count": 12,
        "created_at": "2024-01-14T10:00:00Z"
      }
    ]
    ```

#### 4.1.3 获取相册详情
获取单个相册的详细信息。

- **URL**: `GET /albums/{album_id}`
- **Response**: `200 OK`
    ```json
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "我的旅行",
      "description": "...", // 如果有
      "cover_url": "http://example.com/latest_photo_thumb.jpg",
      "owner_id": "user_openid_123",
      "photo_count": 12,
      "size": 10485760,
      "created_at": "2024-01-14T10:00:00Z"
    }
    ```

#### 4.1.4 修改相册
更新相册信息（名称）。

- **URL**: `PUT /albums/{album_id}`
- **Request Body**:
    ```json
    {
      "name": "新名称"
    }
    ```
- **Response**: `200 OK` (返回更新后的相册对象)

#### 4.1.5 删除相册
删除指定相册。

- **URL**: `DELETE /albums/{album_id}`
- **Response**: `200 OK`
    ```json
    {
      "message": "Album deleted successfully",
      "id": "550e8400-e29b-41d4-a716-446655440000"
    }
    ```
    - **注意**: 默认相册 (`is_default=1`) 不允许删除，将返回 `400 Bad Request`。

---

### 4.2 相册共享 (Share)

#### 4.2.1 创建共享链接
为相册生成访问令牌。

- **URL**: `POST /albums/{album_id}/share`
- **Request Body**:
    ```json
    {
      "expires_in_hours": 72, // 可选，默认值可设为无限制或7天
      "permission": "read_only" // 可选，默认 read_only。枚举值: read_only, allow_upload
    }
    ```
- **Response**: `200 OK`
    ```json
    {
      "token": "unique_share_token_abc123",
      "share_url": "pages/share?token=unique_share_token_abc123", // 前端路由格式
      "permission": "read_only",
      "expires_at": "2024-01-17T10:00:00Z"
    }
    ```

#### 4.2.2 访问/校验共享
通过 Token 获取共享的相册信息（无需登录即可调用，用于共享页）。
此接口通常位于 `shares` 路由下。

- **URL**: `GET /shares/{token}`
- **Response**: `200 OK`
    ```json
    {
      "valid": true,
      "album": {
        "id": "...",
        "name": "我的旅行",
        "owner_nickname": "张三", // 显示所有者昵称
        "owner_avatar_url": "http://...", // 显示所有者头像
        "cover_url": "..."
      },
      "permission": "read_only" // 返回此共享链接的权限，以便前端控制上传入口
    }
    ```
- **Error**: `404 Not Found` (Token无效或过期)

#### 4.2.3 获取相册活跃分享列表
列出指定相册下所有已生成的分享链接。

- **URL**: `GET /albums/{album_id}/shares`
- **Response**: `200 OK`
    ```json
    [
      {
        "token": "unique_share_token_abc123",
        "share_url": "pages/share?token=unique_share_token_abc123",
        "permission": "read_only",
        "expires_at": "2024-01-17T10:00:00Z"
      }
    ]
    ```

#### 4.2.4 撤销分享
删除指定的分享链接。

- **URL**: `DELETE /albums/shares/{token}`
- **Response**: `200 OK`
    ```json
    {
      "message": "Share deleted successfully"
    }
    ```

---

### 4.3 关联资源：相册内的照片

获取相册内的照片列表，复用 `GET /photos` 接口，通过 `album_id` 过滤。

- **URL**: `GET /photos`
- **Query Parameters**:
    - `album_id`: string (指定相册ID)
    - `skip`: integer
    - `limit`: integer
- **Response**: Photo List
