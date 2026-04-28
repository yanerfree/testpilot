import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import fs from 'node:fs/promises';
import path from 'node:path';
import { loadConfig, resolveApiKey, type CLIFlags } from './config/loader.js';
import { createLLMProvider } from './llm/factory.js';
import { generateTests } from './generator/generator.js';
import { generateTestCasesLocally } from './generator/local-generator.js';
import { generateScripts } from './generator/script-generator.js';
import { detectFormat, type InputFormat } from './parsers/detect.js';
import { parseMarkdown } from './parsers/markdown.js';
import { parseText } from './parsers/text.js';
import { parseOpenAPI } from './parsers/openapi.js';
import { writeTestFile } from './output/writer.js';
import { askGenerateOptions, askScriptOptions } from './interactive.js';
import { startChat } from './chat.js';
import { TestPilotError, ConfigError, LLMError } from './errors.js';
import type { TestMode } from './llm/types.js';

const program = new Command();

program
  .name('testpilot')
  .description('AI-powered test case generation agent')
  .version('0.1.0');

program
  .command('generate')
  .description('Generate test cases from requirements docs, OpenAPI specs, or text')
  .argument('[input...]', 'Input file(s) — leave empty for interactive mode')
  .option('-m, --mode <type>', 'Test mode: api or e2e', 'api')
  .option('-f, --format <type>', 'Force input format: markdown, openapi, or text')
  .option('-o, --outdir <path>', 'Output directory', './tests/generated')
  .option('-e, --executor <type>', 'Executor: self or llm')
  .option('--model <model>', 'LLM model to use')
  .option('--api-key <key>', 'LLM API key')
  .option('--dry-run', 'Print generated test cases to stdout instead of writing files')
  .option('--verbose', 'Show debug output')
  .option('--force', 'Overwrite existing output files')
  .action(async (inputs: string[], opts) => {
    try {
      let inputFiles: string[];
      let mode: TestMode;
      let outdir: string;
      let format: InputFormat | undefined;

      if (inputs.length === 0) {
        const answers = await askGenerateOptions();
        inputFiles = [answers.inputPath];
        mode = answers.mode;
        outdir = answers.outdir;
        format = answers.format;
      } else {
        inputFiles = inputs;
        mode = opts.mode as TestMode;
        outdir = opts.outdir;
        format = opts.format as InputFormat | undefined;
      }

      const flags: CLIFlags = {
        mode,
        format,
        outdir,
        executor: opts.executor,
        model: opts.model,
        apiKey: opts.apiKey,
        dryRun: opts.dryRun,
        verbose: opts.verbose,
        force: opts.force,
      };

      const config = await loadConfig(flags);

      for (const inputPath of inputFiles) {
        const spinner = ora({
          text: `Generating ${mode} test cases from ${inputPath}...`,
          color: 'cyan',
        }).start();

        try {
          if (config.executor === 'self') {
            const content = await fs.readFile(inputPath, 'utf-8');
            const fmt = format ?? detectFormat(inputPath, content);
            let parsed;
            switch (fmt) {
              case 'markdown': parsed = parseMarkdown(content, inputPath); break;
              case 'openapi': parsed = await parseOpenAPI(content, inputPath); break;
              default: parsed = parseText(content);
            }

            const testCases = generateTestCasesLocally(parsed, mode, '');

            if (flags.dryRun) {
              spinner.succeed(`Generated ${mode} test cases from ${inputPath}`);
              console.log('\n' + testCases);
            } else {
              const basename = path.basename(inputPath, path.extname(inputPath));
              const suffix = mode === 'e2e' ? '.e2e-cases.md' : '.api-cases.md';
              const outputPath = path.resolve(outdir, basename + suffix);
              await writeTestFile(testCases, outputPath, config.output.overwrite);
              spinner.succeed(`Written to ${outputPath}`);
            }
          } else {
            const apiKey = resolveApiKey(config);
            const provider = createLLMProvider(config, apiKey);

            const result = await generateTests({
              inputPath,
              mode,
              config,
              provider,
              format,
              dryRun: flags.dryRun,
              verbose: flags.verbose,
            });

            spinner.succeed(
              flags.dryRun
                ? `Generated ${mode} test cases from ${inputPath}`
                : `Written to ${result.outputPath}`,
            );

            if (flags.dryRun) {
              console.log('\n' + result.content);
            }

            if (flags.verbose) {
              console.error(chalk.dim(`  Model: ${result.model}`));
              console.error(chalk.dim(`  Tokens: ${result.usage?.inputTokens ?? '?'} in / ${result.usage?.outputTokens ?? '?'} out`));
              console.error(chalk.dim(`  Duration: ${result.durationMs}ms`));
            }
          }
        } catch (err) {
          spinner.fail(`Failed to generate test cases from ${inputPath}`);
          throw err;
        }
      }
    } catch (err) {
      handleError(err);
    }
  });

program
  .command('script')
  .description('Generate Playwright test scripts from test case files')
  .argument('[cases...]', 'Test case file(s) — leave empty for interactive mode')
  .option('-m, --mode <type>', 'Test mode: api or e2e', 'api')
  .option('-o, --outdir <path>', 'Output directory', './tests/specs')
  .option('--force', 'Overwrite existing output files')
  .action(async (cases: string[], opts) => {
    try {
      let caseFiles: string[];
      let mode: TestMode;
      let outdir: string;

      if (cases.length === 0) {
        const answers = await askScriptOptions();
        caseFiles = [answers.casesPath];
        mode = answers.mode;
        outdir = answers.outdir;
      } else {
        caseFiles = cases;
        mode = opts.mode as TestMode;
        outdir = opts.outdir;
      }

      for (const casesPath of caseFiles) {
        const spinner = ora({
          text: `Generating ${mode} scripts from ${casesPath}...`,
          color: 'cyan',
        }).start();

        try {
          const writtenFiles = await generateScripts({
            casesPath,
            mode,
            outdir,
            overwrite: opts.force ?? false,
          });

          spinner.succeed(`Generated ${writtenFiles.length} script file(s) from ${casesPath}`);
          for (const f of writtenFiles) {
            console.log(chalk.green(`  → ${f}`));
          }
        } catch (err) {
          spinner.fail(`Failed to generate scripts from ${casesPath}`);
          throw err;
        }
      }
    } catch (err) {
      handleError(err);
    }
  });

program
  .command('init')
  .description('Create a .testpilotrc.json config file')
  .action(async () => {
    const configPath = path.resolve('.testpilotrc.json');
    try {
      await fs.access(configPath);
      console.log(chalk.yellow('.testpilotrc.json already exists.'));
      return;
    } catch {
      // file doesn't exist — create it
    }

    const defaultConfig = {
      executor: 'self',
      llm: {
        provider: 'deepseek',
        model: 'deepseek-chat',
        apiKey: '',
        maxTokens: 8192,
        temperature: 0.2,
      },
      output: {
        dir: './tests/generated',
        overwrite: false,
      },
    };

    await fs.writeFile(configPath, JSON.stringify(defaultConfig, null, 2) + '\n', 'utf-8');
    console.log(chalk.green(`Created ${configPath}`));
    console.log(chalk.dim('Edit the file to set your LLM API key and preferences.'));
  });

program
  .command('chat', { isDefault: true })
  .description('Interactive natural language mode')
  .action(async () => {
    await startChat();
  });

function handleError(err: unknown): never {
  if (err instanceof ConfigError) {
    console.error(chalk.red(`Config Error: ${err.message}`));
    if (err.cause) console.error(chalk.dim(`  Cause: ${err.cause.message}`));
    process.exit(1);
  }
  if (err instanceof LLMError) {
    console.error(chalk.red(`LLM Error: ${err.message}`));
    if (err.statusCode) console.error(chalk.dim(`  Status: ${err.statusCode}`));
    process.exit(2);
  }
  if (err instanceof TestPilotError) {
    console.error(chalk.red(`Error: ${err.message}`));
    if (err.cause) console.error(chalk.dim(`  Cause: ${err.cause.message}`));
    process.exit(1);
  }
  console.error(chalk.red('Unexpected error:'), err);
  process.exit(1);
}

export { program };
