# 认证模块 API 文档

本文档描述了用户认证相关的 API 接口，包括微信小程序登录、获取用户信息和更新用户信息。

**Base URL**: `/api/v1/auth`

---

## 1. 微信小程序登录 (Login)

接收微信小程序的 `code`，与微信服务器交互获取 OpenID，并返回系统的 JWT Token。

**注意**：`userInfo` 中的 `avatarUrl` 如果是 `http://tmp/` 开头的本地临时路径，**不要**传给此接口，因为服务器无法保存。请在登录后使用 **上传用户头像** 接口。

- **URL**: `/login`
- **Method**: `POST`
- **Auth Required**: No

### 请求参数 (Request Body)

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `code` | string | 是 | 微信小程序 `wx.login` 获取的临时登录凭证 |
| `userInfo` | object | 否 | 微信用户信息（仅用于昵称，头像建议登录后上传） |

### 响应结果 (Response)

成功时返回 HTTP 200 和 Token 信息。

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "oAbc123...",
  "is_new_user": true
}
```

---

## 2. 上传用户头像 (Upload Avatar)

**新增接口**：用于上传用户头像并自动更新用户信息。推荐在微信小程序获取到临时头像路径后调用。

- **URL**: `/avatar`
- **Method**: `POST`
- **Auth Required**: Yes (Bearer Token)
- **Content-Type**: `multipart/form-data`

### 请求参数 (Form Data)

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `file` | file | 是 | 图片文件 (jpg/png 等) |

### 响应结果 (Response)

返回更新后的用户信息。

```json
{
  "id": "oAbc123...",
  "nickname": "微信用户",
  "avatar_url": "https://minio.example.com/bucket/avatars/...",
  "created_at": "..."
}
```

---

## 3. 获取当前用户信息 (Get Me)

获取当前登录用户的详细信息。

- **URL**: `/me`
- **Method**: `GET`
- **Auth Required**: Yes (Bearer Token)

### 响应结果 (Response)

```json
{
  "id": "oAbc123...",
  "nickname": "微信用户",
  "avatar_url": "https://thirdwx.qlogo.cn/...",
  "created_at": "2023-10-27T10:00:00.123456"
}
```

---

## 4. 更新当前用户信息 (Update Me)

更新当前用户的昵称或头像 URL（如果是手动上传到其他地方）。

- **URL**: `/me`
- **Method**: `PUT`
- **Auth Required**: Yes (Bearer Token)
- **Content-Type**: `application/json`

### 请求参数 (Request Body)

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `nickname` | string | 否 | 新昵称 |
| `avatar_url` | string | 否 | 新头像 URL |

### 响应结果 (Response)

成功时返回更新后的用户信息。
