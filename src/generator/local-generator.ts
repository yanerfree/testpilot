import type { ParsedInput, Endpoint } from '../parsers/types.js';
import type { TestMode } from '../llm/types.js';

const TABLE_HEADER = `| 用例ID | 标题 | 模块 | 测试类型 | 优先级 | 前置条件 | 测试步骤 | 预期结果 |
|--------|------|------|---------|--------|---------|---------|---------|`;

export function generateTestCasesLocally(input: ParsedInput, mode: TestMode, baseUrl: string): string {
  if (mode === 'api') {
    return generateApiCases(input, baseUrl);
  }
  return generateE2eCases(input, baseUrl);
}

function generateApiCases(input: ParsedInput, baseUrl: string): string {
  const rows: string[] = [TABLE_HEADER];

  for (const ep of input.endpoints) {
    const prefix = buildIdPrefix(ep);
    const module = inferModule(ep);
    let seq = 1;

    // P0: 正常流程
    rows.push(row(
      `TC-${prefix}-${pad(seq++)}`,
      `验证${ep.method} ${ep.path} 正常请求成功`,
      module,
      '功能测试',
      'P0',
      buildPrecondition(ep),
      `1. 发送 ${ep.method} ${ep.path}${ep.requestBody ? `，body: ${JSON.stringify(ep.requestBody)}` : ''}${needsAuth(ep) ? `，Header: Authorization: Bearer {valid_token}` : ''}`,
      buildSuccessExpectation(ep),
    ));

    // P1: 必填字段缺失
    if (ep.requestBody && typeof ep.requestBody === 'object') {
      const fields = Object.keys(ep.requestBody as Record<string, unknown>);
      for (const field of fields) {
        const partial = { ...(ep.requestBody as Record<string, unknown>) };
        delete partial[field];
        rows.push(row(
          `TC-${prefix}-${pad(seq++)}`,
          `验证缺少 ${field} 字段返回 400`,
          module,
          '参数校验',
          'P1',
          '无',
          `1. 发送 ${ep.method} ${ep.path}，body: ${JSON.stringify(partial)}${needsAuth(ep) ? `，Header: Authorization: Bearer {valid_token}` : ''}`,
          `1. 状态码 400 2. 返回错误信息提示 ${field} 必填`,
        ));
      }
    }

    // P2: 空请求体
    if (ep.requestBody) {
      rows.push(row(
        `TC-${prefix}-${pad(seq++)}`,
        `验证空请求体返回 400`,
        module,
        '边界条件',
        'P2',
        '无',
        `1. 发送 ${ep.method} ${ep.path}，body: {}${needsAuth(ep) ? `，Header: Authorization: Bearer {valid_token}` : ''}`,
        `1. 状态码 400`,
      ));
    }

    // 从 responses 生成异常用例
    if (ep.responses) {
      for (const resp of ep.responses) {
        if (resp.status >= 400 && resp.description) {
          const already = rows.some(r => r.includes(`状态码 ${resp.status}`) && r.includes(prefix));
          if (!already) {
            rows.push(row(
              `TC-${prefix}-${pad(seq++)}`,
              `验证${resp.description}返回 ${resp.status}`,
              module,
              resp.status === 401 || resp.status === 403 ? '异常场景' : resp.status === 409 ? '业务规则' : '异常场景',
              resp.status === 401 ? 'P1' : 'P2',
              '无',
              `1. 构造触发"${resp.description}"的请求，发送 ${ep.method} ${ep.path}`,
              `1. 状态码 ${resp.status} 2. 返回错误信息"${resp.description}"`,
            ));
          }
        }
      }
    }

    // P1: 未认证（需要认证的接口）
    if (needsAuth(ep)) {
      rows.push(row(
        `TC-${prefix}-${pad(seq++)}`,
        `验证未携带 token 返回 401`,
        module,
        '异常场景',
        'P1',
        '无',
        `1. 发送 ${ep.method} ${ep.path}${ep.requestBody ? `，body: ${JSON.stringify(ep.requestBody)}` : ''}，不设置 Authorization Header`,
        `1. 状态码 401`,
      ));

      rows.push(row(
        `TC-${prefix}-${pad(seq++)}`,
        `验证 token 无效返回 401`,
        module,
        '异常场景',
        'P1',
        '无',
        `1. 发送 ${ep.method} ${ep.path}${ep.requestBody ? `，body: ${JSON.stringify(ep.requestBody)}` : ''}，Header: Authorization: Bearer invalid_token`,
        `1. 状态码 401`,
      ));
    }
  }

  return rows.join('\n');
}

function generateE2eCases(input: ParsedInput, baseUrl: string): string {
  const rows: string[] = [TABLE_HEADER];

  for (const page of input.pages) {
    const prefix = buildPageIdPrefix(page.name);
    const module = page.name;
    let seq = 1;

    // P0: 页面正常加载
    rows.push(row(
      `TC-${prefix}-${pad(seq++)}`,
      `验证${page.name}正常加载`,
      module,
      '功能测试',
      'P0',
      '已打开浏览器',
      `1. 访问 ${baseUrl}${page.url ?? '/'}`,
      `1. 页面正常加载，无报错 2. 页面关键元素可见`,
    ));

    // 从 actions + assertions 生成正常流程
    if (page.actions && page.actions.length > 0 && page.assertions && page.assertions.length > 0) {
      const steps = page.actions.map((a, i) => `${i + 1}. ${a}`).join(' ');
      const expects = page.assertions.filter(a => /成功|跳转/.test(a));
      if (expects.length > 0) {
        rows.push(row(
          `TC-${prefix}-${pad(seq++)}`,
          `验证${page.name}正常操作流程`,
          module,
          '功能测试',
          'P0',
          `1. 已打开 ${page.url ?? '/'} 页面`,
          steps,
          expects.map((e, i) => `${i + 1}. ${e}`).join(' '),
        ));
      }
    }

    // 从 assertions 中提取校验类用例
    if (page.assertions) {
      for (const assertion of page.assertions) {
        if (/为空|格式|不正确|不一致|少于|至少/.test(assertion)) {
          rows.push(row(
            `TC-${prefix}-${pad(seq++)}`,
            `验证${assertion.replace(/显示|时/, '')}`,
            module,
            '表单校验',
            'P1',
            `1. 已打开 ${page.url ?? '/'} 页面`,
            `1. 构造触发该校验的输入 2. 提交表单`,
            `1. ${assertion}`,
          ));
        } else if (/错误|失败|锁定/.test(assertion)) {
          rows.push(row(
            `TC-${prefix}-${pad(seq++)}`,
            `验证${assertion.replace(/显示/, '')}`,
            module,
            '异常场景',
            'P1',
            `1. 已打开 ${page.url ?? '/'} 页面`,
            `1. 构造触发该场景的操作`,
            `1. ${assertion}`,
          ));
        }
      }
    }

    // 页面导航：从 elements 中找链接
    if (page.elements) {
      for (const el of page.elements) {
        if (/链接|link|跳转/.test(el.name)) {
          rows.push(row(
            `TC-${prefix}-${pad(seq++)}`,
            `验证点击${el.name}正确跳转`,
            module,
            '页面导航',
            'P1',
            `1. 已打开 ${page.url ?? '/'} 页面`,
            `1. 点击「${el.name.replace(/链接|link/gi, '').trim() || el.name}」`,
            `1. 页面跳转到对应目标页面`,
          ));
        }
      }
    }
  }

  return rows.join('\n');
}

function row(...cells: string[]): string {
  return `| ${cells.join(' | ')} |`;
}

function pad(n: number): string {
  return String(n).padStart(3, '0');
}

function buildIdPrefix(ep: Endpoint): string {
  const parts = ep.path.split('/').filter(Boolean);
  const last = parts[parts.length - 1] ?? 'API';
  return last.replace(/[^a-zA-Z]/g, '').toUpperCase().slice(0, 6) || 'API';
}

function buildPageIdPrefix(name: string): string {
  const map: Record<string, string> = {
    '登录': 'LOGIN', '注册': 'REG', '首页': 'HOME', '列表': 'LIST',
    '详情': 'DETAIL', '设置': 'SET', '个人': 'PROF',
  };
  for (const [key, val] of Object.entries(map)) {
    if (name.includes(key)) return val;
  }
  return name.replace(/页面|page/gi, '').trim().toUpperCase().slice(0, 6) || 'PAGE';
}

function inferModule(ep: Endpoint): string {
  const path = ep.path.toLowerCase();
  if (path.includes('register') || path.includes('signup')) return '用户注册';
  if (path.includes('login') || path.includes('signin')) return '用户登录';
  if (path.includes('password')) return '修改密码';
  if (path.includes('auth/me') || path.includes('profile')) return '用户信息';
  if (path.includes('auth')) return '用户认证';
  const parts = path.split('/').filter(Boolean);
  return parts[parts.length - 1] ?? 'API';
}

function needsAuth(ep: Endpoint): boolean {
  const summary = (ep.summary ?? '').toLowerCase();
  if (summary.includes('认证') || summary.includes('token') || summary.includes('bearer') || summary.includes('auth')) {
    return true;
  }
  if (ep.responses?.some(r => r.status === 401)) return true;
  if (ep.method === 'GET' || ep.method === 'PUT' || ep.method === 'DELETE' || ep.method === 'PATCH') {
    if (ep.path.includes('/me') || ep.path.includes('/password') || ep.path.includes('/profile')) return true;
  }
  return false;
}

function buildPrecondition(ep: Endpoint): string {
  const parts: string[] = [];
  if (needsAuth(ep)) parts.push('已注册并登录，获取有效 token');
  if (ep.path.includes('login')) parts.push('已注册用户');
  if (ep.path.includes('password')) parts.push('当前密码已知');
  return parts.length > 0 ? parts.join('，') : '无';
}

function buildSuccessExpectation(ep: Endpoint): string {
  const success = ep.responses?.find(r => r.status >= 200 && r.status < 300);
  if (success) {
    return `1. 状态码 ${success.status} 2. ${success.description ?? '返回成功'}`;
  }
  return `1. 状态码 200`;
}
