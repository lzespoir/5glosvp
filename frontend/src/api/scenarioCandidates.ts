import { apiClient } from './client';

export interface ScenarioCandidate {
  candidate_id: string;
  candidate_hash: string;
  taxonomy_version: string;
  name_zh: string;
  name_en: string;
  scenario_family: string;
  dimensions: Record<string, string>;
  compatibility_status: string;
  support_status: string;
  supported_problem_types: string[];
  source: string;
  acceptance_eligible: false;
}

export interface CandidatePreview {
  theoretical_count: number;
  valid_candidate_count: number;
  invalid_candidate_count: number;
  executable_candidate_count: number;
  external_dependency_candidate_count: number;
  filtered_candidate_count: number;
  total: number;
  offset: number;
  limit: number;
  returned_count: number;
  has_more: boolean;
  truncated: boolean;
  query_hash: string;
  taxonomy_version: string;
  items: ScenarioCandidate[];
  persisted: false;
  configured_count_changed: false;
  acceptance_eligible: false;
}

export const scenarioCandidatesApi = {
  preview: async (selection: Record<string, string[]>, options: { offset?: number; limit?: number; filters?: Record<string, string>; query_hash?: string } = {}) => (await apiClient.post<CandidatePreview>('/scenario-candidates/preview', { selection, offset: 0, limit: 20, filters: {}, ...options })).data,
  promote: async (candidate: ScenarioCandidate) => (await apiClient.post('/scenario-candidates/' + encodeURIComponent(candidate.candidate_id) + '/promote', { dimensions: candidate.dimensions })).data as { scenario_id: string; state: string },
};
