import { test, expect, APIRequestContext } from '@playwright/test';
import { env } from '../env.config';

const ENDPOINT = '/api/auth/change-password';
const LOGIN_ENDPOINT = '/api/auth/login';

let context: APIRequestContext;
let authToken: string;

async function login(ctx: APIRequestContext, password?: string): Promise<string> {
  const res = await ctx.post(LOGIN_ENDPOINT, {
    data: { username: env.testUser.username, password: password ?? env.testUser.password },
  });
  expect(res.status()).toBe(200);
  return (await res.json()).data.token;
}

async function changePassword(ctx: APIRequestContext, token: string, oldPwd: string, newPwd: string) {
  return ctx.post(ENDPOINT, {
    headers: { Authorization: `Bearer ${token}` },
    data: { oldPassword: oldPwd, newPassword: newPwd },
  });
}

test.beforeAll(async ({ playwright }) => {
  context = await playwright.request.newContext({
    baseURL: env.api.baseUrl,
  });
  authToken = await login(context);
});

test.afterAll(async () => {
  await context.dispose();
});

test.describe('修改密码 POST /api/auth/change-password', () => {

  // TC-CHPWD-001 验证正确原密码修改密码成功
  test('TC-CHPWD-001 should change password successfully', { tag: '@P0' }, async () => {
    const newPassword = 'NewPass789';
    const response = await changePassword(context, authToken, env.testUser.password, newPassword);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.message).toBe('密码修改成功');

    try {
      const loginWithNew = await context.post(LOGIN_ENDPOINT, {
        data: { username: env.testUser.username, password: newPassword },
      });
      expect(loginWithNew.status()).toBe(200);

      const loginWithOld = await context.post(LOGIN_ENDPOINT, {
        data: { username: env.testUser.username, password: env.testUser.password },
      });
      expect(loginWithOld.status()).not.toBe(200);
    } finally {
      const tmpToken = await login(context, newPassword);
      await changePassword(context, tmpToken, newPassword, env.testUser.password);
      authToken = await login(context);
    }
  });

  // TC-CHPWD-002 验证修改密码后旧 token 是否失效
  test('TC-CHPWD-002 should check old token status after password change', { tag: '@P1' }, async () => {
    const oldToken = authToken;
    const newPassword = 'TmpPwd789';

    const response = await changePassword(context, oldToken, env.testUser.password, newPassword);
    expect(response.status()).toBe(200);

    try {
      const meResponse = await context.get('/api/auth/me', {
        headers: { Authorization: `Bearer ${oldToken}` },
      });
      expect([200, 401]).toContain(meResponse.status());
    } finally {
      const tmpToken = await login(context, newPassword);
      await changePassword(context, tmpToken, newPassword, env.testUser.password);
      authToken = await login(context);
    }
  });

  // TC-CHPWD-003 验证原密码错误返回 422
  test('TC-CHPWD-003 should return 422 for wrong old password', { tag: '@P1' }, async () => {
    const response = await changePassword(context, authToken, 'wrongPassword', 'newPass456');
    expect(response.status()).toBe(422);
    const body = await response.json();
    expect(body.error.code).toBe('WRONG_PASSWORD');
    expect(body.error.message).toBe('原密码错误');
  });

  // TC-CHPWD-004 验证未携带 token 返回 401
  // 注意：后端实际返回 MISSING_TOKEN，与 Swagger 定义的 UNAUTHORIZED 不一致
  test('TC-CHPWD-004 should return 401 without token', { tag: '@P1' }, async () => {
    const response = await context.post(ENDPOINT, {
      data: { oldPassword: env.testUser.password, newPassword: 'newPass456' },
    });
    expect(response.status()).toBe(401);
    const body = await response.json();
    expect(body.error.code).toBe('MISSING_TOKEN');
  });

  // TC-CHPWD-005 验证 token 已过期返回 401
  test('TC-CHPWD-005 should return 401 with expired token', { tag: '@P1' }, async () => {
    const expiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MSwiZXhwIjoxMDAwMDAwMDAwfQ.fake';
    const response = await changePassword(context, expiredToken, env.testUser.password, 'newPass456');
    expect(response.status()).toBe(401);
  });

  // TC-CHPWD-006 验证 token 无效返回 401
  test('TC-CHPWD-006 should return 401 with invalid token', { tag: '@P1' }, async () => {
    const response = await context.post(ENDPOINT, {
      headers: { Authorization: 'Bearer invalid_token_abc' },
      data: { oldPassword: env.testUser.password, newPassword: 'newPass456' },
    });
    expect(response.status()).toBe(401);
  });

  // TC-CHPWD-007 验证新密码不足 6 位返回 422
  // 注意：后端实际返回 Pydantic 校验格式 {"detail":[...]}, 与 Swagger 定义的 ErrorEnvelope 不一致
  test('TC-CHPWD-007 should return 422 when new password less than 6 chars', { tag: '@P1' }, async () => {
    const response = await changePassword(context, authToken, env.testUser.password, 'abc');
    expect(response.status()).toBe(422);
    const body = await response.json();
    expect(body.detail).toBeDefined();
    expect(body.detail[0].type).toBe('string_too_short');
  });

  // TC-CHPWD-008 验证新密码恰好 6 位通过校验
  test('TC-CHPWD-008 should accept new password with exactly 6 chars', { tag: '@P2' }, async () => {
    const sixCharPwd = 'abcdef';
    const response = await changePassword(context, authToken, env.testUser.password, sixCharPwd);
    expect(response.status()).toBe(200);

    try {
      await login(context, sixCharPwd);
    } finally {
      const tmpToken = await login(context, sixCharPwd);
      await changePassword(context, tmpToken, sixCharPwd, env.testUser.password);
      authToken = await login(context);
    }
  });

  // TC-CHPWD-009 验证缺少 oldPassword 字段返回 422
  test('TC-CHPWD-009 should return 422 when oldPassword is missing', { tag: '@P1' }, async () => {
    const response = await context.post(ENDPOINT, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { newPassword: 'newPass456' },
    });
    expect(response.status()).toBe(422);
  });

  // TC-CHPWD-010 验证缺少 newPassword 字段返回 422
  test('TC-CHPWD-010 should return 422 when newPassword is missing', { tag: '@P1' }, async () => {
    const response = await context.post(ENDPOINT, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { oldPassword: env.testUser.password },
    });
    expect(response.status()).toBe(422);
  });

  // TC-CHPWD-011 验证空请求体返回 422
  test('TC-CHPWD-011 should return 422 for empty request body', { tag: '@P2' }, async () => {
    const response = await context.post(ENDPOINT, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: {},
    });
    expect(response.status()).toBe(422);
  });

  // TC-CHPWD-012 验证 oldPassword 为空字符串返回 422
  test('TC-CHPWD-012 should return 422 when oldPassword is empty string', { tag: '@P2' }, async () => {
    const response = await changePassword(context, authToken, '', 'newPass456');
    expect(response.status()).toBe(422);
  });

  // TC-CHPWD-013 验证 newPassword 为空字符串返回 422
  test('TC-CHPWD-013 should return 422 when newPassword is empty string', { tag: '@P2' }, async () => {
    const response = await changePassword(context, authToken, env.testUser.password, '');
    expect(response.status()).toBe(422);
  });

  // TC-CHPWD-014 验证新旧密码相同
  test('TC-CHPWD-014 should handle same old and new password', { tag: '@P2' }, async () => {
    const response = await changePassword(context, authToken, env.testUser.password, env.testUser.password);
    expect([200, 422]).toContain(response.status());
    if (response.status() === 200) {
      authToken = await login(context);
    }
  });

  // TC-CHPWD-015 验证 Authorization 缺少 Bearer 前缀返回 401
  test('TC-CHPWD-015 should return 401 without Bearer prefix', { tag: '@P2' }, async () => {
    const response = await context.post(ENDPOINT, {
      headers: { Authorization: authToken },
      data: { oldPassword: env.testUser.password, newPassword: 'newPass456' },
    });
    expect(response.status()).toBe(401);
  });

  // TC-CHPWD-016 验证新密码包含特殊字符可以成功
  test('TC-CHPWD-016 should accept new password with special characters', { tag: '@P2' }, async () => {
    const specialPwd = 'P@ss!#456';
    const response = await changePassword(context, authToken, env.testUser.password, specialPwd);
    expect(response.status()).toBe(200);

    try {
      await login(context, specialPwd);
    } finally {
      const tmpToken = await login(context, specialPwd);
      await changePassword(context, tmpToken, specialPwd, env.testUser.password);
      authToken = await login(context);
    }
  });

  // TC-CHPWD-017 验证请求 Content-Type 非 JSON 的处理
  test('TC-CHPWD-017 should reject non-JSON content type', { tag: '@P3' }, async () => {
    const response = await context.fetch(ENDPOINT, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'text/plain',
      },
      data: 'oldPassword=current123&newPassword=newPass456',
    });
    expect([400, 415, 422]).toContain(response.status());
  });
});
