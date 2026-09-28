export interface BackendInfo {
  id: string;
  name_zh: string;
  name_en: string;
  available: boolean;
  version?: string | null;
  capabilities?: string[];
  reason?: string | null;
  source_type?: string;
}
