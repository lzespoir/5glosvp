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
  returned_count: number;
  truncated: boolean;
  items: ScenarioCandidate[];
  persisted: false;
  configured_count_changed: false;
}

export const scenarioCandidatesApi = {
  preview: async (selection: Record<string, string[]>, limit = 50) => (await apiClient.post<CandidatePreview>('/scenario-candidates/preview', { selection, limit })).data,
  promote: async (candidate: ScenarioCandidate) => (await apiClient.post('/scenario-candidates/' + encodeURIComponent(candidate.candidate_id) + '/promote', { dimensions: candidate.dimensions })).data as { scenario_id: string; state: string },
};
