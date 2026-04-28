import fs from 'node:fs/promises';
import path from 'node:path';
import type { TestMode } from '../llm/types.js';

export interface TestCase {
  id: string;
  title: string;
  module: string;
  testType: string;
  priority: string;
  precondition: string;
  steps: string;
  expected: string;
}

export interface ScriptGenerateOptions {
  casesPath: string;
  mode: TestMode;
  outdir: string;
  overwrite: boolean;
}

export async function generateScripts(options: ScriptGenerateOptions): Promise<string[]> {
  const content = await fs.readFile(options.casesPath, 'utf-8');
  const cases = parseTestCases(content);

  if (cases.length === 0) {
    throw new Error(`No test cases found in ${options.casesPath}`);
  }

  const grouped = groupByModule(cases);
  const writtenFiles: string[] = [];

  await fs.mkdir(options.outdir, { recursive: true });

  for (const [moduleName, moduleCases] of Object.entries(grouped)) {
    const fileName = toFileName(moduleName, options.mode);
    const filePath = path.resolve(options.outdir, fileName);

    if (!options.overwrite) {
      try {
        await fs.access(filePath);
        throw new Error(`File already exists: ${filePath}\n  → Use --force to overwrite.`);
      } catch (err) {
        if (err instanceof Error && err.message.startsWith('File already')) throw err;
      }
    }

    let code: string;
    if (options.mode === 'api') {
      code = generateApiScript(moduleName, moduleCases);
    } else {
      code = generateE2eScript(moduleName, moduleCases);
    }

    await fs.writeFile(filePath, code, 'utf-8');
    writtenFiles.push(filePath);
  }

  return writtenFiles;
}

function parseTestCases(content: string): TestCase[] {
  const lines = content.split('\n').filter(l => l.trim().startsWith('|'));

  // Skip header and separator rows
  const dataLines = lines.filter(l => !l.includes('-----') && !l.includes('用例ID'));

  return dataLines.map(line => {
    const cells = line.split('|').map(c => c.trim()).filter(Boolean);
    if (cells.length < 8) return null;
    return {
      id: cells[0],
      title: cells[1],
      module: cells[2],
      testType: cells[3],
      priority: cells[4],
      precondition: cells[5],
      steps: cells[6],
      expected: cells[7],
    };
  }).filter(Boolean) as TestCase[];
}

function groupByModule(cases: TestCase[]): Record<string, TestCase[]> {
  const grouped: Record<string, TestCase[]> = {};
  for (const tc of cases) {
    if (!grouped[tc.module]) grouped[tc.module] = [];
    grouped[tc.module].push(tc);
  }
  return grouped;
}

function toFileName(moduleName: string, mode: TestMode): string {
  const nameMap: Record<string, string> = {
    '用户注册': 'register',
    '用户登录': 'login',
    '用户信息': 'me',
    '修改密码': 'password',
    '登录页面': 'login',
    '注册页面': 'register',
  };
  const eng = nameMap[moduleName] ?? moduleName.toLowerCase().replace(/[^a-z0-9]/g, '-');
  return `${eng}.${mode}.spec.ts`;
}

function generateApiScript(moduleName: string, cases: TestCase[]): string {
  const needsAuth = cases.some(tc =>
    tc.precondition.includes('token') || tc.precondition.includes('登录')
  );

  const endpoint = extractEndpoint(cases);
  const lines: string[] = [];

  lines.push(`import { test, expect, APIRequestContext } from '@playwright/test';`);
  lines.push(`import { env } from '../env.config';`);
  lines.push('');
  lines.push('let context: APIRequestContext;');
  if (needsAuth) lines.push('let authToken: string;');
  lines.push('');

  // beforeAll
  lines.push('test.beforeAll(async ({ playwright }) => {');
  lines.push('  context = await playwright.request.newContext({');
  lines.push('    baseURL: env.api.baseUrl,');
  lines.push('  });');
  if (needsAuth) {
    lines.push('  const loginRes = await context.post(\'/api/auth/login\', {');
    lines.push('    data: { email: env.testUser.email, password: env.testUser.password },');
    lines.push('  });');
    lines.push('  authToken = (await loginRes.json()).token;');
  }
  lines.push('});');
  lines.push('');
  lines.push('test.afterAll(async () => {');
  lines.push('  await context.dispose();');
  lines.push('});');
  lines.push('');

  // describe
  lines.push(`test.describe('${moduleName}', () => {`);

  for (const tc of cases) {
    const tag = `@${tc.priority}`;
    const testTitle = `${tc.id} ${toEnglishTitle(tc.title)}`;
    const { method, path: apiPath, body } = parseStepRequest(tc.steps);
    const expectedStatus = extractExpectedStatus(tc.expected);

    // Determine auth behavior from step description
    const noAuth = tc.steps.includes('不设置 Authorization') || tc.steps.includes('无 Authorization');
    const invalidToken = tc.steps.includes('invalid_token') || tc.title.includes('token 无效');
    const expiredToken = tc.steps.includes('expired_token') || tc.title.includes('token 过期');
    const noBearerPrefix = tc.steps.includes('无Bearer') || tc.steps.includes('无 Bearer') || tc.title.includes('缺少 Bearer');
    const useAuth = !noAuth && !invalidToken && !expiredToken && !noBearerPrefix
      && (tc.precondition.includes('token') || tc.steps.includes('Bearer {valid_token}'));

    lines.push('');
    lines.push(`  test('${testTitle}', { tag: '${tag}' }, async () => {`);

    // Build request
    const reqOpts: string[] = [];
    if (body !== null) reqOpts.push(`      data: ${body},`);

    if (noAuth) {
      // no auth header — intentional
    } else if (invalidToken) {
      reqOpts.push(`      headers: { Authorization: 'Bearer invalid_token_abc' },`);
    } else if (expiredToken) {
      reqOpts.push(`      headers: { Authorization: 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MSwiZXhwIjoxMDAwMDAwMDAwfQ.fake' },`);
    } else if (noBearerPrefix) {
      reqOpts.push(`      headers: { Authorization: authToken },`);
    } else if (useAuth) {
      reqOpts.push(`      headers: { Authorization: \`Bearer \${authToken}\` },`);
    }

    if (reqOpts.length > 0) {
      lines.push(`    const response = await context.${method.toLowerCase()}('${apiPath}', {`);
      lines.push(reqOpts.join('\n'));
      lines.push('    });');
    } else {
      lines.push(`    const response = await context.${method.toLowerCase()}('${apiPath}');`);
    }

    // Assertions
    if (expectedStatus) {
      lines.push(`    expect(response.status()).toBe(${expectedStatus});`);
    }

    // Body assertions for success cases
    if (expectedStatus && parseInt(expectedStatus) < 300) {
      const bodyAssertions = extractBodyAssertions(tc.expected);
      if (bodyAssertions.length > 0) {
        lines.push('    const body = await response.json();');
        for (const assertion of bodyAssertions) {
          lines.push(`    ${assertion}`);
        }
      }
    }

    lines.push('  });');
  }

  lines.push('});');
  lines.push('');

  return lines.join('\n');
}

function generateE2eScript(moduleName: string, cases: TestCase[]): string {
  const pageUrl = extractPageUrl(cases);
  const lines: string[] = [];

  lines.push(`import { test, expect } from '@playwright/test';`);
  lines.push(`import { env } from '../env.config';`);
  lines.push('');
  lines.push(`test.describe('${moduleName}', () => {`);
  lines.push('  test.beforeEach(async ({ page }) => {');
  lines.push(`    await page.goto(env.e2e.baseUrl + '${pageUrl}');`);
  lines.push('  });');

  for (const tc of cases) {
    const tag = `@${tc.priority}`;
    const testTitle = `${tc.id} ${toEnglishTitle(tc.title)}`;

    lines.push('');
    lines.push(`  test('${testTitle}', { tag: '${tag}' }, async ({ page }) => {`);

    const steps = parseE2eSteps(tc.steps);
    for (const step of steps) {
      lines.push(`    ${step}`);
    }

    lines.push('');
    const assertions = parseE2eAssertions(tc.expected);
    for (const assertion of assertions) {
      lines.push(`    ${assertion}`);
    }

    lines.push('  });');
  }

  lines.push('});');
  lines.push('');

  return lines.join('\n');
}

// --- Helper functions ---

function extractEndpoint(cases: TestCase[]): string {
  for (const tc of cases) {
    const match = tc.steps.match(/(GET|POST|PUT|PATCH|DELETE)\s+(\/\S+?)[\s，,]/);
    if (match) return match[2];
  }
  return '/api/unknown';
}

function parseStepRequest(steps: string): { method: string; path: string; body: string | null } {
  const methodMatch = steps.match(/(GET|POST|PUT|PATCH|DELETE)\s+(\/\S+?)[\s，,]/);
  const method = methodMatch?.[1] ?? 'GET';
  const apiPath = methodMatch?.[2] ?? '/api/unknown';

  const bodyMatch = steps.match(/body:\s*(\{[^}]*\})/);
  const body = bodyMatch?.[1] ?? null;

  return { method, path: apiPath, body };
}

function extractExpectedStatus(expected: string): string | null {
  const match = expected.match(/状态码\s*(\d{3})/);
  return match?.[1] ?? null;
}

function extractBodyAssertions(expected: string): string[] {
  const assertions: string[] = [];

  // "包含 xxx 字段"
  const fieldMatches = expected.matchAll(/包含\s*([\w、]+)/g);
  for (const m of fieldMatches) {
    const fields = m[1].split(/[、,]/).map(f => f.trim()).filter(Boolean);
    for (const field of fields) {
      if (/^[a-zA-Z]/.test(field)) {
        assertions.push(`expect(body).toHaveProperty('${field}');`);
      }
    }
  }

  // "不返回 xxx 字段"
  const notMatch = expected.match(/不返回\s*(\w+)\s*字段/);
  if (notMatch) {
    assertions.push(`expect(body).not.toHaveProperty('${notMatch[1]}');`);
  }

  return assertions;
}

function extractPageUrl(cases: TestCase[]): string {
  for (const tc of cases) {
    const match = tc.precondition.match(/\/\w[\w/-]*/);
    if (match) return match[0];
  }
  return '/';
}

function toEnglishTitle(title: string): string {
  const map: [RegExp, string][] = [
    [/验证正确信息?注册成功/, 'should register successfully with valid data'],
    [/验证正确邮箱密码登录成功/, 'should login successfully with valid credentials'],
    [/验证缺少\s*(\w+)\s*字段返回\s*(\d+)/, 'should return $2 when $1 is missing'],
    [/验证(\w+)为空字符串返回\s*(\d+)/, 'should return $2 when $1 is empty string'],
    [/验证空请求体返回\s*(\d+)/, 'should return $1 for empty request body'],
    [/验证邮箱格式不正确返回\s*(\d+)/, 'should return $1 for invalid email format'],
    [/验证邮箱已被注册返回\s*(\d+)/, 'should return $1 when email already registered'],
    [/验证邮箱不存在返回\s*(\d+)/, 'should return $1 for non-existent email'],
    [/验证密码错误返回\s*(\d+)/, 'should return $1 for wrong password'],
    [/验证密码不足.*返回\s*(\d+)/, 'should return $1 when password is too short'],
    [/验证密码缺少大写.*返回\s*(\d+)/, 'should return $1 when password has no uppercase'],
    [/验证密码缺少数字.*返回\s*(\d+)/, 'should return $1 when password has no digits'],
    [/验证携带有效\s*token\s*获取用户信息/, 'should return user info with valid token'],
    [/验证不携带\s*token\s*返回\s*(\d+)/, 'should return $1 without token'],
    [/验证\s*token\s*无效返回\s*(\d+)/, 'should return $1 with invalid token'],
    [/验证\s*token\s*过期返回\s*(\d+)/, 'should return $1 with expired token'],
    [/验证.*缺少\s*Bearer.*返回\s*(\d+)/, 'should return $1 without Bearer prefix'],
    [/验证修改密码成功/, 'should change password successfully'],
    [/验证旧密码错误返回\s*(\d+)/, 'should return $1 for wrong old password'],
    [/验证未认证返回\s*(\d+)/, 'should return $1 without auth'],
    [/验证新密码不足.*返回\s*(\d+)/, 'should return $1 when new password is too short'],
    [/验证新密码缺少大写.*返回\s*(\d+)/, 'should return $1 when new password has no uppercase'],
    [/验证新密码缺少数字.*返回\s*(\d+)/, 'should return $1 when new password has no digits'],
    [/验证缺少\s*oldPassword.*返回\s*(\d+)/, 'should return $1 when oldPassword is missing'],
    [/验证缺少\s*newPassword.*返回\s*(\d+)/, 'should return $1 when newPassword is missing'],
    [/验证新旧密码相同返回\s*(\d+)/, 'should return $1 when new password equals old'],
  ];

  for (const [pattern, replacement] of map) {
    if (pattern.test(title)) {
      return title.replace(pattern, replacement);
    }
  }

  return title;
}

function parseE2eSteps(steps: string): string[] {
  const lines: string[] = [];
  const parts = steps.split(/\d+\.\s*/).filter(Boolean);

  for (const part of parts) {
    const trimmed = part.trim();

    // 重复/循环操作
    if (/重复.*共?(\d+)次/.test(trimmed)) {
      const countMatch = trimmed.match(/共?(\d+)次/);
      const count = countMatch ? parseInt(countMatch[1]) : 3;
      lines.push(`for (let i = 0; i < ${count}; i++) {`);
      // Find the referenced steps and inline them
      const refMatch = trimmed.match(/重复步骤(\d+)-(\d+)/);
      if (refMatch) {
        // Re-parse referenced steps from the original parts
        const from = parseInt(refMatch[1]) - 1;
        const to = parseInt(refMatch[2]) - 1;
        const allParts = steps.split(/\d+\.\s*/).filter(Boolean);
        for (let s = from; s <= to && s < allParts.length; s++) {
          const subSteps = parseE2eSteps(`1. ${allParts[s]}`);
          for (const sub of subSteps) {
            lines.push(`  ${sub}`);
          }
        }
      }
      lines.push('}');
      continue;
    }

    // 勾选复选框
    if (/勾选/.test(trimmed)) {
      const checkMatch = trimmed.match(/勾选[「]?(.+?)[」]?(?:复选框)?$/);
      if (checkMatch) {
        lines.push(`await page.getByLabel('${checkMatch[1].trim()}').check();`);
      }
      continue;
    }

    // 点击链接
    if (/点击.*链接|点击[「].*[」]链接/.test(trimmed)) {
      const linkMatch = trimmed.match(/点击[「\s]*(.+?)[」\s]*链接/);
      if (linkMatch) {
        lines.push(`await page.getByRole('link', { name: '${linkMatch[1].trim()}' }).click();`);
      }
      continue;
    }

    // 点击按钮
    if (/点击.*按钮|点击[「].*[」]按钮/.test(trimmed)) {
      const btnMatch = trimmed.match(/点击[「\s]*(.+?)[」\s]*按钮/);
      if (btnMatch) {
        lines.push(`await page.getByRole('button', { name: '${btnMatch[1].trim()}' }).click();`);
      }
      continue;
    }

    // 通用点击（无明确按钮/链接标识）
    if (/^点击/.test(trimmed)) {
      const clickMatch = trimmed.match(/点击[「\s]*(.+?)[」\s]*$/);
      if (clickMatch) {
        lines.push(`await page.getByRole('button', { name: '${clickMatch[1].trim()}' }).click();`);
      }
      continue;
    }

    // 输入框输入
    if (/输入框输入|填写/.test(trimmed)) {
      const labelMatch = trimmed.match(/(?:在)?(.+?)(?:输入框)?(?:输入|填写)\s*(.+)/);
      if (labelMatch) {
        lines.push(`await page.getByLabel('${labelMatch[1].trim()}').fill('${labelMatch[2].trim()}');`);
      }
      continue;
    }

    // 留空 — 不操作
    if (/留空/.test(trimmed)) {
      continue;
    }
  }

  return lines;
}

function parseE2eAssertions(expected: string): string[] {
  const lines: string[] = [];
  // Split by numbered items: "1. xxx 2. xxx" or "1. xxx，2. xxx"
  const parts = expected.split(/\d+\.\s*/).filter(Boolean);

  for (const part of parts) {
    const trimmed = part.replace(/[，,]\s*$/, '').trim();

    // 页面跳转
    const urlMatch = trimmed.match(/(?:页面)?跳转到\s*(\/[\w/-]+)/);
    if (urlMatch) {
      lines.push(`await expect(page).toHaveURL('${urlMatch[1]}');`);
      continue;
    }

    // 显示某段文字
    const showMatch = trimmed.match(/显示[「"]?(.+?)[」"]?\s*$/);
    if (showMatch) {
      const text = showMatch[1].replace(/[，,。].*$/, '').trim();
      lines.push(`await expect(page.getByText('${text}')).toBeVisible();`);
      continue;
    }

    // 页面停留
    if (/页面停留/.test(trimmed)) {
      const stayMatch = trimmed.match(/停留在\s*(\/[\w/-]+)/);
      if (stayMatch) {
        lines.push(`await expect(page).toHaveURL('${stayMatch[1]}');`);
      }
      continue;
    }
  }

  return lines;
}
