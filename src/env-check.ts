import fs from 'node:fs/promises';
import path from 'node:path';
import chalk from 'chalk';
import { input } from '@inquirer/prompts';

export interface EnvCheckResult {
  valid: boolean;
  missing: string[];
  warnings: string[];
}

export async function checkEnvConfig(envPath: string): Promise<EnvCheckResult> {
  const missing: string[] = [];
  const warnings: string[] = [];

  try {
    await fs.access(envPath);
  } catch {
    missing.push(`环境配置文件不存在: ${envPath}`);
    return { valid: false, missing, warnings };
  }

  const content = await fs.readFile(envPath, 'utf-8');

  if (!content.includes('baseUrl')) {
    missing.push('api.baseUrl 未配置');
  }

  if (!content.includes('testUser')) {
    missing.push('testUser（测试账号）未配置');
  }

  if (/username.*['"]admin['"]/.test(content) || /TEST_USER_NAME.*admin/.test(content)) {
    warnings.push('检测到使用 admin 账号进行测试，建议使用专用测试账号，避免影响管理员数据');
  }

  if (content.includes("'http://localhost") || content.includes('"http://localhost')) {
    warnings.push('baseUrl 使用 localhost，请确认被测服务是否在本机运行');
  }

  return {
    valid: missing.length === 0,
    missing,
    warnings,
  };
}

export function reportEnvCheck(result: EnvCheckResult): void {
  if (result.missing.length > 0) {
    console.log(chalk.red('\n环境配置缺失:'));
    for (const m of result.missing) {
      console.log(chalk.red(`  ✗ ${m}`));
    }
  }

  if (result.warnings.length > 0) {
    console.log(chalk.yellow('\n环境配置警告:'));
    for (const w of result.warnings) {
      console.log(chalk.yellow(`  ⚠ ${w}`));
    }
  }

  if (result.valid && result.warnings.length === 0) {
    console.log(chalk.green('  ✓ 环境配置检查通过'));
  }
}

export async function ensureEnvConfig(envPath: string): Promise<boolean> {
  const result = await checkEnvConfig(envPath);
  reportEnvCheck(result);

  if (!result.valid) {
    console.log(chalk.dim('\n请先配置 tests/env.config.ts，或提供以下信息:'));

    const baseUrl = await input({ message: '被测系统 URL:' });
    const username = await input({ message: '测试账号用户名:' });
    const password = await input({ message: '测试账号密码:' });

    if (username.toLowerCase() === 'admin') {
      console.log(chalk.yellow('\n⚠ 建议不要使用 admin 账号进行测试，可能会影响管理员数据。'));
      const proceed = await input({ message: '是否继续使用 admin？(y/N)' });
      if (proceed.toLowerCase() !== 'y') {
        const newUsername = await input({ message: '请输入其他测试账号:' });
        return await writeEnvConfig(envPath, baseUrl.trim(), newUsername.trim(), password.trim());
      }
    }

    return await writeEnvConfig(envPath, baseUrl.trim(), username.trim(), password.trim());
  }

  if (result.warnings.length > 0) {
    for (const w of result.warnings) {
      if (w.includes('admin')) {
        const proceed = await input({ message: '是否继续使用 admin 账号？(y/N)' });
        if (proceed.toLowerCase() !== 'y') {
          const username = await input({ message: '请输入其他测试账号用户名:' });
          const password = await input({ message: '密码:' });
          const content = await fs.readFile(envPath, 'utf-8');
          const baseUrlMatch = content.match(/baseUrl.*?'(http[^']+)'/);
          const baseUrl = baseUrlMatch?.[1] ?? 'http://localhost:8000';
          return await writeEnvConfig(envPath, baseUrl, username.trim(), password.trim());
        }
      }
    }
  }

  return true;
}

async function writeEnvConfig(envPath: string, baseUrl: string, username: string, password: string): Promise<boolean> {
  const dir = path.dirname(envPath);
  await fs.mkdir(dir, { recursive: true });

  const content = `export const env = {
  api: {
    baseUrl: process.env.TEST_API_URL ?? '${baseUrl}',
  },
  e2e: {
    baseUrl: process.env.TEST_APP_URL ?? '${baseUrl}',
  },
  db: {
    host: process.env.TEST_DB_HOST ?? 'localhost',
    port: Number(process.env.TEST_DB_PORT ?? 5432),
    name: process.env.TEST_DB_NAME ?? 'testdb',
    user: process.env.TEST_DB_USER ?? 'postgres',
    password: process.env.TEST_DB_PASSWORD ?? '',
  },
  testUser: {
    username: process.env.TEST_USER_NAME ?? '${username}',
    password: process.env.TEST_USER_PASSWORD ?? '${password}',
  },
};
`;

  await fs.writeFile(envPath, content, 'utf-8');
  console.log(chalk.green(`\n✓ 已更新 ${envPath}`));
  return true;
}
