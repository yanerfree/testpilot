import path from 'node:path';

export type InputFormat = 'markdown' | 'openapi' | 'text';

export function detectFormat(filePath: string, content: string): InputFormat {
  const ext = path.extname(filePath).toLowerCase();

  if (ext === '.md' || ext === '.markdown') return 'markdown';

  if (ext === '.yaml' || ext === '.yml') {
    if (content.includes('openapi:') || content.includes('swagger:')) return 'openapi';
    return 'text';
  }

  if (ext === '.json') {
    try {
      const parsed = JSON.parse(content);
      if (parsed.openapi || parsed.swagger) return 'openapi';
    } catch {
      // not valid JSON
    }
    return 'text';
  }

  return 'text';
}
