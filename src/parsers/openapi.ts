import SwaggerParser from '@apidevtools/swagger-parser';
import type { ParsedInput, Endpoint, ParamDef, ResponseDef } from './types.js';
import { ParseError } from '../errors.js';

export async function parseOpenAPI(content: string, filePath: string): Promise<ParsedInput> {
  let api: any;
  try {
    api = await SwaggerParser.dereference(filePath);
  } catch (err) {
    throw new ParseError(
      `Failed to parse OpenAPI spec: ${filePath}`,
      err instanceof Error ? err : undefined,
    );
  }

  const title = api.info?.title;
  const description = api.info?.description;
  const baseUrl = extractBaseUrl(api);
  const endpoints: Endpoint[] = [];

  const paths = api.paths ?? {};
  for (const [pathStr, pathItem] of Object.entries(paths)) {
    if (!pathItem || typeof pathItem !== 'object') continue;

    for (const method of ['get', 'post', 'put', 'patch', 'delete'] as const) {
      const operation = (pathItem as Record<string, any>)[method];
      if (!operation) continue;

      const endpoint: Endpoint = {
        method: method.toUpperCase(),
        path: pathStr,
        summary: operation.summary ?? operation.description ?? '',
        responses: [],
      };

      // Parameters
      const params = [...((pathItem as any).parameters ?? []), ...(operation.parameters ?? [])];
      for (const param of params) {
        const def: ParamDef = {
          name: param.name,
          type: param.schema?.type ?? 'string',
          required: param.required ?? false,
          description: param.description,
          example: param.example ?? param.schema?.example,
        };

        switch (param.in) {
          case 'query':
            endpoint.queryParams = endpoint.queryParams ?? [];
            endpoint.queryParams.push(def);
            break;
          case 'path':
            endpoint.pathParams = endpoint.pathParams ?? [];
            endpoint.pathParams.push(def);
            break;
          case 'header':
            endpoint.headers = endpoint.headers ?? [];
            endpoint.headers.push(def);
            break;
        }
      }

      // Request body
      const reqBody = operation.requestBody;
      if (reqBody) {
        const jsonContent = reqBody.content?.['application/json'];
        if (jsonContent) {
          endpoint.requestBody = jsonContent.example ?? jsonContent.schema?.example ?? schemaToExample(jsonContent.schema);
        }
      }

      // Responses
      if (operation.responses) {
        for (const [status, resp] of Object.entries(operation.responses)) {
          const statusNum = parseInt(status, 10);
          if (isNaN(statusNum)) continue;
          const respObj = resp as any;
          const respDef: ResponseDef = {
            status: statusNum,
            description: respObj.description ?? '',
          };
          const jsonResp = respObj.content?.['application/json'];
          if (jsonResp) {
            respDef.schema = jsonResp.schema;
          }
          endpoint.responses!.push(respDef);
        }
      }

      endpoints.push(endpoint);
    }
  }

  return {
    source: 'openapi',
    title,
    description,
    baseUrl,
    endpoints,
    pages: [],
    rawText: content,
  };
}

function extractBaseUrl(api: any): string | undefined {
  if (api.servers && api.servers.length > 0) {
    return api.servers[0].url;
  }
  if (api.host) {
    const scheme = api.schemes?.[0] ?? 'http';
    const basePath = api.basePath ?? '';
    return `${scheme}://${api.host}${basePath}`;
  }
  return undefined;
}

function schemaToExample(schema: any): unknown {
  if (!schema) return undefined;
  if (schema.example !== undefined) return schema.example;

  if (schema.type === 'object' && schema.properties) {
    const obj: Record<string, unknown> = {};
    for (const [key, prop] of Object.entries(schema.properties)) {
      obj[key] = schemaToExample(prop as any);
    }
    return obj;
  }

  switch (schema.type) {
    case 'string': return schema.enum?.[0] ?? 'string';
    case 'number': case 'integer': return 0;
    case 'boolean': return true;
    case 'array': return schema.items ? [schemaToExample(schema.items)] : [];
    default: return undefined;
  }
}
