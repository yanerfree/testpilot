import { test, expect } from '@playwright/test';
import { env } from '../env.config';

test.describe('登录页面', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(env.e2e.baseUrl + '/login');
  });

  test('TC-LOGIN-001 should login successfully with valid credentials', { tag: '@P0' }, async ({ page }) => {
    await page.getByLabel('邮箱').fill('test@example.com');
    await page.getByLabel('密码').fill('Abc123456');
    await page.getByRole('button', { name: '登录' }).click();

    await expect(page).toHaveURL('/dashboard');
  });

  test('TC-LOGIN-002 验证邮箱为空时显示校验提示', { tag: '@P1' }, async ({ page }) => {
    await page.getByLabel('密码').fill('Abc123456');
    await page.getByRole('button', { name: '登录' }).click();

    await expect(page.getByText('请输入邮箱')).toBeVisible();
  });

  test('TC-LOGIN-003 验证密码为空时显示校验提示', { tag: '@P1' }, async ({ page }) => {
    await page.getByLabel('邮箱').fill('test@example.com');
    await page.getByRole('button', { name: '登录' }).click();

    await expect(page.getByText('请输入密码')).toBeVisible();
  });

  test('TC-LOGIN-004 验证邮箱格式不正确显示校验提示', { tag: '@P2' }, async ({ page }) => {
    await page.getByLabel('邮箱').fill('not-an-email');
    await page.getByLabel('密码').fill('Abc123456');
    await page.getByRole('button', { name: '登录' }).click();

    await expect(page.getByText('邮箱格式不正确')).toBeVisible();
  });

  test('TC-LOGIN-005 验证密码错误显示错误提示', { tag: '@P1' }, async ({ page }) => {
    await page.getByLabel('邮箱').fill('test@example.com');
    await page.getByLabel('密码').fill('WrongPass123');
    await page.getByRole('button', { name: '登录' }).click();

    await expect(page.getByText('邮箱或密码错误')).toBeVisible();
    await expect(page).toHaveURL('/login');
  });

  test('TC-LOGIN-006 验证连续输错密码5次显示锁定提示', { tag: '@P2' }, async ({ page }) => {
    await page.getByLabel('邮箱').fill('test@example.com');
    await page.getByLabel('密码').fill('Wrong1');
    await page.getByRole('button', { name: '登录' }).click();
    for (let i = 0; i < 5; i++) {
      await page.getByLabel('密码').fill('Wrong1');
      await page.getByRole('button', { name: '登录' }).click();
    }

    await expect(page.getByText('账号已锁定')).toBeVisible();
  });

  test('TC-LOGIN-007 验证点击忘记密码跳转到重置密码页', { tag: '@P1' }, async ({ page }) => {
    await page.getByRole('link', { name: '忘记密码？' }).click();

  });

  test('TC-LOGIN-008 验证点击注册链接跳转到注册页', { tag: '@P1' }, async ({ page }) => {
    await page.getByRole('link', { name: '没有账号？去注册' }).click();

    await expect(page).toHaveURL('/register');
  });

  test('TC-LOGIN-009 验证勾选记住我后自动登录', { tag: '@P2' }, async ({ page }) => {
    await page.getByLabel('邮箱').fill('test@example.com');
    await page.getByLabel('密码').fill('Abc123456');
    await page.getByLabel('记住我').check();
    await page.getByRole('button', { name: '登录' }).click();

    await expect(page).toHaveURL('/dashboard');
    await expect(page).toHaveURL('/dashboard');
  });
});
