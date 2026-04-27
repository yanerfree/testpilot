import type { LLMMessage, TestMode } from '../llm/types.js';

export function getFewShotExamples(mode: TestMode): LLMMessage[] {
  if (mode === 'api') {
    return getApiExamples();
  }
  return getE2eExamples();
}

function getApiExamples(): LLMMessage[] {
  return [
    {
      role: 'user',
      content: `Generate test cases for:

## POST /api/auth/login

Login endpoint. Accepts email and password, returns JWT token.

Request body:
\`\`\`json
{"email": "user@example.com", "password": "pass123"}
\`\`\`

- 200: Returns { token, user } on success
- 401: Invalid credentials
- 400: Missing required fields`,
    },
    {
      role: 'assistant',
      content: `| 用例ID | 标题 | 模块 | 测试类型 | 优先级 | 前置条件 | 测试步骤 | 预期结果 |
|--------|------|------|---------|--------|---------|---------|---------|
| TC-AUTH-001 | 验证正确邮箱密码登录成功 | 用户登录 | 功能测试 | P0 | 已注册账号 email=user@example.com, password=pass123 | 1. 发送 POST /api/auth/login，body: {"email":"user@example.com","password":"pass123"} | 1. 状态码 200 2. 返回 JSON 包含 token 字段（string 类型） 3. 返回 user 对象包含 id、email |
| TC-AUTH-002 | 验证密码错误返回 401 | 用户登录 | 异常场景 | P1 | 已注册账号 email=user@example.com | 1. 发送 POST /api/auth/login，body: {"email":"user@example.com","password":"wrongpass"} | 1. 状态码 401 2. 返回错误信息 |
| TC-AUTH-003 | 验证邮箱不存在返回 401 | 用户登录 | 异常场景 | P1 | 无 | 1. 发送 POST /api/auth/login，body: {"email":"noexist@example.com","password":"pass123"} | 1. 状态码 401 |
| TC-AUTH-004 | 验证缺少 email 字段返回 400 | 用户登录 | 参数校验 | P1 | 无 | 1. 发送 POST /api/auth/login，body: {"password":"pass123"} | 1. 状态码 400 2. 返回错误信息提示 email 必填 |
| TC-AUTH-005 | 验证缺少 password 字段返回 400 | 用户登录 | 参数校验 | P1 | 无 | 1. 发送 POST /api/auth/login，body: {"email":"user@example.com"} | 1. 状态码 400 2. 返回错误信息提示 password 必填 |
| TC-AUTH-006 | 验证空请求体返回 400 | 用户登录 | 边界条件 | P2 | 无 | 1. 发送 POST /api/auth/login，body: {} | 1. 状态码 400 |
| TC-AUTH-007 | 验证 email 格式不正确返回 400 | 用户登录 | 参数校验 | P2 | 无 | 1. 发送 POST /api/auth/login，body: {"email":"not-an-email","password":"pass123"} | 1. 状态码 400 2. 返回错误信息提示邮箱格式不正确 |`,
    },
  ];
}

function getE2eExamples(): LLMMessage[] {
  return [
    {
      role: 'user',
      content: `Generate test cases for:

## 登录页面
URL: /login

用户操作:
- 输入邮箱
- 输入密码
- 点击登录按钮

预期结果:
- 登录成功跳转到首页
- 密码错误显示错误提示
- 邮箱为空显示校验提示`,
    },
    {
      role: 'assistant',
      content: `| 用例ID | 标题 | 模块 | 测试类型 | 优先级 | 前置条件 | 测试步骤 | 预期结果 |
|--------|------|------|---------|--------|---------|---------|---------|
| TC-LOGIN-001 | 验证正确邮箱密码登录成功 | 登录页面 | 功能测试 | P0 | 1. 已注册账号 email=user@example.com, password=password123 2. 已打开登录页 /login | 1. 在邮箱输入框输入 user@example.com 2. 在密码输入框输入 password123 3. 点击「登录」按钮 | 1. 页面跳转到 /dashboard 2. 页面显示欢迎信息 |
| TC-LOGIN-002 | 验证密码错误显示错误提示 | 登录页面 | 异常场景 | P1 | 1. 已注册账号 email=user@example.com 2. 已打开登录页 /login | 1. 在邮箱输入框输入 user@example.com 2. 在密码输入框输入 wrongpassword 3. 点击「登录」按钮 | 1. 页面停留在 /login 2. 显示错误提示"邮箱或密码错误" |
| TC-LOGIN-003 | 验证邮箱为空的校验提示 | 登录页面 | 表单校验 | P1 | 1. 已打开登录页 /login | 1. 邮箱输入框留空 2. 在密码输入框输入 password123 3. 点击「登录」按钮 | 1. 邮箱输入框下方显示"请输入邮箱" 2. 不发送请求 |
| TC-LOGIN-004 | 验证密码为空的校验提示 | 登录页面 | 表单校验 | P1 | 1. 已打开登录页 /login | 1. 在邮箱输入框输入 user@example.com 2. 密码输入框留空 3. 点击「登录」按钮 | 1. 密码输入框下方显示"请输入密码" 2. 不发送请求 |
| TC-LOGIN-005 | 验证邮箱格式不正确的校验 | 登录页面 | 表单校验 | P2 | 1. 已打开登录页 /login | 1. 在邮箱输入框输入 not-an-email 2. 在密码输入框输入 password123 3. 点击「登录」按钮 | 1. 邮箱输入框下方显示"邮箱格式不正确" |`,
    },
  ];
}
