import { test, expect, APIRequestContext } from '@playwright/test';
import { env } from '../env.config';

let context: APIRequestContext;
let authToken: string;

test.beforeAll(async ({ playwright }) => {
  context = await playwright.request.newContext({
    baseURL: env.api.baseUrl,
  });

  const loginResponse = await context.post('/api/auth/login', {
    data: { email: env.testUser.email, password: env.testUser.password },
  });
  const loginBody = await loginResponse.json();
  authToken = loginBody.token;
});

test.afterAll(async () => {
  await context.dispose();
});

test.describe('GET /api/auth/me', () => {
  const endpoint = '/api/auth/me';

  // TC-ME-001 验证携带有效 token 获取用户信息
  test('TC-ME-001 should return user info with valid token', async () => {
    const response = await context.get(endpoint, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('id');
    expect(body).toHaveProperty('username');
    expect(body).toHaveProperty('email');
    expect(body).toHaveProperty('createdAt');
    expect(new Date(body.createdAt).toString()).not.toBe('Invalid Date');
  });

  // TC-ME-002 验证不携带 token 返回 401
  test('TC-ME-002 should return 401 without token', async () => {
    const response = await context.get(endpoint);
    expect(response.status()).toBe(401);
  });

  // TC-ME-003 验证 token 无效返回 401
  test('TC-ME-003 should return 401 with invalid token', async () => {
    const response = await context.get(endpoint, {
      headers: { Authorization: 'Bearer invalid_token_abc' },
    });
    expect(response.status()).toBe(401);
  });

  // TC-ME-004 验证 token 过期返回 401
  test('TC-ME-004 should return 401 with expired token', async () => {
    const expiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MSwiZXhwIjoxMDAwMDAwMDAwfQ.fake';
    const response = await context.get(endpoint, {
      headers: { Authorization: `Bearer ${expiredToken}` },
    });
    expect(response.status()).toBe(401);
  });

  // TC-ME-005 验证 Authorization 缺少 Bearer 前缀返回 401
  test('TC-ME-005 should return 401 without Bearer prefix', async () => {
    const response = await context.get(endpoint, {
      headers: { Authorization: authToken },
    });
    expect(response.status()).toBe(401);
  });
});
