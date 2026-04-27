import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { loadConfig, resolveApiKey, type CLIFlags } from './config/loader.js';
import { createLLMProvider } from './llm/factory.js';
import { generateTests } from './generator/generator.js';
import { TestPilotError, ConfigError, LLMError } from './errors.js';
import type { TestMode } from './llm/types.js';
import type { InputFormat } from './parsers/detect.js';

const program = new Command();

program
  .name('testpilot')
  .description('AI-powered test case generation agent')
  .version('0.1.0');

program
  .command('generate')
  .description('Generate test cases from requirements docs, OpenAPI specs, or text')
  .argument('<input...>', 'Input file(s) — Markdown, OpenAPI YAML/JSON, or plain text')
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
    const flags: CLIFlags = {
      mode: opts.mode as TestMode,
      format: opts.format as InputFormat | undefined,
      outdir: opts.outdir,
      executor: opts.executor,
      model: opts.model,
      apiKey: opts.apiKey,
      dryRun: opts.dryRun,
      verbose: opts.verbose,
      force: opts.force,
    };

    try {
      const config = await loadConfig(flags);

      if (config.executor === 'self') {
        // TODO: self 模式 — agent 自身生成，不调外部 API
        console.log(chalk.yellow('Self executor mode — not yet implemented in CLI. Use as Claude Code agent instead.'));
        process.exit(0);
      }

      const apiKey = resolveApiKey(config);
      const provider = createLLMProvider(config, apiKey);

      for (const inputPath of inputs) {
        const spinner = ora({
          text: `Generating ${flags.mode} test cases from ${inputPath}...`,
          color: 'cyan',
        }).start();

        try {
          const result = await generateTests({
            inputPath,
            mode: flags.mode ?? 'api',
            config,
            provider,
            format: flags.format as InputFormat | undefined,
            dryRun: flags.dryRun,
            verbose: flags.verbose,
          });

          spinner.succeed(
            flags.dryRun
              ? `Generated ${flags.mode} test cases from ${inputPath}`
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
        } catch (err) {
          spinner.fail(`Failed to generate test cases from ${inputPath}`);
          throw err;
        }
      }
    } catch (err) {
      handleError(err);
    }
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
