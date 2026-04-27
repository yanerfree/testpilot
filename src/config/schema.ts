import { z } from 'zod/v4';

const llmSchema = z.object({
  provider: z.enum(['claude', 'deepseek', 'openai-compatible']).default('claude'),
  apiKey: z.string().optional(),
  model: z.string().default('claude-sonnet-4-20250514'),
  maxTokens: z.number().default(8192),
  temperature: z.number().min(0).max(1).default(0.2),
  baseUrl: z.string().url().optional(),
});

const outputSchema = z.object({
  dir: z.string().default('./tests/generated'),
  overwrite: z.boolean().default(false),
});

export const configSchema = z.object({
  executor: z.enum(['self', 'llm']).default('self'),
  llm: llmSchema.default({
    provider: 'claude',
    model: 'claude-sonnet-4-20250514',
    maxTokens: 8192,
    temperature: 0.2,
  }),
  output: outputSchema.default({
    dir: './tests/generated',
    overwrite: false,
  }),
});

export type TestPilotConfig = z.infer<typeof configSchema>;
