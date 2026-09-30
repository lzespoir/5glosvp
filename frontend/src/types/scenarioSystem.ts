export interface TaxonomyOption {
  value: string;
  label_zh: string;
  label_en: string;
  status: string;
}

export interface TaxonomyDimension {
  key: string;
  label_zh: string;
  label_en: string;
  options: TaxonomyOption[];
}

export interface ScenarioTaxonomy {
  taxonomy_version: string;
  dimensions: TaxonomyDimension[];
  families: { value: string; label_zh: string; label_en: string }[];
}

export interface ScenarioCounts {
  theoretical_count: number;
  valid_count: number;
  invalid_count: number;
  executable_count: number;
  requires_external_asset_count: number;
  materialized_count?: number;
  executed_count?: number;
  definition_verified_count?: number;
  experiment_verified_count?: number;
  verified_count?: number;
  acceptance_evidence_count?: number;
}

export interface ScenarioDefinition {
  scenario_id: string;
  name_zh: string;
  name_en: string;
  description: string;
  taxonomy_version: string;
  scenario_family: string;
  dimensions: Record<string, string>;
  compatibility_status: string;
  support_status: string;
  model_bindings: Record<string, unknown>;
  dataset_bindings: Record<string, unknown>;
  artifact_bindings: Record<string, unknown>;
  supported_problem_types: string[];
  source: string;
  version: string;
  scenario_definition_hash: string;
  experiment_scenario_id?: string | null;
}

export interface ScenarioPreview {
  counts: ScenarioCounts;
  combinations: ScenarioDefinition[];
  truncated: boolean;
}

export interface ScenarioCoverage {
  counts: ScenarioCounts;
  matrix: Array<{ row: string; column: string; dimensions: Record<string, string>; counts: ScenarioCounts }>;
  family_counts: Record<string, ScenarioCounts>;
}

export interface AcceptanceMapping {
  key: string;
  title_zh: string;
  title_en: string;
  status: string;
  evidence: string[];
  note_zh: string;
}

export interface ScenarioWorkspace {
  workspace_status: string;
  scenario: ScenarioDefinition;
  scenario_instance: {
    scenario_instance_id: string;
    scenario_id: string;
    scenario_version: string;
    scenario_definition_hash: string;
    seed: number;
    status: string;
  };
  experiment_identity: Record<string, string>;
  message_zh: string;
}
