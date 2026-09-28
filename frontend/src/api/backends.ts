import { useQuery } from '@tanstack/react-query';

import type { BackendInfo } from '../types/backend';
import type { ListResponse } from '../types/common';
import { apiClient } from './client';

export const backendKeys = { all: ['backends'] as const };

export async function fetchBackends(): Promise<BackendInfo[]> {
  const { data } = await apiClient.get<ListResponse<BackendInfo>>('/backends');
  return data.items;
}

export function useBackends() {
  return useQuery({ queryKey: backendKeys.all, queryFn: fetchBackends, refetchInterval: 30_000 });
}
