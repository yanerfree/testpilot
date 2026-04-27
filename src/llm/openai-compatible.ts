import OpenAI from 'openai';
import type { LLMProvider, LLMRequest, LLMResponse } from './types.js';

export interface OpenAICompatibleConfig {
  apiKey: string;
  model: string;
  baseUrl: string;
}

export class OpenAICompatibleProvider implements LLMProvider {
  private client: OpenAI;
  private model: string;

  constructor(config: OpenAICompatibleConfig) {
    this.model = config.model;
    this.client = new OpenAI({
      apiKey: config.apiKey,
      baseURL: config.baseUrl,
    });
  }

  async generate(request: LLMRequest): Promise<LLMResponse> {
    const start = Date.now();
    const response = await this.client.chat.completions.create({
      model: this.model,
      max_tokens: request.maxTokens ?? 8192,
      temperature: request.temperature ?? 0.2,
      messages: [
        { role: 'system', content: request.systemPrompt },
        ...request.messages.map((m) => ({
          role: m.role as 'user' | 'assistant',
          content: m.content,
        })),
      ],
    });

    const choice = response.choices[0];
    return {
      content: choice?.message?.content ?? '',
      usage: response.usage ? {
        inputTokens: response.usage.prompt_tokens ?? 0,
        outputTokens: response.usage.completion_tokens ?? 0,
      } : undefined,
      model: response.model ?? this.model,
      durationMs: Date.now() - start,
    };
  }
}
