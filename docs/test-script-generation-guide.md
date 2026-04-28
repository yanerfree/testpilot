# TestPilot 测试脚本生成指导规范

## 1. 总则

测试脚本从已审核通过的测试用例文档生成，框架为 Playwright + TypeScript。
脚本必须与用例一一对应，通过用例ID建立追溯关系。

## 2. 环境引用规则

所有环境相关信息统一从 `tests/env.config.ts` 读取，脚本中禁止硬编码。

| 信息类型 | 引用方式 | 禁止写法 |
|---------|---------|---------|
| API 地址 | `env.api.baseUrl` | `'http://localhost:3000'` |
| 页面地址 | `env.e2e.baseUrl` | `'http://localhost:5173'` |
| 测试账号 | `env.testUser.email` | `'test@example.com'` |
| 数据库连接 | `env.db.host` | `'localhost'` |

## 3. 文件组织规则

### 3.1 文件拆分

按测试用例中的**模块**字段拆分文件，一个模块一个文件。

| 用例模块 | 脚本文件名 |
|---------|-----------|
| 用户注册 | `register.api.spec.ts` |
| 用户登录 | `login.api.spec.ts` |
| 登录页面 | `login.e2e.spec.ts` |

命名规则：`{模块名英文}.{api|e2e}.spec.ts`

### 3.2 目录结构

```
tests/
├── env.config.ts          # 环境配置
├── specs/
│   ├── register.api.spec.ts
│   ├── login.api.spec.ts
│   └── login.e2e.spec.ts
```

## 4. 脚本结构规则

### 4.1 API 测试脚本结构

```typescript
import { test, expect, APIRequestContext } from '@playwright/test';
import { env } from '../env.config';

let context: APIRequestContext;

test.beforeAll(async ({ playwright }) => {
  context = await playwright.request.newContext({
    baseURL: env.api.baseUrl,
  });
  // 如需认证：在此登录获取 token
});

test.afterAll(async () => {
  await context.dispose();
});

test.describe('模块名 — 接口路径', () => {
  // 每条用例对应一个 test
});
```

### 4.2 E2E 测试脚本结构

```typescript
import { test, expect } from '@playwright/test';
import { env } from '../env.config';

test.describe('页面/流程名称', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(env.e2e.baseUrl + '/path');
  });

  // 每条用例对应一个 test
});
```

## 5. 用例到脚本的映射规则

### 5.1 test 命名

格式：`用例ID + 用例标题的英文概述`

```typescript
// 用例：TC-REG-001 验证正确信息注册成功
test('TC-REG-001 should register successfully with valid data', async () => {
```

每个 test 必须以用例ID开头，确保用例与脚本可追溯。

### 5.2 用例字段到脚本的映射

| 用例字段 | 对应脚本位置 |
|---------|------------|
| 用例ID | `test('TC-XXX-NNN ...')` 的标题前缀 |
| 标题 | `test()` 标题的英文描述部分 |
| 模块 | `test.describe()` 的分组名 |
| 前置条件 | `test.beforeAll()` 或 `test.beforeEach()` 中实现 |
| 测试步骤 | `test()` 函数体中的操作代码 |
| 预期结果 | `expect()` 断言 |
| 优先级 | 通过 Playwright tag 标记：`test('...', { tag: '@P0' }, async () => {` |
| 测试类型 | 通过 Playwright tag 标记：`{ tag: ['@P0', '@功能测试'] }` |

### 5.3 优先级标记

```typescript
// P0 核心用例
test('TC-LOG-001 should login successfully', { tag: '@P0' }, async () => {

// P2 边界条件
test('TC-REG-005 should return 400 for empty body', { tag: '@P2' }, async () => {
```

运行时可按优先级筛选：`npx playwright test --grep @P0`

## 6. 断言规则

### 6.1 API 测试断言顺序

1. 先断言状态码
2. 再断言返回体结构（字段存在性）
3. 最后断言字段值

```typescript
expect(response.status()).toBe(200);
const body = await response.json();
expect(body).toHaveProperty('token');
expect(typeof body.token).toBe('string');
```

### 6.2 E2E 测试断言

1. 页面跳转用 `toHaveURL()`
2. 元素可见性用 `toBeVisible()`
3. 文本内容用 `toHaveText()` 或 `toContainText()`
4. 表单状态用 `toBeDisabled()` / `toBeEnabled()`

```typescript
await expect(page).toHaveURL('/dashboard');
await expect(page.getByText('欢迎')).toBeVisible();
```

### 6.3 E2E 选择器优先级

1. `page.getByTestId('submit-btn')` — data-testid
2. `page.getByRole('button', { name: '登录' })` — ARIA role
3. `page.getByLabel('邮箱')` — 表单 label
4. `page.getByPlaceholder('请输入邮箱')` — placeholder
5. `page.getByText('登录')` — 文本内容
6. `page.locator('.css-selector')` — CSS 选择器（最后手段）

## 7. 数据管理规则

### 7.1 测试数据独立性

- 每个 test 使用的数据不能依赖其他 test 的执行结果
- 需要唯一数据时用时间戳或随机值：`const email = \`test_\${Date.now()}@example.com\``
- 需要已存在数据时在 `beforeAll` 中创建

### 7.2 数据恢复（强制规则）

**凡是修改了系统原有数据的操作，必须在 test 结束时恢复到操作前的状态。**

适用场景：
- 修改密码 → 改回原密码
- 修改用户信息（昵称、头像、邮箱等）→ 改回原值
- 修改系统配置/设置 → 改回原值
- 修改数据状态（启用/禁用、审核通过/拒绝等）→ 改回原状态
- 删除数据 → 如果是软删除需恢复，硬删除需在 beforeAll 中创建专用测试数据

实现方式：**必须使用 try/finally**，确保即使断言失败也能执行恢复。

```typescript
test('should change password successfully', async () => {
  const newPassword = 'NewPass789';
  const response = await changePassword(context, authToken, env.testUser.password, newPassword);
  expect(response.status()).toBe(200);

  try {
    // 验证逻辑
    const loginRes = await login(context, newPassword);
    expect(loginRes.status()).toBe(200);
  } finally {
    // 恢复密码 — 无论断言是否通过都执行
    const tmpToken = await login(context, newPassword);
    await changePassword(context, tmpToken, newPassword, env.testUser.password);
    authToken = await login(context);
  }
});
```

**禁止事项：**
- 禁止把恢复逻辑放在 try 块里（断言失败后不会执行）
- 禁止依赖下一个 test 来恢复数据
- 禁止直接操作数据库来恢复（通过 API 恢复）

- 创建类操作（注册用户）如需清理，在 `afterAll` 中处理
- 不依赖数据库直接操作，通过 API 调用完成数据准备和清理

### 7.3 认证处理

需要认证的接口，统一在 `beforeAll` 中登录获取 token：

```typescript
let authToken: string;

test.beforeAll(async ({ playwright }) => {
  context = await playwright.request.newContext({ baseURL: env.api.baseUrl });
  const res = await context.post('/api/auth/login', {
    data: { email: env.testUser.email, password: env.testUser.password },
  });
  authToken = (await res.json()).token;
});
```

后续 test 中通过 header 传递：

```typescript
const response = await context.get('/api/auth/me', {
  headers: { Authorization: \`Bearer \${authToken}\` },
});
```

## 8. 禁止事项

- 禁止硬编码任何环境地址、端口、账号密码
- 禁止使用管理员账号（admin）进行测试，如用户提供 admin 账号需提醒风险，建议使用专用测试账号
- 禁止修改系统原有数据后不恢复（必须 try/finally 还原）
- 禁止 test 之间有执行顺序依赖
- 禁止在 test 中使用 `sleep` / `waitForTimeout`（用 Playwright 的自动等待）
- 禁止跳过断言（不能只调接口不检查结果）
- 禁止在脚本中写注释解释业务逻辑（业务逻辑在用例文档中，脚本只负责执行）
- 禁止直接操作数据库（通过 API 完成数据准备和恢复）
