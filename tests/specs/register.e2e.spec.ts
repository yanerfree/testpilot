import { test, expect } from '@playwright/test';
import { env } from '../env.config';

test.describe('注册页面', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(env.e2e.baseUrl + '/register');
  });

  test('TC-REG-001 should register successfully with valid data', { tag: '@P0' }, async ({ page }) => {
    await page.getByLabel('用户名').fill('newuser');
    await page.getByLabel('邮箱').fill('newuser@example.com');
    await page.getByLabel('密码').fill('Abc123456');
    await page.getByLabel('确认密码').fill('Abc123456');
    await page.getByRole('button', { name: '注册' }).click();

    await expect(page).toHaveURL('/login');
    await expect(page.getByText('注册成功')).toBeVisible();
  });

  test('TC-REG-002 验证用户名少于2个字符显示校验提示', { tag: '@P1' }, async ({ page }) => {
    await page.getByLabel('用户名').fill('a');
    await page.getByLabel('邮箱').fill('test@example.com');
    await page.getByLabel('密码').fill('Abc123456');
    await page.getByLabel('确认密码').fill('Abc123456');
    await page.getByRole('button', { name: '注册' }).click();

    await expect(page.getByText('用户名至少2个字符')).toBeVisible();
  });

  test('TC-REG-003 验证邮箱已被注册显示提示', { tag: '@P1' }, async ({ page }) => {
    await page.getByLabel('用户名').fill('another');
    await page.getByLabel('邮箱').fill('test@example.com');
    await page.getByLabel('密码').fill('Abc123456');
    await page.getByLabel('确认密码').fill('Abc123456');
    await page.getByRole('button', { name: '注册' }).click();

    await expect(page.getByText('该邮箱已被注册')).toBeVisible();
  });

  test('TC-REG-004 验证两次密码不一致显示校验提示', { tag: '@P1' }, async ({ page }) => {
    await page.getByLabel('用户名').fill('testuser');
    await page.getByLabel('邮箱').fill('test@example.com');
    await page.getByLabel('密码').fill('Abc123456');
    await page.getByLabel('确认密码').fill('Different789');
    await page.getByRole('button', { name: '注册' }).click();

    await expect(page.getByText('两次密码不一致')).toBeVisible();
  });

  test('TC-REG-005 验证密码少于8位显示校验提示', { tag: '@P1' }, async ({ page }) => {
    await page.getByLabel('用户名').fill('testuser');
    await page.getByLabel('邮箱').fill('test@example.com');
    await page.getByLabel('密码').fill('Ab1');
    await page.getByLabel('确认密码').fill('Ab1');
    await page.getByRole('button', { name: '注册' }).click();

    await expect(page.getByText('密码至少8位')).toBeVisible();
  });

  test('TC-REG-006 验证点击返回登录链接跳转到登录页', { tag: '@P1' }, async ({ page }) => {
    await page.getByRole('link', { name: '已有账号？去登录' }).click();

    await expect(page).toHaveURL('/login');
  });
});
