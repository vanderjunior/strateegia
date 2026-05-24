export type CapabilityStatus =
  | "implemented_and_tested"
  | "implemented_but_needs_manual_validation"
  | "partially_implemented"
  | "foundation_only"
  | "metadata_only"
  | "not_implemented";

export type ApiSource = "backend" | "mock" | "offline" | "unsupported";

export type DashboardConnectionState =
  | "mock"
  | "connected"
  | "auth_required"
  | "offline"
  | "unsupported"
  | "error";

export interface ApiErrorDetails {
  code:
    | "missing_base_url"
    | "mock_mode"
    | "network_error"
    | "timeout"
    | "unauthorized"
    | "not_found"
    | "http_error"
    | "invalid_json";
  message: string;
}

export interface ApiSuccess<T> {
  ok: true;
  data: T;
  status: number;
  source: "backend";
}

export interface ApiFailure {
  ok: false;
  status: number | null;
  source: ApiSource;
  error: ApiErrorDetails;
}

export type ApiResult<T> = ApiSuccess<T> | ApiFailure;

export interface StudyOverviewCard {
  title: string;
  value: string;
  note: string;
  metric: number;
}

export interface CapabilityCard {
  title: string;
  status: CapabilityStatus;
  summary: string;
  detail: string;
}

export interface CapabilityStatusItem {
  id: string;
  label: string;
  status: CapabilityStatus;
  source: ApiSource;
  detail: string;
}

export interface BackendConnectionInfo {
  state: DashboardConnectionState;
  source: ApiSource;
  title: string;
  detail: string;
  endpoint?: string;
}

export interface DashboardViewModel {
  connection: BackendConnectionInfo;
  studyOverviewCards: StudyOverviewCard[];
  documentCards: CapabilityCard[];
  pscppCards: CapabilityCard[];
  runtimeCards: CapabilityCard[];
  capabilityItems: CapabilityStatusItem[];
}

export interface BackendExamProfileSummary {
  format_summary?: string;
  timing_summary?: string;
  scoring_summary?: string;
  difficulty_summary?: string;
  cognitive_demand_summary?: string;
  limitation_summary?: string;
  metadata?: Record<string, unknown>;
}

export interface BackendExamProfile {
  profile_id: string;
  exam_board: string;
  profile_name: string;
  exam_family?: string;
  description?: string;
  summary?: BackendExamProfileSummary;
  question_style_profile?: {
    profile_id?: string;
    metadata?: Record<string, unknown>;
  };
  metadata?: Record<string, unknown>;
}

export interface BackendDashboardOverview {
  dashboard_available: boolean;
  dashboard_state: string;
  dashboard_summary: string;
  pipeline_readiness: string;
  study_readiness: string;
  user: {
    user_id?: string | null;
    authenticated: boolean;
  };
  materials: {
    total_materials: number;
    processed_count: number;
    pending_count: number;
    ocr_required_count: number;
  };
  document_pipeline: {
    total_documents: number;
    extracted_count: number;
    chunked_count: number;
    sectioned_count: number;
  };
  edital: {
    edital_available: boolean;
    status: string;
  };
  alignment: {
    alignment_available: boolean;
    status: string;
    gaps_detected: number;
  };
  study_cycle: {
    cycle_available: boolean;
    status: string;
    topic_slot_count: number;
  };
  exam_profile: {
    profile_available: boolean;
    suggested_profile_id?: string | null;
    exam_family?: string | null;
  };
  simulado_blueprint: {
    blueprint_available: boolean;
    status: string;
    question_slot_count: number;
    readiness_state: string;
  };
}
