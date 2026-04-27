import fs from 'node:fs/promises';
import path from 'node:path';
import { OutputError } from '../errors.js';

export async function writeTestFile(code: string, outputPath: string, overwrite: boolean): Promise<void> {
  const dir = path.dirname(outputPath);

  try {
    await fs.mkdir(dir, { recursive: true });
  } catch (err) {
    throw new OutputError(`Failed to create output directory: ${dir}`, err as Error);
  }

  if (!overwrite) {
    try {
      await fs.access(outputPath);
      throw new OutputError(
        `Output file already exists: ${outputPath}\n  → Use --force to overwrite.`,
      );
    } catch (err) {
      if (err instanceof OutputError) throw err;
      // File doesn't exist — good, we can write
    }
  }

  try {
    await fs.writeFile(outputPath, code, 'utf-8');
  } catch (err) {
    throw new OutputError(`Failed to write file: ${outputPath}`, err as Error);
  }
}
