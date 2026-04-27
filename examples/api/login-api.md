# 用户认证 API

用户认证模块，提供注册、登录、获取用户信息等接口。

## POST /api/auth/register

用户注册接口。接收用户名、邮箱和密码，创建新用户账号。

请求体：
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "Abc123456"
}
```

- 201 创建成功，返回 { id, username, email }
- 400 缺少必填字段或格式不正确
- 409 邮箱已被注册

## POST /api/auth/login

用户登录接口。接收邮箱和密码，返回 JWT token。

请求体：
```json
{
  "email": "test@example.com",
  "password": "Abc123456"
}
```

- 200 登录成功，返回 { token, user: { id, username, email } }
- 401 邮箱或密码错误
- 400 缺少必填字段

## GET /api/auth/me

获取当前登录用户信息。需要在 Header 中携带 Authorization: Bearer {token}。

- 200 返回 { id, username, email, createdAt }
- 401 未提供 token 或 token 无效

## PUT /api/auth/password

修改密码。需要认证。

请求体：
```json
{
  "oldPassword": "Abc123456",
  "newPassword": "Xyz789012"
}
```

- 200 修改成功
- 400 新密码格式不符合要求（至少8位，包含大小写和数字）
- 401 旧密码错误或未认证
