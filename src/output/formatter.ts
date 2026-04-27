import prettier from 'prettier';

export async function formatCode(code: string): Promise<string> {
  try {
    return await prettier.format(code, {
      parser: 'typescript',
      singleQuote: true,
      trailingComma: 'all',
      printWidth: 100,
      tabWidth: 2,
      semi: true,
    });
  } catch {
    // If prettier fails (malformed code), return unformatted
    return code;
  }
}
