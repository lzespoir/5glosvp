// 与后端 OpenAPI（/openapi.json）保持一致 / Mirrors the backend OpenAPI contract.

export interface ErrorBody {
  code: string;
  message_zh: string;
  message_en: string;
  detail?: Record<string, unknown>;
}

export interface ErrorResponse {
  error: ErrorBody;
}

export interface ListResponse<T> {
  items: T[];
}

export interface HealthResponse {
  status: string;
  service: string;
  name_zh: string;
  name_en: string;
  version: string;
  testing: boolean;
}

/** 数据来源类型；前端不认识的值按字符串原样展示。 */
export type SourceType = 'simulation' | 'test_fixture';
