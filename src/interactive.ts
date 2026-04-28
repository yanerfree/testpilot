import { input, select, confirm } from '@inquirer/prompts';
import fs from 'node:fs/promises';
import path from 'node:path';
import { detectFormat, type InputFormat } from './parsers/detect.js';
import type { TestMode } from './llm/types.js';

export interface GenerateAnswers {
  inputPath: string;
  mode: TestMode;
  format: InputFormat;
  outdir: string;
}

export interface ScriptAnswers {
  casesPath: string;
  mode: TestMode;
  outdir: string;
}

export async function askGenerateOptions(): Promise<GenerateAnswers> {
  const inputPath = await input({
    message: '请输入需求文档路径:',
    validate: async (val: string) => {
      if (!val.trim()) return '路径不能为空';
      try {
        await fs.access(val.trim());
        return true;
      } catch {
        return `文件不存在: ${val}`;
      }
    },
  });

  const content = await fs.readFile(inputPath.trim(), 'utf-8');
  const detectedFormat = detectFormat(inputPath.trim(), content);

  console.log(`  检测到文件格式: ${detectedFormat}`);

  const mode = await select<TestMode>({
    message: '测试模式:',
    choices: [
      { name: 'API 接口测试', value: 'api' },
      { name: 'E2E 页面测试', value: 'e2e' },
    ],
  });

  const outdir = await input({
    message: '输出目录:',
    default: './tests/generated',
  });

  return {
    inputPath: inputPath.trim(),
    mode,
    format: detectedFormat,
    outdir: outdir.trim(),
  };
}

export async function askScriptOptions(): Promise<ScriptAnswers> {
  const casesPath = await input({
    message: '请输入测试用例文件路径:',
    validate: async (val: string) => {
      if (!val.trim()) return '路径不能为空';
      try {
        await fs.access(val.trim());
        return true;
      } catch {
        return `文件不存在: ${val}`;
      }
    },
  });

  const mode = await select<TestMode>({
    message: '测试模式:',
    choices: [
      { name: 'API 接口测试', value: 'api' },
      { name: 'E2E 页面测试', value: 'e2e' },
    ],
  });

  const outdir = await input({
    message: '输出目录:',
    default: './tests/specs',
  });

  return {
    casesPath: casesPath.trim(),
    mode,
    outdir: outdir.trim(),
  };
}

export async function confirmProceed(message: string): Promise<boolean> {
  return confirm({ message, default: true });
}
