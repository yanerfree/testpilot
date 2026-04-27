export type TestMode = 'api' | 'e2e';

export interface LLMMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface LLMRequest {
  systemPrompt: string;
  messages: LLMMessage[];
  maxTokens?: number;
  temperature?: number;
}

export interface LLMResponse {
  content: string;
  usage?: {
    inputTokens: number;
    outputTokens: number;
  };
  model: string;
  durationMs: number;
}

export interface LLMProvider {
  generate(request: LLMRequest): Promise<LLMResponse>;
}
