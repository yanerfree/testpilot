export interface ParamDef {
  name: string;
  type: string;
  required: boolean;
  description?: string;
  example?: unknown;
}

export interface ResponseDef {
  status: number;
  description?: string;
  schema?: unknown;
}

export interface Endpoint {
  method: string;
  path: string;
  summary?: string;
  requestBody?: unknown;
  queryParams?: ParamDef[];
  pathParams?: ParamDef[];
  headers?: ParamDef[];
  responses?: ResponseDef[];
}

export interface ElementDef {
  name: string;
  type: string;
  selector?: string;
  testId?: string;
}

export interface PageFlow {
  name: string;
  url?: string;
  elements?: ElementDef[];
  actions?: string[];
  assertions?: string[];
}

export interface ParsedInput {
  source: 'markdown' | 'openapi' | 'text';
  title?: string;
  description?: string;
  baseUrl?: string;
  endpoints: Endpoint[];
  pages: PageFlow[];
  rawText: string;
}
