# TestPilot

AI 驱动的测试用例 & 测试脚本生成 Agent。

从需求文档 / OpenAPI 规范 / 文字描述出发，自动生成结构化测试用例，再从用例生成 Playwright TypeScript 测试脚本。

## 功能

```
需求文档 (.md / .yaml / .txt)
        ↓  testpilot generate
测试用例 (.api-cases.md / .e2e-cases.md)
        ↓  testpilot script
测试脚本 (.api.spec.ts / .e2e.spec.ts)
```

- **API 接口测试**：从 Markdown 需求文档或 OpenAPI 规范生成
- **E2E 页面测试**：从页面需求文档生成
- **两种执行模式**：`self`（Agent 本地生成）或 `llm`（调用 Claude/DeepSeek/OpenAI）
- **环境解耦**：测试脚本通过 `env.config.ts` 引用环境变量，不硬编码

## 快速开始

```bash
# 安装依赖
pnpm install

# 初始化配置文件
pnpm dev init

# 从需求文档生成测试用例
pnpm dev generate examples/api/login-api.md --mode api

# 从测试用例生成 Playwright 脚本
pnpm dev script tests/generated/login-api.api-cases.md --mode api

# E2E 模式
pnpm dev generate examples/e2e/login-page.md --mode e2e
pnpm dev script tests/generated/login-page.e2e-cases.md --mode e2e
```

## CLI 命令

### `testpilot generate <input...>`

从需求文档生成测试用例。

```
选项：
  -m, --mode <type>       api 或 e2e（默认 api）
  -f, --format <type>     强制输入格式：markdown / openapi / text
  -o, --outdir <path>     输出目录（默认 ./tests/generated）
  -e, --executor <type>   执行模式：self 或 llm
  --dry-run               输出到终端不写文件
  --force                 覆盖已有文件
```

### `testpilot script <cases...>`

从测试用例文件生成 Playwright 脚本。

```
选项：
  -m, --mode <type>       api 或 e2e（默认 api）
  -o, --outdir <path>     输出目录（默认 ./tests/specs）
  --force                 覆盖已有文件
```

### `testpilot init`

创建 `.testpilotrc.json` 配置文件。

## 配置

### `.testpilotrc.json` — TestPilot 运行配置

```json
{
  "executor": "self",
  "llm": {
    "provider": "deepseek",
    "model": "deepseek-chat",
    "apiKey": "sk-xxx",
    "maxTokens": 8192,
    "temperature": 0.2
  },
  "output": {
    "dir": "./tests/generated",
    "overwrite": false
  }
}
```

| 字段 | 说明 |
|------|------|
| `executor` | `self`（本地生成）或 `llm`（调用外部 API） |
| `llm.provider` | `claude` / `deepseek` / `openai-compatible` |
| `llm.apiKey` | LLM API Key（也可用环境变量 `ANTHROPIC_API_KEY`） |

### `tests/env.config.ts` — 被测环境配置

测试脚本通过此文件引用环境信息，所有配置项支持环境变量覆盖：

```typescript
export const env = {
  api: { baseUrl: process.env.TEST_API_URL ?? 'http://localhost:3000' },
  e2e: { baseUrl: process.env.TEST_APP_URL ?? 'http://localhost:5173' },
  testUser: {
    email: process.env.TEST_USER_EMAIL ?? 'test@example.com',
    password: process.env.TEST_USER_PASSWORD ?? 'Abc123456',
  },
};
```

## 输入格式

| 格式 | 扩展名 | 自动检测 |
|------|--------|---------|
| Markdown | .md | 按扩展名 |
| OpenAPI/Swagger | .yaml, .yml, .json | 检测 openapi/swagger 关键字 |
| 纯文本 | 其他 | 兜底 |

## 输出结构

```
tests/
├── env.config.ts                # 被测环境配置
├── generated/                   # 测试用例
│   ├── login-api.api-cases.md
│   └── login-page.e2e-cases.md
└── specs/                       # 测试脚本
    ├── register.api.spec.ts
    ├── login.api.spec.ts
    ├── login.e2e.spec.ts
    └── register.e2e.spec.ts
```

## 文档

- [项目规范](docs/project-spec.md) — 定位、流程、输入输出规范
- [测试用例生成规范](docs/test-case-generation-guide.md) — 字段定义、覆盖要求
- [测试脚本生成规范](docs/test-script-generation-guide.md) — 映射规则、断言规则
