import Anthropic from '@anthropic-ai/sdk';
import type { LLMProvider, LLMRequest, LLMResponse } from './types.js';

export interface ClaudeConfig {
  apiKey: string;
  model: string;
  baseUrl?: string;
}

export class ClaudeProvider implements LLMProvider {
  private client: Anthropic;
  private model: string;

  constructor(config: ClaudeConfig) {
    this.model = config.model;
    this.client = new Anthropic({
      apiKey: config.apiKey,
      ...(config.baseUrl ? { baseURL: config.baseUrl } : {}),
    });
  }

  async generate(request: LLMRequest): Promise<LLMResponse> {
    const start = Date.now();
    const response = await this.client.messages.create({
      model: this.model,
      max_tokens: request.maxTokens ?? 8192,
      temperature: request.temperature ?? 0.2,
      system: request.systemPrompt,
      messages: request.messages.map((m) => ({
        role: m.role,
        content: m.content,
      })),
    });

    const textBlock = response.content.find((b) => b.type === 'text');
    return {
      content: textBlock?.text ?? '',
      usage: {
        inputTokens: response.usage.input_tokens,
        outputTokens: response.usage.output_tokens,
      },
      model: response.model,
      durationMs: Date.now() - start,
    };
  }
}
