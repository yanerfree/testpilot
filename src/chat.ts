import { input } from '@inquirer/prompts';
import fs from 'node:fs/promises';
import path from 'node:path';
import chalk from 'chalk';
import ora from 'ora';
import { loadConfig } from './config/loader.js';
import { detectFormat } from './parsers/detect.js';
import { parseMarkdown } from './parsers/markdown.js';
import { parseText } from './parsers/text.js';
import { parseOpenAPI } from './parsers/openapi.js';
import { generateTestCasesLocally } from './generator/local-generator.js';
import { generateScripts } from './generator/script-generator.js';
import { writeTestFile } from './output/writer.js';
import type { TestMode } from './llm/types.js';

interface ParsedIntent {
  action: 'generate' | 'script' | 'help' | 'exit' | 'unknown';
  filePath?: string;
  mode?: TestMode;
  outdir?: string;
}

function parseIntent(text: string): ParsedIntent {
  const t = text.trim();

  if (/^(退出|exit|quit|q)$/i.test(t)) {
    return { action: 'exit' };
  }

  if (/^(帮助|help|h|\?)$/i.test(t)) {
    return { action: 'help' };
  }

  // Extract file path — anything that looks like a path
  const pathMatch = t.match(/([\w./_-]+\.(md|yaml|yml|json|txt))/);
  const filePath = pathMatch?.[1];

  // Detect mode
  let mode: TestMode | undefined;
  if (/e2e|页面|ui|前端|浏览器/i.test(t)) {
    mode = 'e2e';
  } else if (/api|接口|后端/i.test(t)) {
    mode = 'api';
  }

  // Detect action
  if (/生成.*脚本|脚本.*生成|转.*脚本|generate.*script|script/i.test(t)) {
    return { action: 'script', filePath, mode };
  }

  if (/生成.*用例|用例.*生成|测试用例|generate|生成/i.test(t)) {
    return { action: 'generate', filePath, mode };
  }

  // If a file is mentioned but no clear action, guess from file name
  if (filePath) {
    if (filePath.includes('-cases.md') || filePath.includes('cases')) {
      return { action: 'script', filePath, mode };
    }
    return { action: 'generate', filePath, mode };
  }

  return { action: 'unknown' };
}

async function resolveFilePath(filePath: string | undefined, hint: string): Promise<string | null> {
  if (filePath) {
    try {
      await fs.access(filePath);
      return filePath;
    } catch {
      console.log(chalk.red(`  文件不存在: ${filePath}`));
    }
  }

  const answer = await input({ message: hint });
  const trimmed = answer.trim();
  if (!trimmed) return null;

  try {
    await fs.access(trimmed);
    return trimmed;
  } catch {
    console.log(chalk.red(`  文件不存在: ${trimmed}`));
    return null;
  }
}

async function inferMode(filePath: string, mode?: TestMode): Promise<TestMode> {
  if (mode) return mode;
  if (/e2e|page|页面/i.test(filePath)) return 'e2e';
  return 'api';
}

async function handleGenerate(intent: ParsedIntent) {
  const filePath = await resolveFilePath(intent.filePath, '请输入需求文档路径:');
  if (!filePath) return;

  const content = await fs.readFile(filePath, 'utf-8');
  const format = detectFormat(filePath, content);
  const mode = await inferMode(filePath, intent.mode);

  console.log(chalk.dim(`  文件: ${filePath}`));
  console.log(chalk.dim(`  格式: ${format}`));
  console.log(chalk.dim(`  模式: ${mode === 'api' ? 'API 接口测试' : 'E2E 页面测试'}`));

  const spinner = ora({ text: `生成 ${mode} 测试用例...`, color: 'cyan' }).start();

  let parsed;
  switch (format) {
    case 'markdown': parsed = parseMarkdown(content, filePath); break;
    case 'openapi': parsed = await parseOpenAPI(content, filePath); break;
    default: parsed = parseText(content);
  }

  const testCases = generateTestCasesLocally(parsed, mode, '');

  const config = await loadConfig();
  const basename = path.basename(filePath, path.extname(filePath));
  const suffix = mode === 'e2e' ? '.e2e-cases.md' : '.api-cases.md';
  const outputPath = path.resolve(config.output.dir, basename + suffix);

  await writeTestFile(testCases, outputPath, true);
  spinner.succeed(`已生成测试用例 → ${outputPath}`);

  const lines = testCases.split('\n').filter(l => l.startsWith('| TC-'));
  console.log(chalk.dim(`  共 ${lines.length} 条用例`));
}

async function handleScript(intent: ParsedIntent) {
  const filePath = await resolveFilePath(intent.filePath, '请输入测试用例文件路径:');
  if (!filePath) return;

  const mode = await inferMode(filePath, intent.mode);

  console.log(chalk.dim(`  用例文件: ${filePath}`));
  console.log(chalk.dim(`  模式: ${mode === 'api' ? 'API 接口测试' : 'E2E 页面测试'}`));

  const spinner = ora({ text: `生成 ${mode} 测试脚本...`, color: 'cyan' }).start();

  const writtenFiles = await generateScripts({
    casesPath: filePath,
    mode,
    outdir: './tests/specs',
    overwrite: true,
  });

  spinner.succeed(`已生成 ${writtenFiles.length} 个脚本文件`);
  for (const f of writtenFiles) {
    console.log(chalk.green(`  → ${f}`));
  }
}

function showHelp() {
  console.log(`
${chalk.bold('TestPilot — 自然语言交互模式')}

直接用自然语言告诉我你要做什么，例如：

  ${chalk.cyan('根据 examples/api/login-api.md 生成 API 测试用例')}
  ${chalk.cyan('帮我生成 E2E 测试用例，文件是 examples/e2e/login-page.md')}
  ${chalk.cyan('把 tests/generated/login-api.api-cases.md 转成测试脚本')}
  ${chalk.cyan('生成用例')}          → 会问你要哪个文件
  ${chalk.cyan('生成脚本')}          → 会问你用例文件在哪

输入 ${chalk.yellow('exit')} 或 ${chalk.yellow('退出')} 结束。
`);
}

export async function startChat() {
  console.log(chalk.bold('\nTestPilot Agent'));
  console.log(chalk.dim('输入你的需求，或输入 help 查看帮助\n'));

  while (true) {
    const userInput = await input({ message: '>' });
    if (!userInput.trim()) continue;

    const intent = parseIntent(userInput);

    try {
      switch (intent.action) {
        case 'generate':
          await handleGenerate(intent);
          break;
        case 'script':
          await handleScript(intent);
          break;
        case 'help':
          showHelp();
          break;
        case 'exit':
          console.log(chalk.dim('再见！'));
          return;
        case 'unknown':
          console.log(chalk.yellow('没理解你的意思。输入 help 查看我能做什么。'));
          break;
      }
    } catch (err) {
      console.error(chalk.red(`错误: ${err instanceof Error ? err.message : String(err)}`));
    }

    console.log('');
  }
}
