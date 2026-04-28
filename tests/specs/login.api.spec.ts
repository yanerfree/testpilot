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

test.describe('用户登录', () => {

  test('TC-LOG-001 should login successfully with valid credentials', { tag: '@P0' }, async () => {
    const response = await context.post('/api/auth/login', {
      data: {"email":"test@example.com","password":"Abc123456"},
    });
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('token');
    expect(body).toHaveProperty('id');
    expect(body).toHaveProperty('username');
    expect(body).toHaveProperty('email');
  });

  test('TC-LOG-002 should return 401 for wrong password', { tag: '@P1' }, async () => {
    const response = await context.post('/api/auth/login', {
      data: {"email":"test@example.com","password":"WrongPass123"},
    });
    expect(response.status()).toBe(401);
  });

  test('TC-LOG-003 should return 401 for non-existent email', { tag: '@P1' }, async () => {
    const response = await context.post('/api/auth/login', {
      data: {"email":"noexist@example.com","password":"Abc123456"},
    });
    expect(response.status()).toBe(401);
  });

  test('TC-LOG-004 should return 400 when email is missing', { tag: '@P1' }, async () => {
    const response = await context.post('/api/auth/login', {
      data: {"password":"Abc123456"},
    });
    expect(response.status()).toBe(400);
  });

  test('TC-LOG-005 should return 400 when password is missing', { tag: '@P1' }, async () => {
    const response = await context.post('/api/auth/login', {
      data: {"email":"test@example.com"},
    });
    expect(response.status()).toBe(400);
  });

  test('TC-LOG-006 should return 400 for empty request body', { tag: '@P2' }, async () => {
    const response = await context.post('/api/auth/login', {
      data: {},
    });
    expect(response.status()).toBe(400);
  });
});
