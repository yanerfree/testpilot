# TestPilot 项目规范

## 1. 项目定位

TestPilot 是一个测试 Agent，具备两项核心能力：

| 能力 | 输入 | 输出 |
|------|------|------|
| 生成测试用例 | 需求文档 / API 规范 / 文字描述 | 结构化测试用例文档（.md） |
| 生成测试脚本 | 测试用例文档 | Playwright TypeScript 脚本（.spec.ts） |

两步独立执行，用户审核用例通过后再生成脚本。

## 2. 执行模式

通过 `.testpilotrc.json` 中的 `executor` 字段配置：

| 模式 | 值 | 说明 |
|------|-----|------|
| 自执行 | `"self"` | Agent 自身直接生成（开发阶段默认，不依赖外部 API） |
| LLM 调用 | `"llm"` | 读取配置的 LLM（Claude/DeepSeek/OpenAI 兼容）来生成 |

当 `executor = "self"` 时，`llm` 配置可以不填。
当 `executor = "llm"` 时，必须提供有效的 `llm` 配置。

## 3. 交互流程

Agent 不是静默执行，需要与用户交互确认：

### 3.1 生成测试用例

```
用户：请生成测试用例
  ↓
Agent：请提供需求文档路径（或直接粘贴内容）
  ↓
用户：./docs/api-spec.md
  ↓
Agent：检测到文件类型为 Markdown，包含 4 个 API 接口。
       请确认：
       - 测试模式：API 接口测试 / E2E 页面测试？
       - 输出目录：./tests/generated/（默认）
       - 输出格式：Markdown 表格（默认）
  ↓
用户：API 测试，默认就行
  ↓
Agent：生成中...
  ↓
Agent：已生成 31 条测试用例，写入 ./tests/generated/api-spec.api-cases.md
       [展示用例摘要]
       请审核，有问题可以告诉我调整。
```

### 3.2 生成测试脚本

```
用户：根据用例生成 Playwright 脚本
  ↓
Agent：请提供测试用例文件路径
  ↓
用户：./tests/output1/api-spec.api-cases.md
  ↓
Agent：检测到 31 条测试用例，涉及 4 个模块。

       [检查环境配置 tests/env.config.ts]
       ✓ api.baseUrl = http://192.168.51.108:5173
       ⚠ 检测到使用 admin 账号，建议使用专用测试账号
  ↓
用户：改成 tester / 123456
  ↓
Agent：✓ 已更新环境配置
       请确认：
       - 输出目录：./tests/output1/（与用例同目录）
  ↓
用户：确认
  ↓
Agent：生成中...
  ↓
Agent：已生成 4 个测试文件，写入 ./tests/output1/
       所有脚本通过 env.config.ts 引用环境变量，不硬编码地址。
```

### 3.3 Agent 检查清单

生成脚本前 Agent 必须确认：

| 检查项 | 说明 |
|--------|------|
| 环境配置文件存在 | `tests/env.config.ts` 是否存在 |
| baseUrl 已配置 | 被测系统地址，不能是空或占位符 |
| 测试账号已配置 | username + password，不能为空 |
| 非 admin 账号 | 如果是 admin，警告用户并建议更换 |
| 输出目录明确 | 用户指定了就用用户的，没指定才用默认 |

## 4. 输入规范

### 4.1 支持的输入格式

| 格式 | 文件类型 | 自动检测 | 优先级 |
|------|---------|---------|--------|
| Markdown 需求文档 | .md, .markdown | 按扩展名 | 最高（最常用） |
| Swagger/OpenAPI | .yaml, .yml, .json | 检测 openapi/swagger 关键字 | 高（API 最精准） |
| 纯文本描述 | .txt 或其他 | 兜底 | 低（兜底） |

### 4.2 输入方式

- 指定文件路径：`testpilot generate ./docs/api-spec.md`
- 交互中提供：Agent 询问后用户给出路径
- stdin 管道：`cat spec.md | testpilot generate --format markdown`

## 5. 输出规范

### 5.1 测试用例

- **格式**：Markdown 表格
- **文件命名**：`{输入文件名}.{模式}-cases.md`
  - API 模式 → `login-api.api-cases.md`
  - E2E 模式 → `login-page.e2e-cases.md`
- **默认目录**：`./tests/generated/`
- **字段**：用例ID、标题、模块、测试类型、优先级、前置条件、测试步骤、预期结果

### 5.2 测试脚本

- **格式**：Playwright + TypeScript
- **文件命名**：`{模块名}.{模式}.spec.ts`
  - API 模式 → `register.api.spec.ts`
  - E2E 模式 → `login.e2e.spec.ts`
- **默认目录**：`./tests/specs/`
- **环境引用**：所有脚本通过 `env.config.ts` 引用环境信息，不硬编码

### 5.3 输出目录结构

```
tests/
├── env.config.ts               # 被测环境配置（URL、数据库、账号等）
├── generated/                  # 测试用例文档
│   ├── login-api.api-cases.md
│   └── login-page.e2e-cases.md
└── specs/                      # 测试脚本（从用例生成）
    ├── register.api.spec.ts
    ├── login.api.spec.ts
    └── login.e2e.spec.ts
```

## 6. 被测环境配置

生成的测试脚本不硬编码任何环境信息，统一通过 `tests/env.config.ts` 引用。

### 6.1 配置文件：`tests/env.config.ts`

```typescript
export const env = {
  // 被测系统地址
  api: {
    baseUrl: process.env.TEST_API_URL ?? 'http://localhost:3000',
  },
  e2e: {
    baseUrl: process.env.TEST_APP_URL ?? 'http://localhost:5173',
  },

  // 数据库（用于测试数据准备/清理）
  db: {
    host: process.env.TEST_DB_HOST ?? 'localhost',
    port: Number(process.env.TEST_DB_PORT ?? 5432),
    name: process.env.TEST_DB_NAME ?? 'testdb',
    user: process.env.TEST_DB_USER ?? 'postgres',
    password: process.env.TEST_DB_PASSWORD ?? '',
  },

  // 测试账号
  testUser: {
    email: process.env.TEST_USER_EMAIL ?? 'test@example.com',
    password: process.env.TEST_USER_PASSWORD ?? 'Abc123456',
  },
};
```

### 6.2 脚本中的引用方式

```typescript
// API 测试脚本中
import { env } from '../env.config';

test.beforeAll(async ({ playwright }) => {
  context = await playwright.request.newContext({
    baseURL: env.api.baseUrl,
  });
});

// E2E 测试脚本中
import { env } from '../env.config';

test.beforeEach(async ({ page }) => {
  await page.goto(env.e2e.baseUrl + '/login');
});

// 使用测试账号
await page.getByLabel('邮箱').fill(env.testUser.email);
```

### 6.3 设计原则

- **环境变量优先**：所有配置项支持通过环境变量覆盖，方便 CI/CD
- **合理默认值**：本地开发时不需要额外配置即可运行
- **脚本不硬编码**：URL、端口、账号、密码等全部从 `env.config.ts` 读取
- **一处修改全局生效**：切换测试环境只需改这一个文件或设置环境变量
- **敏感信息不提交**：密码等敏感信息通过环境变量传入，`env.config.ts` 中只放默认值

## 7. TestPilot 配置文件

文件：`.testpilotrc.json`（项目根目录）

仅配置 TestPilot Agent 自身的运行参数，不包含被测环境信息：

```json
{
  "executor": "self | llm",
  "llm": {
    "provider": "claude | deepseek | openai-compatible",
    "apiKey": "sk-xxx",
    "model": "模型名称",
    "maxTokens": 8192,
    "temperature": 0.2,
    "baseUrl": "自定义 LLM API 地址（可选）"
  },
  "output": {
    "dir": "./tests/generated",
    "overwrite": false
  }
}
```

## 8. 关联文件清单

| 文件 | 用途 |
|------|------|
| `.testpilotrc.json` | TestPilot 配置（执行模式、LLM、输出路径） |
| `tests/env.config.ts` | 被测环境配置（URL、数据库、测试账号） |
| `docs/test-case-generation-guide.md` | 测试用例生成规范（字段定义、覆盖要求、编写规范） |
| `src/prompts/system-api.ts` | API 测试用例生成提示词（给 LLM 用，从规范提炼） |
| `src/prompts/system-e2e.ts` | E2E 测试用例生成提示词（给 LLM 用，从规范提炼） |
| `src/prompts/examples.ts` | Few-shot 示例（给 LLM 用，示范输出格式） |
| `src/generator/local-generator.ts` | self 模式的本地生成逻辑 |
| `src/generator/generator.ts` | LLM 模式的生成编排器 |
