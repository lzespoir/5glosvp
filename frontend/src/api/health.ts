import { useQuery } from '@tanstack/react-query';

import type { HealthResponse } from '../types/common';
import { apiClient } from './client';

export const healthKeys = { all: ['health'] as const };

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>('/health');
  return data;
}

export function useHealth() {
  return useQuery({ queryKey: healthKeys.all, queryFn: fetchHealth, refetchInterval: 30_000 });
}
