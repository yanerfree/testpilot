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

test.describe('用户注册', () => {

  test('TC-REG-001 should register successfully with valid data', { tag: '@P0' }, async () => {
    const response = await context.post('/api/auth/register', {
      data: {"username":"testuser","email":"test@example.com","password":"Abc123456"},
    });
    expect(response.status()).toBe(201);
    const body = await response.json();
    expect(body).toHaveProperty('id');
    expect(body).not.toHaveProperty('password');
  });

  test('TC-REG-002 should return 400 when username is missing', { tag: '@P1' }, async () => {
    const response = await context.post('/api/auth/register', {
      data: {"email":"test@example.com","password":"Abc123456"},
    });
    expect(response.status()).toBe(400);
  });

  test('TC-REG-003 should return 400 when email is missing', { tag: '@P1' }, async () => {
    const response = await context.post('/api/auth/register', {
      data: {"username":"testuser","password":"Abc123456"},
    });
    expect(response.status()).toBe(400);
  });

  test('TC-REG-004 should return 400 when password is missing', { tag: '@P1' }, async () => {
    const response = await context.post('/api/auth/register', {
      data: {"username":"testuser","email":"test@example.com"},
    });
    expect(response.status()).toBe(400);
  });

  test('TC-REG-005 should return 400 for empty request body', { tag: '@P2' }, async () => {
    const response = await context.post('/api/auth/register', {
      data: {},
    });
    expect(response.status()).toBe(400);
  });

  test('TC-REG-006 should return 400 for invalid email format', { tag: '@P2' }, async () => {
    const response = await context.post('/api/auth/register', {
      data: {"username":"testuser","email":"not-an-email","password":"Abc123456"},
    });
    expect(response.status()).toBe(400);
  });

  test('TC-REG-007 should return 400 when password is too short', { tag: '@P2' }, async () => {
    const response = await context.post('/api/auth/register', {
      data: {"username":"testuser","email":"test@example.com","password":"Ab1"},
    });
    expect(response.status()).toBe(400);
  });

  test('TC-REG-008 should return 400 when password has no uppercase', { tag: '@P2' }, async () => {
    const response = await context.post('/api/auth/register', {
      data: {"username":"testuser","email":"test@example.com","password":"abc123456"},
    });
    expect(response.status()).toBe(400);
  });

  test('TC-REG-009 should return 400 when password has no digits', { tag: '@P2' }, async () => {
    const response = await context.post('/api/auth/register', {
      data: {"username":"testuser","email":"test@example.com","password":"Abcdefghi"},
    });
    expect(response.status()).toBe(400);
  });

  test('TC-REG-010 should return 409 when email already registered', { tag: '@P1' }, async () => {
    const response = await context.post('/api/auth/register', {
      data: {"username":"another","email":"test@example.com","password":"Abc123456"},
    });
    expect(response.status()).toBe(409);
  });

  test('TC-REG-011 验证 username 为空字符串返回 400', { tag: '@P2' }, async () => {
    const response = await context.post('/api/auth/register', {
      data: {"username":"","email":"test@example.com","password":"Abc123456"},
    });
    expect(response.status()).toBe(400);
  });

  test('TC-REG-012 验证 email 为空字符串返回 400', { tag: '@P2' }, async () => {
    const response = await context.post('/api/auth/register', {
      data: {"username":"testuser","email":"","password":"Abc123456"},
    });
    expect(response.status()).toBe(400);
  });
});
