import { test, expect, APIRequestContext } from '@playwright/test';
import { env } from '../env.config';

let context: APIRequestContext;
let authToken: string;

test.beforeAll(async ({ playwright }) => {
  context = await playwright.request.newContext({
    baseURL: env.api.baseUrl,
  });
  const loginRes = await context.post('/api/auth/login', {
    data: { email: env.testUser.email, password: env.testUser.password },
  });
  authToken = (await loginRes.json()).token;
});

test.afterAll(async () => {
  await context.dispose();
});

test.describe('用户信息', () => {

  test('TC-ME-001 should return user info with valid token', { tag: '@P0' }, async () => {
    const response = await context.get('/api/auth/me', {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('id');
    expect(body).toHaveProperty('username');
    expect(body).toHaveProperty('email');
    expect(body).toHaveProperty('createdAt');
  });

  test('TC-ME-002 should return 401 without token', { tag: '@P1' }, async () => {
    const response = await context.get('/api/auth/me');
    expect(response.status()).toBe(401);
  });

  test('TC-ME-003 should return 401 with invalid token', { tag: '@P1' }, async () => {
    const response = await context.get('/api/auth/me', {
      headers: { Authorization: 'Bearer invalid_token_abc' },
    });
    expect(response.status()).toBe(401);
  });

  test('TC-ME-004 should return 401 with expired token', { tag: '@P2' }, async () => {
    const response = await context.get('/api/auth/me', {
      headers: { Authorization: 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MSwiZXhwIjoxMDAwMDAwMDAwfQ.fake' },
    });
    expect(response.status()).toBe(401);
  });

  test('TC-ME-005 should return 401 without Bearer prefix', { tag: '@P2' }, async () => {
    const response = await context.get('/api/auth/me', {
      headers: { Authorization: authToken },
    });
    expect(response.status()).toBe(401);
  });
});
