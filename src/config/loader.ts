import { cosmiconfig } from 'cosmiconfig';
import { configSchema, type TestPilotConfig } from './schema.js';
import { ConfigError } from '../errors.js';

const explorer = cosmiconfig('testpilot');

export interface CLIFlags {
  mode?: 'api' | 'e2e';
  format?: 'markdown' | 'openapi' | 'text';
  outdir?: string;
  model?: string;
  apiKey?: string;
  executor?: 'self' | 'llm';
  dryRun?: boolean;
  verbose?: boolean;
  force?: boolean;
}

export async function loadConfig(flags: CLIFlags = {}): Promise<TestPilotConfig> {
  let fileConfig: Record<string, unknown> = {};

  try {
    const result = await explorer.search();
    if (result && !result.isEmpty) {
      fileConfig = result.config as Record<string, unknown>;
    }
  } catch (err) {
    throw new ConfigError(
      `Failed to load config file: ${err instanceof Error ? err.message : String(err)}`,
    );
  }

  if (flags.executor) {
    fileConfig.executor = flags.executor;
  }
  if (flags.outdir) {
    fileConfig.output = { ...(fileConfig.output as object ?? {}), dir: flags.outdir };
  }
  if (flags.force) {
    fileConfig.output = { ...(fileConfig.output as object ?? {}), overwrite: true };
  }
  if (flags.model) {
    fileConfig.llm = { ...(fileConfig.llm as object ?? {}), model: flags.model };
  }
  if (flags.apiKey) {
    fileConfig.llm = { ...(fileConfig.llm as object ?? {}), apiKey: flags.apiKey };
  }

  const parsed = configSchema.safeParse(fileConfig);
  if (!parsed.success) {
    throw new ConfigError(`Invalid configuration: ${parsed.error.message}`);
  }

  const config = parsed.data;

  if (!config.llm.apiKey) {
    config.llm.apiKey = process.env.ANTHROPIC_API_KEY;
  }

  return config;
}

export function resolveApiKey(config: TestPilotConfig): string {
  const key = config.llm.apiKey ?? process.env.ANTHROPIC_API_KEY;
  if (!key) {
    throw new ConfigError(
      'No API key found. Set ANTHROPIC_API_KEY env var, add llm.apiKey to .testpilotrc.json, or pass --api-key flag.',
    );
  }
  return key;
}
