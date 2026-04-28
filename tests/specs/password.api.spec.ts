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

test.describe('修改密码', () => {

  test('TC-PWD-001 should change password successfully', { tag: '@P0' }, async () => {
    const response = await context.put('/api/auth/password', {
      data: {"oldPassword":"Abc123456","newPassword":"Xyz789012"},
      headers: { Authorization: `Bearer ${authToken}` },
    });
    expect(response.status()).toBe(200);
  });

  test('TC-PWD-002 should return 401 for wrong old password', { tag: '@P1' }, async () => {
    const response = await context.put('/api/auth/password', {
      data: {"oldPassword":"WrongOld123","newPassword":"Xyz789012"},
      headers: { Authorization: `Bearer ${authToken}` },
    });
    expect(response.status()).toBe(401);
  });

  test('TC-PWD-003 should return 401 without auth', { tag: '@P1' }, async () => {
    const response = await context.put('/api/auth/password', {
      data: {"oldPassword":"Abc123456","newPassword":"Xyz789012"},
    });
    expect(response.status()).toBe(401);
  });

  test('TC-PWD-004 should return 400 when new password is too short', { tag: '@P2' }, async () => {
    const response = await context.put('/api/auth/password', {
      data: {"oldPassword":"Abc123456","newPassword":"Xy7"},
      headers: { Authorization: `Bearer ${authToken}` },
    });
    expect(response.status()).toBe(400);
  });

  test('TC-PWD-005 should return 400 when new password has no uppercase', { tag: '@P2' }, async () => {
    const response = await context.put('/api/auth/password', {
      data: {"oldPassword":"Abc123456","newPassword":"xyz789012"},
      headers: { Authorization: `Bearer ${authToken}` },
    });
    expect(response.status()).toBe(400);
  });

  test('TC-PWD-006 should return 400 when new password has no digits', { tag: '@P2' }, async () => {
    const response = await context.put('/api/auth/password', {
      data: {"oldPassword":"Abc123456","newPassword":"Xyzabcdef"},
      headers: { Authorization: `Bearer ${authToken}` },
    });
    expect(response.status()).toBe(400);
  });

  test('TC-PWD-007 should return 400 when oldPassword is missing', { tag: '@P2' }, async () => {
    const response = await context.put('/api/auth/password', {
      data: {"newPassword":"Xyz789012"},
      headers: { Authorization: `Bearer ${authToken}` },
    });
    expect(response.status()).toBe(400);
  });

  test('TC-PWD-008 should return 400 when newPassword is missing', { tag: '@P2' }, async () => {
    const response = await context.put('/api/auth/password', {
      data: {"oldPassword":"Abc123456"},
      headers: { Authorization: `Bearer ${authToken}` },
    });
    expect(response.status()).toBe(400);
  });

  test('TC-PWD-009 should return 400 when new password equals old', { tag: '@P2' }, async () => {
    const response = await context.put('/api/auth/password', {
      data: {"oldPassword":"Abc123456","newPassword":"Abc123456"},
      headers: { Authorization: `Bearer ${authToken}` },
    });
    expect(response.status()).toBe(400);
  });
});
