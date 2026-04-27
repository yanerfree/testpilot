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

test.describe('PUT /api/auth/password', () => {
  const endpoint = '/api/auth/password';

  // TC-PWD-001 验证修改密码成功
  test('TC-PWD-001 should change password successfully', async () => {
    const newPassword = `New${Date.now()}`.slice(0, 12);
    const response = await context.put(endpoint, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { oldPassword: env.testUser.password, newPassword },
    });
    expect(response.status()).toBe(200);

    const loginWithNew = await context.post('/api/auth/login', {
      data: { email: env.testUser.email, password: newPassword },
    });
    expect(loginWithNew.status()).toBe(200);

    const loginWithOld = await context.post('/api/auth/login', {
      data: { email: env.testUser.email, password: env.testUser.password },
    });
    expect(loginWithOld.status()).toBe(401);

    // Restore original password
    const restoreLogin = await loginWithNew.json();
    await context.put(endpoint, {
      headers: { Authorization: `Bearer ${restoreLogin.token}` },
      data: { oldPassword: newPassword, newPassword: env.testUser.password },
    });
  });

  // TC-PWD-002 验证旧密码错误返回 401
  test('TC-PWD-002 should return 401 for wrong old password', async () => {
    const response = await context.put(endpoint, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { oldPassword: 'WrongOld123', newPassword: 'Xyz789012' },
    });
    expect(response.status()).toBe(401);
  });

  // TC-PWD-003 验证未认证返回 401
  test('TC-PWD-003 should return 401 without auth token', async () => {
    const response = await context.put(endpoint, {
      data: { oldPassword: 'Abc123456', newPassword: 'Xyz789012' },
    });
    expect(response.status()).toBe(401);
  });

  // TC-PWD-004 验证新密码不足 8 位返回 400
  test('TC-PWD-004 should return 400 when new password is too short', async () => {
    const response = await context.put(endpoint, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { oldPassword: env.testUser.password, newPassword: 'Xy7' },
    });
    expect(response.status()).toBe(400);
  });

  // TC-PWD-005 验证新密码缺少大写字母返回 400
  test('TC-PWD-005 should return 400 when new password has no uppercase', async () => {
    const response = await context.put(endpoint, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { oldPassword: env.testUser.password, newPassword: 'xyz789012' },
    });
    expect(response.status()).toBe(400);
  });

  // TC-PWD-006 验证新密码缺少数字返回 400
  test('TC-PWD-006 should return 400 when new password has no digits', async () => {
    const response = await context.put(endpoint, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { oldPassword: env.testUser.password, newPassword: 'Xyzabcdef' },
    });
    expect(response.status()).toBe(400);
  });

  // TC-PWD-007 验证缺少 oldPassword 字段返回 400
  test('TC-PWD-007 should return 400 when oldPassword is missing', async () => {
    const response = await context.put(endpoint, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { newPassword: 'Xyz789012' },
    });
    expect(response.status()).toBe(400);
  });

  // TC-PWD-008 验证缺少 newPassword 字段返回 400
  test('TC-PWD-008 should return 400 when newPassword is missing', async () => {
    const response = await context.put(endpoint, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { oldPassword: env.testUser.password },
    });
    expect(response.status()).toBe(400);
  });

  // TC-PWD-009 验证新旧密码相同返回 400
  test('TC-PWD-009 should return 400 when new password equals old password', async () => {
    const response = await context.put(endpoint, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { oldPassword: env.testUser.password, newPassword: env.testUser.password },
    });
    expect(response.status()).toBe(400);
  });
});
