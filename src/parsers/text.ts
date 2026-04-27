import type { ParsedInput } from './types.js';

export function parseText(content: string): ParsedInput {
  return {
    source: 'text',
    rawText: content.trim(),
    endpoints: [],
    pages: [],
  };
}
