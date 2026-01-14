# 认证模块 API 文档

本文档描述了用户认证相关的 API 接口，包括微信小程序登录、获取用户信息和更新用户信息。

**Base URL**: `/api/v1/auth`

---

## 1. 微信小程序登录 (Login)

接收微信小程序的 `code`，与微信服务器交互获取 OpenID，并返回系统的 JWT Token。

- **URL**: `/login`
- **Method**: `POST`
- **Auth Required**: No

### 请求参数 (Request Body)

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `code` | string | 是 | 微信小程序 `wx.login` 获取的临时登录凭证 |
| `userInfo` | object | 否 | 微信用户信息（用于首次注册时自动设置头像昵称） |

**userInfo 结构**:
| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `nickName` | string | 昵称 |
| `avatarUrl` | string | 头像 URL |
| `gender` | int | 性别 (0: 未知, 1: 男, 2: 女) |
| `city` | string | 城市 |
| `province` | string | 省份 |
| `country` | string | 国家 |
| `language` | string | 语言 |

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

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `access_token` | string | JWT 访问令牌，后续请求需放入 Header |
| `token_type` | string | 固定为 "bearer" |
| `user_id` | string | 用户 ID (OpenID) |
| `is_new_user` | boolean | 是否为新注册用户 (true: 新用户, false: 老用户) |

---

## 2. 获取当前用户信息 (Get Me)

获取当前登录用户的详细信息。

- **URL**: `/me`
- **Method**: `GET`
- **Auth Required**: Yes (Bearer Token)

### 请求头 (Headers)

| Key | Value |
| :--- | :--- |
| `Authorization` | `Bearer <access_token>` |

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

## 4. 上传用户头像 (Upload Avatar)

上传图片文件作为用户头像，并自动更新用户资料中的 `avatar_url`。

- **URL**: `/avatar`
- **Method**: `POST`
- **Auth Required**: Yes (Bearer Token)
- **Content-Type**: `multipart/form-data`

### 请求参数 (Form Data)

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `file` | File | 是 | 图片文件 (jpg/png等) |

### 响应结果 (Response)

成功时返回更新后的用户信息。

```json
{
  "id": "oAbc123...",
  "nickname": "用户昵称",
  "avatar_url": "http://192.168.x.x:9000/camera-server-photos/users/oAbc123.../avatar.jpg",
  "created_at": "2023-10-27T10:00:00.123456"
}
```

---

## 3. 更新当前用户信息 (Update Me)

更新当前用户的昵称或头像。

- **URL**: `/me`
- **Method**: `PUT`
- **Auth Required**: Yes (Bearer Token)

### 请求参数 (Request Body)

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `nickname` | string | 否 | 新昵称 |
| `avatar_url` | string | 否 | 新头像 URL |

*注意：`nickname` 和 `avatar_url` 至少提供一个，或者都不提供（不更新）。*

### 响应结果 (Response)

成功时返回更新后的用户信息。

```json
{
  "id": "oAbc123...",
  "nickname": "新昵称",
  "avatar_url": "https://new-avatar-url.com/...",
  "created_at": "2023-10-27T10:00:00.123456"
}
```
