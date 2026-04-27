import type { ParsedInput } from '../parsers/types.js';
import type { TestMode } from '../llm/types.js';

export function buildUserMessage(input: ParsedInput, mode: TestMode): string {
  if (mode === 'api') {
    return buildApiMessage(input);
  }
  return buildE2eMessage(input);
}

function buildApiMessage(input: ParsedInput): string {
  const parts: string[] = [];

  parts.push(`请根据以下 API 接口需求，生成完整的测试用例。`);
  parts.push('');

  if (input.endpoints.length > 0) {
    parts.push('## 接口列表\n');
    for (const ep of input.endpoints) {
      parts.push(`### ${ep.method} ${ep.path}`);
      if (ep.summary) parts.push(ep.summary);
      if (ep.requestBody) {
        parts.push(`\n请求体示例:\n\`\`\`json\n${JSON.stringify(ep.requestBody, null, 2)}\n\`\`\``);
      }
      if (ep.responses && ep.responses.length > 0) {
        parts.push('\n响应码:');
        for (const r of ep.responses) {
          parts.push(`- ${r.status}: ${r.description ?? ''}`);
        }
      }
      parts.push('');
    }
  }

  if (input.rawText) {
    parts.push('## 完整需求文档\n');
    parts.push(input.rawText);
  }

  parts.push('\n请为上述每个接口生成完整的测试用例，覆盖正常流程、参数校验、业务规则和边界条件。');

  return parts.join('\n');
}

function buildE2eMessage(input: ParsedInput): string {
  const parts: string[] = [];

  parts.push(`请根据以下页面需求，生成完整的 E2E 测试用例。`);
  parts.push('');

  if (input.pages.length > 0) {
    parts.push('## 页面列表\n');
    for (const page of input.pages) {
      parts.push(`### ${page.name}`);
      if (page.url) parts.push(`URL: ${page.url}`);
      if (page.elements && page.elements.length > 0) {
        parts.push('\n页面元素:');
        for (const el of page.elements) {
          parts.push(`- ${el.name} (${el.type}${el.testId ? `, data-testid="${el.testId}"` : ''})`);
        }
      }
      if (page.actions && page.actions.length > 0) {
        parts.push('\n用户操作:');
        for (const a of page.actions) parts.push(`- ${a}`);
      }
      if (page.assertions && page.assertions.length > 0) {
        parts.push('\n预期结果:');
        for (const a of page.assertions) parts.push(`- ${a}`);
      }
      parts.push('');
    }
  }

  if (input.rawText) {
    parts.push('## 完整需求文档\n');
    parts.push(input.rawText);
  }

  parts.push('\n请为上述每个页面和流程生成完整的测试用例，覆盖正常流程、表单校验、交互反馈和边界场景。');

  return parts.join('\n');
}
