import { Lexer, type Token, type Tokens } from 'marked';
import type { ParsedInput, Endpoint, PageFlow } from './types.js';

const HTTP_METHOD_PATTERN = /^(GET|POST|PUT|PATCH|DELETE)\s+(\S+)/i;
const PAGE_PATTERN = /页面|page|screen|视图|view/i;

export function parseMarkdown(content: string, filePath?: string): ParsedInput {
  const tokens = new Lexer().lex(content);

  let title: string | undefined;
  let description: string | undefined;
  const endpoints: Endpoint[] = [];
  const pages: PageFlow[] = [];

  let currentEndpoint: Endpoint | null = null;
  let currentPage: PageFlow | null = null;
  let firstHeading = true;

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];

    if (token.type === 'heading') {
      const heading = token as Tokens.Heading;

      if (firstHeading && heading.depth <= 2) {
        title = heading.text;
        firstHeading = false;

        const next = tokens[i + 1];
        if (next?.type === 'paragraph') {
          description = (next as Tokens.Paragraph).text;
        }
        continue;
      }

      flushCurrent();

      const methodMatch = heading.text.match(HTTP_METHOD_PATTERN);
      if (methodMatch) {
        currentEndpoint = {
          method: methodMatch[1].toUpperCase(),
          path: methodMatch[2],
          summary: '',
          responses: [],
        };
        continue;
      }

      if (PAGE_PATTERN.test(heading.text)) {
        currentPage = {
          name: heading.text,
          elements: [],
          actions: [],
          assertions: [],
        };
        continue;
      }

      // 通用 heading — 可能是 endpoint 描述或 page 描述
      // 尝试从后续内容推断
      currentEndpoint = null;
      currentPage = null;
    }

    if (token.type === 'paragraph' && currentEndpoint) {
      const para = token as Tokens.Paragraph;
      const methodMatch = para.text.match(HTTP_METHOD_PATTERN);
      if (methodMatch && !currentEndpoint.path) {
        currentEndpoint.method = methodMatch[1].toUpperCase();
        currentEndpoint.path = methodMatch[2];
      } else {
        currentEndpoint.summary = (currentEndpoint.summary ? currentEndpoint.summary + ' ' : '') + para.text;
      }
    }

    if (token.type === 'paragraph' && currentPage) {
      const para = token as Tokens.Paragraph;
      const urlMatch = para.text.match(/(?:URL|路径|地址|url)[：:\s]+(\S+)/i);
      if (urlMatch) {
        currentPage.url = urlMatch[1];
      }
    }

    if (token.type === 'list' && currentEndpoint) {
      const list = token as Tokens.List;
      for (const item of list.items) {
        const text = item.text.trim();
        if (/^\d{3}\b/.test(text)) {
          const status = parseInt(text.substring(0, 3), 10);
          currentEndpoint.responses = currentEndpoint.responses ?? [];
          currentEndpoint.responses.push({ status, description: text.substring(3).trim() });
        }
      }
    }

    if (token.type === 'list' && currentPage) {
      const list = token as Tokens.List;
      for (const item of list.items) {
        const text = item.text.trim();
        if (/操作|action|click|fill|输入|点击|选择|提交/i.test(text)) {
          currentPage.actions!.push(text);
        } else if (/预期|expect|should|断言|验证|显示|跳转/i.test(text)) {
          currentPage.assertions!.push(text);
        } else if (/元素|element|按钮|输入框|链接|button|input|link/i.test(text)) {
          currentPage.elements!.push({ name: text, type: 'unknown' });
        } else {
          currentPage.actions!.push(text);
        }
      }
    }

    if (token.type === 'code') {
      const code = token as Tokens.Code;
      if (code.lang === 'json' && currentEndpoint) {
        try {
          const parsed = JSON.parse(code.text);
          if (!currentEndpoint.requestBody) {
            currentEndpoint.requestBody = parsed;
          }
        } catch {
          // ignore invalid JSON
        }
      }
    }
  }

  flushCurrent();

  return {
    source: 'markdown',
    title,
    description,
    endpoints,
    pages,
    rawText: content,
  };

  function flushCurrent() {
    if (currentEndpoint?.path) {
      endpoints.push(currentEndpoint);
    }
    if (currentPage) {
      pages.push(currentPage);
    }
    currentEndpoint = null;
    currentPage = null;
  }
}
