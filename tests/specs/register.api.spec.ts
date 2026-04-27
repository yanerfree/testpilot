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

test.describe('POST /api/auth/register', () => {
  const endpoint = '/api/auth/register';
  const uniqueEmail = () => `test_${Date.now()}@example.com`;

  // TC-REG-001 验证正确信息注册成功
  test('TC-REG-001 should register successfully with valid data', async () => {
    const email = uniqueEmail();
    const response = await context.post(endpoint, {
      data: { username: 'testuser', email, password: 'Abc123456' },
    });
    expect(response.status()).toBe(201);
    const body = await response.json();
    expect(body).toHaveProperty('id');
    expect(typeof body.id).toBe('number');
    expect(body.username).toBe('testuser');
    expect(body.email).toBe(email);
    expect(body).not.toHaveProperty('password');
  });

  // TC-REG-002 验证缺少 username 字段返回 400
  test('TC-REG-002 should return 400 when username is missing', async () => {
    const response = await context.post(endpoint, {
      data: { email: 'test@example.com', password: 'Abc123456' },
    });
    expect(response.status()).toBe(400);
  });

  // TC-REG-003 验证缺少 email 字段返回 400
  test('TC-REG-003 should return 400 when email is missing', async () => {
    const response = await context.post(endpoint, {
      data: { username: 'testuser', password: 'Abc123456' },
    });
    expect(response.status()).toBe(400);
  });

  // TC-REG-004 验证缺少 password 字段返回 400
  test('TC-REG-004 should return 400 when password is missing', async () => {
    const response = await context.post(endpoint, {
      data: { username: 'testuser', email: 'test@example.com' },
    });
    expect(response.status()).toBe(400);
  });

  // TC-REG-005 验证空请求体返回 400
  test('TC-REG-005 should return 400 for empty request body', async () => {
    const response = await context.post(endpoint, { data: {} });
    expect(response.status()).toBe(400);
  });

  // TC-REG-006 验证邮箱格式不正确返回 400
  test('TC-REG-006 should return 400 for invalid email format', async () => {
    const response = await context.post(endpoint, {
      data: { username: 'testuser', email: 'not-an-email', password: 'Abc123456' },
    });
    expect(response.status()).toBe(400);
  });

  // TC-REG-007 验证密码不足 8 位返回 400
  test('TC-REG-007 should return 400 when password is less than 8 chars', async () => {
    const response = await context.post(endpoint, {
      data: { username: 'testuser', email: 'test@example.com', password: 'Ab1' },
    });
    expect(response.status()).toBe(400);
  });

  // TC-REG-008 验证密码缺少大写字母返回 400
  test('TC-REG-008 should return 400 when password has no uppercase', async () => {
    const response = await context.post(endpoint, {
      data: { username: 'testuser', email: 'test@example.com', password: 'abc123456' },
    });
    expect(response.status()).toBe(400);
  });

  // TC-REG-009 验证密码缺少数字返回 400
  test('TC-REG-009 should return 400 when password has no digits', async () => {
    const response = await context.post(endpoint, {
      data: { username: 'testuser', email: 'test@example.com', password: 'Abcdefghi' },
    });
    expect(response.status()).toBe(400);
  });

  // TC-REG-010 验证邮箱已被注册返回 409
  test('TC-REG-010 should return 409 when email already registered', async () => {
    const email = uniqueEmail();
    await context.post(endpoint, {
      data: { username: 'first', email, password: 'Abc123456' },
    });
    const response = await context.post(endpoint, {
      data: { username: 'second', email, password: 'Abc123456' },
    });
    expect(response.status()).toBe(409);
  });

  // TC-REG-011 验证 username 为空字符串返回 400
  test('TC-REG-011 should return 400 when username is empty string', async () => {
    const response = await context.post(endpoint, {
      data: { username: '', email: 'test@example.com', password: 'Abc123456' },
    });
    expect(response.status()).toBe(400);
  });

  // TC-REG-012 验证 email 为空字符串返回 400
  test('TC-REG-012 should return 400 when email is empty string', async () => {
    const response = await context.post(endpoint, {
      data: { username: 'testuser', email: '', password: 'Abc123456' },
    });
    expect(response.status()).toBe(400);
  });
});
