import { test, expect, APIRequestContext } from '@playwright/test';
import { env } from '../env.config';

let context: APIRequestContext;

test.beforeAll(async ({ playwright }) => {
  context = await playwright.request.newContext({
    baseURL: env.api.baseUrl,
  });
});

test.afterAll(async () => {
  await context.dispose();
});

test.describe('POST /api/auth/login', () => {
  const endpoint = '/api/auth/login';

  // TC-LOG-001 验证正确邮箱密码登录成功
  test('TC-LOG-001 should return token and user on valid credentials', async () => {
    const response = await context.post(endpoint, {
      data: { email: env.testUser.email, password: env.testUser.password },
    });
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('token');
    expect(typeof body.token).toBe('string');
    expect(body.token.length).toBeGreaterThan(0);
    expect(body).toHaveProperty('user');
    expect(body.user).toHaveProperty('id');
    expect(body.user).toHaveProperty('username');
    expect(body.user).toHaveProperty('email');
  });

  // TC-LOG-002 验证密码错误返回 401
  test('TC-LOG-002 should return 401 for wrong password', async () => {
    const response = await context.post(endpoint, {
      data: { email: env.testUser.email, password: 'WrongPass123' },
    });
    expect(response.status()).toBe(401);
  });

  // TC-LOG-003 验证邮箱不存在返回 401
  test('TC-LOG-003 should return 401 for non-existent email', async () => {
    const response = await context.post(endpoint, {
      data: { email: 'noexist@example.com', password: 'Abc123456' },
    });
    expect(response.status()).toBe(401);
  });

  // TC-LOG-004 验证缺少 email 字段返回 400
  test('TC-LOG-004 should return 400 when email is missing', async () => {
    const response = await context.post(endpoint, {
      data: { password: 'Abc123456' },
    });
    expect(response.status()).toBe(400);
  });

  // TC-LOG-005 验证缺少 password 字段返回 400
  test('TC-LOG-005 should return 400 when password is missing', async () => {
    const response = await context.post(endpoint, {
      data: { email: env.testUser.email },
    });
    expect(response.status()).toBe(400);
  });

  // TC-LOG-006 验证空请求体返回 400
  test('TC-LOG-006 should return 400 for empty request body', async () => {
    const response = await context.post(endpoint, { data: {} });
    expect(response.status()).toBe(400);
  });
});
