# 照片模块 API 文档

本文档描述了照片管理相关的 API 接口，包括上传照片、获取照片列表、查看照片详情和删除照片。

**Base URL**: `/api/v1/photos`

---

## 1. 上传照片 (Upload Photo)

上传单张图片文件。可以选择关联到特定相册。
**注意：如果不指定相册 ID，系统将自动把照片存入用户的“默认相册”。如果“默认相册”不存在，系统会自动创建。**

- **URL**: `/`
- **Method**: `POST`
- **Auth Required**: Yes (Bearer Token)
- **Content-Type**: `multipart/form-data`

### 请求参数 (Form Data)

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `file` | File | 是 | 图片文件 (jpg/png/jpeg/gif等) |
| `album_id` | string | 否 | 关联的相册 ID。留空则存入默认相册。 |

### 响应结果 (Response)

成功时返回创建的照片信息。

```json
{
  "id": "pAbc123...",
  "url": "http://minio-host/bucket/photos/user_id/photo.jpg",
  "thumbnail_url": "http://minio-host/bucket/photos/user_id/photo_thumb.jpg",
  "download_url": "http://minio-host/bucket/photos/user_id/photo.jpg", 
  "filename": "my_photo.jpg",
  "size": 102400,
  "album_id": "aXyz789...",
  "owner_id": "uUser123...",
  "created_at": "2023-10-27T10:05:00.123456"
}
```
* `download_url`: 用于“保存到本地”功能的下载链接。

---

## 2. 获取照片列表 (Get Photo List)

分页获取当前用户的照片列表。支持按相册筛选。

- **URL**: `/`
- **Method**: `GET`
- **Auth Required**: Yes (Bearer Token)

### 请求参数 (Query Parameters)

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `page` | int | 否 | 页码 (默认 1) |
| `size` | int | 否 | 每页数量 (默认 20) |
| `album_id` | string | 否 | 按相册 ID 筛选 |

### 响应结果 (Response)

```json
{
  "items": [
    {
      "id": "pAbc123...",
      "url": "http://...",
      "thumbnail_url": "http://...",
      "download_url": "http://...",
      "filename": "photo1.jpg",
      "size": 102400,
      "album_id": "aXyz789...",
      "owner_id": "uUser123...",
      "created_at": "2023-10-27T10:05:00.123456"
    },
    {
      "id": "pDef456...",
      "url": "http://...",
      "thumbnail_url": "http://...",
      "download_url": "http://...",
      "filename": "photo2.jpg",
      "size": 204800,
      "album_id": null,
      "owner_id": "uUser123...",
      "created_at": "2023-10-27T11:00:00.000000"
    }
  ],
  "total": 100,
  "page": 1,
  "size": 20,
  "pages": 5
}
```

---

## 3. 获取照片详情 (Get Photo Detail)

获取单张照片的详细信息，包含下载链接。

- **URL**: `/{photo_id}`
- **Method**: `GET`
- **Auth Required**: Yes (Bearer Token)

### 路径参数 (Path Parameters)

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `photo_id` | string | 照片 ID |

### 响应结果 (Response)

```json
{
  "id": "pAbc123...",
  "url": "http://...",
  "thumbnail_url": "http://...",
  "download_url": "http://...",
  "filename": "photo1.jpg",
  "size": 102400,
  "album_id": "aXyz789...",
  "owner_id": "uUser123...",
  "owner": {
    "id": "uUser123...",
    "nickname": "用户昵称",
    "avatar_url": "http://..."
  },
  "created_at": "2023-10-27T10:05:00.123456"
}
```

---

## 4. 删除照片 (Delete Photo)

删除指定照片。同时会删除云存储中的文件。

- **URL**: `/{photo_id}`
- **Method**: `DELETE`
- **Auth Required**: Yes (Bearer Token)

### 路径参数 (Path Parameters)

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `photo_id` | string | 照片 ID |

### 响应结果 (Response)

HTTP 204 No Content (成功删除，无返回内容) 或者返回简单的成功消息。

```json
{
  "message": "Photo deleted successfully"
}
```

---

## 5. 获取指定用户的照片列表 (Get User Photos)

获取指定用户 ID 的照片列表。通常用于查看他人主页或管理员查询。

- **URL**: `/user/{user_id}`
- **Method**: `GET`
- **Auth Required**: Yes (Bearer Token)

### 路径参数 (Path Parameters)

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `user_id` | string | 目标用户 ID (OpenID) |

### 请求参数 (Query Parameters)

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `page` | int | 否 | 页码 (默认 1) |
| `size` | int | 否 | 每页数量 (默认 20) |

### 响应结果 (Response)

与“获取照片列表”接口一致。

