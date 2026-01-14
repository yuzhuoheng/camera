# 随拍随存 (Camera Server) API 文档

**版本**: 1.0.0 (MVP)  
**后端框架**: FastAPI  
**鉴权方式**: Bearer Token (JWT)

## 1. 基础说明

- **Base URL**: `http://localhost:8000/api/v1` (本地开发)
- **请求头**: 
  - 认证接口外，所有接口需携带: `Authorization: Bearer <your_token>`
  - 文件上传: `Content-Type: multipart/form-data`
  - 其他接口: `Content-Type: application/json`

---

## 2. 认证模块 (Auth)

### 2.1 微信登录
通过微信小程序端的 `wx.login` 获取 code，换取后端自定义 Token。

- **URL**: `/auth/login`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "code": "081......" // 微信临时登录凭证
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "eyJhbG...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user_info": {
      "id": "user_001",
      "nickname": "WeChatUser"
    }
  }
  ```

---

## 3. 相册管理 (Albums)

### 3.1 创建相册
- **URL**: `/albums`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "name": "2023公司团建"
  }
  ```
- **Response**:
  ```json
  {
    "id": "album_123",
    "name": "2023公司团建",
    "owner_id": "user_001",
    "created_at": "2023-10-27T10:00:00Z",
    "photo_count": 0
  }
  ```

### 3.2 获取相册列表
- **URL**: `/albums`
- **Method**: `GET`
- **Query Params**:
  - `skip`: (Optional) 分页偏移量，默认0
  - `limit`: (Optional) 每页数量，默认20
- **Response**:
  ```json
  [
    {
      "id": "album_123",
      "name": "2023公司团建",
      "cover_url": "http://.../photo_1.jpg", // 封面图（可选，取最新一张）
      "photo_count": 5,
      "created_at": "..."
    }
  ]
  ```

### 3.3 修改相册
- **URL**: `/albums/{album_id}`
- **Method**: `PATCH`
- **Body**:
  ```json
  {
    "name": "新名称"
  }
  ```

### 3.4 删除相册
- **URL**: `/albums/{album_id}`
- **Method**: `DELETE`
- **Description**: 删除相册及相册内所有照片（或仅逻辑删除）。

---

## 4. 照片管理 (Photos)

### 4.1 上传照片
- **URL**: `/photos`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Form Data**:
  - `file`: (Binary) 图片文件
  - `album_id`: (String, Optional) 归属相册ID，不传则归入"未分组"
- **Response**:
  ```json
  {
    "id": "photo_999",
    "url": "http://oss.../files/img_01.jpg",
    "thumbnail_url": "http://oss.../files/img_01_thumb.jpg",
    "album_id": "album_123",
    "created_at": "..."
  }
  ```

### 4.2 获取照片流
支持获取某个相册的照片，或者所有照片的时间线。

- **URL**: `/photos`
- **Method**: `GET`
- **Query Params**:
  - `album_id`: (Optional) 筛选特定相册
  - `skip`: 0
  - `limit`: 20
- **Response**:
  ```json
  [
    {
      "id": "photo_999",
      "url": "...",
      "thumbnail_url": "...",
      "created_at": "..."
    }
  ]
  ```

### 4.3 删除照片
- **URL**: `/photos/{photo_id}`
- **Method**: `DELETE`

---

## 5. 分享模块 (Shares)

### 5.1 创建分享令牌
- **URL**: `/shares`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "album_id": "album_123",
    "scope": "token", // 目前仅支持 token 模式
    "expires_in_hours": 24 // 可选，过期时间
  }
  ```
- **Response**:
  ```json
  {
    "share_token": "AB12CD", // 短码或随机串
    "share_url": "...",      // 小程序路径参数等
    "expires_at": "2023-10-28T10:00:00Z"
  }
  ```

### 5.2 验证/访问分享
被分享者使用此接口获取相册内容。此接口**不需要**登录 Token，而是需要 `share_token`。

- **URL**: `/shares/access`
- **Method**: `GET`
- **Query Params**:
  - `token`: "AB12CD"
- **Response**:
  ```json
  {
    "album": {
      "id": "album_123",
      "name": "2023公司团建"
    },
    "photos": [
      // ... 照片列表
    ]
  }
  ```

---

## 6. 数据模型 (Models) - 参考

### User
```python
class User(BaseModel):
    id: str         # openid
    created_at: datetime
```

### Album
```python
class Album(BaseModel):
    id: str
    owner_id: str
    name: str
    created_at: datetime
```

### Photo
```python
class Photo(BaseModel):
    id: str
    owner_id: str
    album_id: Optional[str]
    filename: str
    url: str
    thumbnail_url: str
    created_at: datetime
```
