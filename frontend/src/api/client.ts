import axios, { AxiosError } from 'axios';

import type { ErrorBody, ErrorResponse } from '../types/common';

/** 唯一的 API 基地址配置点 / Single place configuring the API base URL. */
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  // 请求等待超时与科学运行状态分离；长运行由运行记录轮询和执行管理器负责。
  timeout: 15 * 60 * 1000,
});

/**
 * 后端返回的 artifact url 是以 /api/v1 开头的路径，需要按 API 所在的源解析，
 * 这样 VITE_API_BASE_URL 指向其他主机时也能正确访问。
 */
export function resolveApiUrl(path: string): string {
  const base = new URL(API_BASE_URL, window.location.origin);
  return new URL(path, base).href;
}

/** 前端统一错误对象 / Normalized API error. */
export class ApiError extends Error {
  readonly status: number | null;
  readonly code: string;
  readonly messageZh: string;
  readonly messageEn: string;
  readonly detail: Record<string, unknown>;

  constructor(status: number | null, body: ErrorBody) {
    super(body.message_en);
    this.name = 'ApiError';
    this.status = status;
    this.code = body.code;
    this.messageZh = body.message_zh;
    this.messageEn = body.message_en;
    this.detail = body.detail ?? {};
  }
}

function isErrorResponse(data: unknown): data is ErrorResponse {
  if (typeof data !== 'object' || data === null || !('error' in data)) return false;
  const error = (data as { error: unknown }).error;
  return typeof error === 'object' && error !== null && 'code' in error;
}

export function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err;
  if (err instanceof AxiosError) {
    const status = err.response?.status ?? null;
    const data: unknown = err.response?.data;
    if (isErrorResponse(data)) return new ApiError(status, data.error);
    if (!err.response) {
      return new ApiError(null, {
        code: 'NETWORK_ERROR',
        message_zh: '无法连接后端服务',
        message_en: 'Cannot reach the backend API',
        detail: { reason: err.message },
      });
    }
    return new ApiError(status, {
      code: `HTTP_${status}`,
      message_zh: '请求失败',
      message_en: 'Request failed',
      detail: { reason: err.message },
    });
  }
  return new ApiError(null, {
    code: 'UNKNOWN_ERROR',
    message_zh: '未知错误',
    message_en: 'Unknown error',
    detail: { reason: err instanceof Error ? err.message : String(err) },
  });
}

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => Promise.reject(toApiError(error)),
);
