import { LLMError } from '../errors.js';

export function extractTestCases(response: string): string {
  // Look for markdown table (starts with | header |)
  const lines = response.split('\n');
  const tableLines: string[] = [];
  let inTable = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      inTable = true;
      tableLines.push(trimmed);
    } else if (inTable && trimmed === '') {
      // blank line between tables — keep going
      continue;
    } else if (inTable) {
      // non-table line after table started — stop or continue looking
      inTable = false;
    }
  }

  if (tableLines.length >= 3) {
    return tableLines.join('\n');
  }

  // Fallback: return the full response if it looks like it has test case content
  if (response.includes('TC-') && response.includes('|')) {
    return response.trim();
  }

  throw new LLMError(
    'Failed to extract test cases from LLM response. The response did not contain a valid markdown table.',
  );
}
