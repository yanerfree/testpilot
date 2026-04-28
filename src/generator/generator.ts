import fs from 'node:fs/promises';
import path from 'node:path';
import type { TestPilotConfig } from '../config/schema.js';
import type { TestMode, LLMProvider } from '../llm/types.js';
import type { ParsedInput } from '../parsers/types.js';
import { detectFormat } from '../parsers/detect.js';
import { parseMarkdown } from '../parsers/markdown.js';
import { parseText } from '../parsers/text.js';
import { API_SYSTEM_PROMPT } from '../prompts/system-api.js';
import { E2E_SYSTEM_PROMPT } from '../prompts/system-e2e.js';
import { buildUserMessage } from '../prompts/templates.js';
import { getFewShotExamples } from '../prompts/examples.js';
import { extractTestCases } from './postprocess.js';
import { writeTestFile } from '../output/writer.js';
import { parseOpenAPI } from '../parsers/openapi.js';
import { ParseError } from '../errors.js';
import type { InputFormat } from '../parsers/detect.js';

export interface GenerateOptions {
  inputPath: string;
  mode: TestMode;
  config: TestPilotConfig;
  provider: LLMProvider;
  format?: InputFormat;
  dryRun?: boolean;
  verbose?: boolean;
}

export interface GenerateResult {
  content: string;
  outputPath?: string;
  usage?: { inputTokens: number; outputTokens: number };
  model: string;
  durationMs: number;
}

export async function generateTests(options: GenerateOptions): Promise<GenerateResult> {
  const { inputPath, mode, config, provider, dryRun, verbose } = options;

  let rawContent: string;
  try {
    rawContent = await fs.readFile(inputPath, 'utf-8');
  } catch (err) {
    throw new ParseError(`Failed to read input file: ${inputPath}`, err as Error);
  }

  const format = options.format ?? detectFormat(inputPath, rawContent);
  let parsed: ParsedInput;

  switch (format) {
    case 'markdown':
      parsed = parseMarkdown(rawContent, inputPath);
      break;
    case 'openapi':
      parsed = await parseOpenAPI(rawContent, inputPath);
      break;
    case 'text':
      parsed = parseText(rawContent);
      break;
    default:
      parsed = parseText(rawContent);
  }

  const systemPrompt = mode === 'api' ? API_SYSTEM_PROMPT : E2E_SYSTEM_PROMPT;
  const userMessage = buildUserMessage(parsed, mode);
  const examples = getFewShotExamples(mode);

  const response = await provider.generate({
    systemPrompt,
    messages: [
      ...examples,
      { role: 'user', content: userMessage },
    ],
    maxTokens: config.llm.maxTokens,
    temperature: config.llm.temperature,
  });

  if (verbose) {
    console.error(`  Model: ${response.model}`);
    console.error(`  Tokens: ${response.usage?.inputTokens ?? '?'} in / ${response.usage?.outputTokens ?? '?'} out`);
    console.error(`  Duration: ${response.durationMs}ms`);
  }

  const testCases = extractTestCases(response.content);

  let outputPath: string | undefined;
  if (!dryRun) {
    const inputBasename = path.basename(inputPath, path.extname(inputPath));
    const suffix = mode === 'e2e' ? '.e2e-cases.md' : '.api-cases.md';
    outputPath = path.resolve(config.output.dir, inputBasename + suffix);
    await writeTestFile(testCases, outputPath, config.output.overwrite);
  }

  return {
    content: testCases,
    outputPath,
    usage: response.usage,
    model: response.model,
    durationMs: response.durationMs,
  };
}
