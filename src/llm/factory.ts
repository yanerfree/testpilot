import type { LLMProvider } from './types.js';
import { ClaudeProvider } from './claude.js';
import { OpenAICompatibleProvider } from './openai-compatible.js';
import { ConfigError } from '../errors.js';
import type { TestPilotConfig } from '../config/schema.js';

const DEEPSEEK_BASE_URL = 'https://api.deepseek.com';
const DEEPSEEK_DEFAULT_MODEL = 'deepseek-chat';

export function createLLMProvider(config: TestPilotConfig, apiKey: string): LLMProvider {
  switch (config.llm.provider) {
    case 'claude':
      return new ClaudeProvider({
        apiKey,
        model: config.llm.model,
        baseUrl: config.llm.baseUrl,
      });
    case 'deepseek':
      return new OpenAICompatibleProvider({
        apiKey,
        model: config.llm.model === 'claude-sonnet-4-20250514' ? DEEPSEEK_DEFAULT_MODEL : config.llm.model,
        baseUrl: config.llm.baseUrl ?? DEEPSEEK_BASE_URL,
      });
    case 'openai-compatible':
      if (!config.llm.baseUrl) {
        throw new ConfigError('openai-compatible provider requires llm.baseUrl to be set.');
      }
      return new OpenAICompatibleProvider({
        apiKey,
        model: config.llm.model,
        baseUrl: config.llm.baseUrl,
      });
    default:
      throw new ConfigError(`Unknown LLM provider: ${config.llm.provider}`);
  }
}
