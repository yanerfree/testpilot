export class TestPilotError extends Error {
  constructor(message: string, public override cause?: Error) {
    super(message);
    this.name = 'TestPilotError';
  }
}

export class ConfigError extends TestPilotError {
  override name = 'ConfigError';
}

export class ParseError extends TestPilotError {
  override name = 'ParseError';
}

export class LLMError extends TestPilotError {
  override name = 'LLMError';
  constructor(message: string, public statusCode?: number, cause?: Error) {
    super(message, cause);
  }
}

export class OutputError extends TestPilotError {
  override name = 'OutputError';
}
