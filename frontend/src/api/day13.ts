import { useMutation, useQuery } from '@tanstack/react-query';

import { apiClient } from './client';
import type { AMatrixLibrary, AMatrixPattern, AMatrixProfile, UETwinResult } from '../types/day13';

export const day13Keys = {
  libraries: ['day13', 'a-matrix', 'libraries'] as const,
  profiles: ['day13', 'a-matrix', 'profiles'] as const,
  pattern: (library: string, beamType: string, entryKey: string) => ['day13', 'a-matrix', 'pattern', library, beamType, entryKey] as const,
};

export async function fetchAMatrixLibraries(): Promise<AMatrixLibrary[]> {
  const { data } = await apiClient.get<{ items: AMatrixLibrary[] }>('/a-matrix/libraries');
  return data.items;
}

export async function fetchAMatrixProfiles(): Promise<AMatrixProfile[]> {
  const { data } = await apiClient.get<{ items: AMatrixProfile[] }>('/a-matrix/profiles');
  return data.items;
}

export async function fetchAMatrixPattern(library: string, beamType: string, entryKey: string): Promise<AMatrixPattern> {
  const { data } = await apiClient.get<AMatrixPattern>('/a-matrix/pattern', { params: { library, beam_type: beamType, entry_key: entryKey } });
  return data;
}

export async function queryUETwin(payload: Record<string, unknown>): Promise<UETwinResult> {
  const { data } = await apiClient.post<UETwinResult>('/ue-twin/query', payload);
  return data;
}

export function useAMatrixLibraries() {
  return useQuery({ queryKey: day13Keys.libraries, queryFn: fetchAMatrixLibraries, staleTime: 60_000 });
}

export function useAMatrixProfiles() {
  return useQuery({ queryKey: day13Keys.profiles, queryFn: fetchAMatrixProfiles, staleTime: 60_000 });
}

export function useAMatrixPattern(library: string, beamType: string, entryKey: string) {
  return useQuery({ queryKey: day13Keys.pattern(library, beamType, entryKey), queryFn: () => fetchAMatrixPattern(library, beamType, entryKey), enabled: Boolean(entryKey), staleTime: 60_000 });
}

export function useUETwinQuery() {
  return useMutation({ mutationFn: queryUETwin });
}
