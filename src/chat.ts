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
import { ensureEnvConfig, checkEnvConfig, reportEnvCheck } from './env-check.js';
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

  // Extract file path — absolute or relative path with extension
  const pathMatch = t.match(/(\/[\w./_-]+\.(md|yaml|yml|json|txt))|([\w./_-]+\.(md|yaml|yml|json|txt))/);
  const filePath = pathMatch?.[0];

  // Extract output directory — "输出到/输出文件/输出目录/output" followed by path
  const outdirMatch = t.match(/(?:输出[文件目录地址]*[：:\s]+|output[:\s]+)(\/[\w./_-]+|[\w./_-]+\/)/i);
  const outdir = outdirMatch?.[1]?.replace(/\/+$/, '');

  // Detect mode
  let mode: TestMode | undefined;
  if (/e2e|页面|ui|前端|浏览器/i.test(t)) {
    mode = 'e2e';
  } else if (/api|接口|后端|swagger/i.test(t)) {
    mode = 'api';
  }

  // Detect action
  if (/生成.*脚本|脚本.*生成|转.*脚本|generate.*script|script/i.test(t)) {
    return { action: 'script', filePath, mode, outdir };
  }

  if (/生成.*用例|用例.*生成|测试用例|generate|生成/i.test(t)) {
    return { action: 'generate', filePath, mode, outdir };
  }

  if (filePath) {
    if (filePath.includes('-cases.md') || filePath.includes('cases')) {
      return { action: 'script', filePath, mode, outdir };
    }
    return { action: 'generate', filePath, mode, outdir };
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

async function resolveOutdir(outdir: string | undefined, defaultDir: string): Promise<string> {
  if (outdir) return outdir;
  const answer = await input({ message: `输出目录 (默认 ${defaultDir}):`, default: defaultDir });
  return answer.trim() || defaultDir;
}

async function inferMode(filePath: string, mode?: TestMode): Promise<TestMode> {
  if (mode) return mode;
  if (/e2e|page|页面/i.test(filePath)) return 'e2e';
  if (/swagger|openapi/i.test(filePath)) return 'api';
  return 'api';
}

async function handleGenerate(intent: ParsedIntent) {
  const filePath = await resolveFilePath(intent.filePath, '请输入需求文档路径:');
  if (!filePath) return;

  const content = await fs.readFile(filePath, 'utf-8');
  const format = detectFormat(filePath, content);
  const mode = await inferMode(filePath, intent.mode);
  const outdir = await resolveOutdir(intent.outdir, './tests/generated');

  console.log(chalk.dim(`  文件: ${filePath}`));
  console.log(chalk.dim(`  格式: ${format}`));
  console.log(chalk.dim(`  模式: ${mode === 'api' ? 'API 接口测试' : 'E2E 页面测试'}`));
  console.log(chalk.dim(`  输出: ${outdir}`));

  const spinner = ora({ text: `生成 ${mode} 测试用例...`, color: 'cyan' }).start();

  let parsed;
  switch (format) {
    case 'markdown': parsed = parseMarkdown(content, filePath); break;
    case 'openapi': parsed = await parseOpenAPI(content, filePath); break;
    default: parsed = parseText(content);
  }

  const testCases = generateTestCasesLocally(parsed, mode, '');

  const basename = path.basename(filePath, path.extname(filePath));
  const suffix = mode === 'e2e' ? '.e2e-cases.md' : '.api-cases.md';
  const outputPath = path.resolve(outdir, basename + suffix);

  await fs.mkdir(outdir, { recursive: true });
  await writeTestFile(testCases, outputPath, true);
  spinner.succeed(`已生成测试用例 → ${outputPath}`);

  const lines = testCases.split('\n').filter(l => l.startsWith('| TC-'));
  console.log(chalk.dim(`  共 ${lines.length} 条用例`));
}

async function handleScript(intent: ParsedIntent) {
  const filePath = await resolveFilePath(intent.filePath, '请输入测试用例文件路径:');
  if (!filePath) return;

  const mode = await inferMode(filePath, intent.mode);
  const outdir = await resolveOutdir(intent.outdir, './tests/specs');

  // Check env config before generating scripts
  const envPath = path.resolve('tests/env.config.ts');
  console.log(chalk.dim('\n检查环境配置...'));
  const configOk = await ensureEnvConfig(envPath);
  if (!configOk) {
    console.log(chalk.red('环境配置未就绪，请先完善配置后再生成脚本。'));
    return;
  }

  console.log(chalk.dim(`  用例文件: ${filePath}`));
  console.log(chalk.dim(`  模式: ${mode === 'api' ? 'API 接口测试' : 'E2E 页面测试'}`));
  console.log(chalk.dim(`  输出: ${outdir}`));

  const spinner = ora({ text: `生成 ${mode} 测试脚本...`, color: 'cyan' }).start();

  const writtenFiles = await generateScripts({
    casesPath: filePath,
    mode,
    outdir,
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

  ${chalk.cyan('帮我生成测试用例')}
  ${chalk.cyan('swagger文件地址：/path/to/spec.yaml')}
  ${chalk.cyan('输出文件地址：/path/to/output/')}

  ${chalk.cyan('根据 examples/api/login-api.md 生成 API 测试用例')}
  ${chalk.cyan('帮我把 tests/generated/login-api.api-cases.md 转成测试脚本')}

可以一次性提供所有信息，也可以分步提供，Agent 会询问缺少的信息。

输入 ${chalk.yellow('exit')} 或 ${chalk.yellow('退出')} 结束。
`);
}

export async function startChat() {
  console.log(chalk.bold('\nTestPilot Agent'));
  console.log(chalk.dim('输入你的需求，或输入 help 查看帮助\n'));

  while (true) {
    let userInput = await input({ message: '>' });

    // Support multi-line input: if the first line doesn't contain a file path,
    // keep reading until we get an empty line
    if (userInput.trim() && !userInput.match(/\.(md|yaml|yml|json|txt)\b/) && !userInput.match(/\/([\w._-]+\/)+/)) {
      let fullInput = userInput;
      while (true) {
        const line = await input({ message: '' });
        if (!line.trim()) break;
        fullInput += '\n' + line;
      }
      userInput = fullInput;
    }

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
