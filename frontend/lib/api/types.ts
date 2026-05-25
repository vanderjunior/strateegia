export type CapabilityStatus =
  | "implemented_and_tested"
  | "implemented_but_needs_manual_validation"
  | "partially_implemented"
  | "foundation_only"
  | "metadata_only"
  | "mocked_or_demo_only"
  | "not_implemented"
  | "intentionally_deferred"
  | "unclear_needs_follow_up";

export type Audience = "public" | "student" | "mentor" | "admin" | "developer";

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
    | "api_base_missing"
    | "backend_offline"
    | "endpoint_unavailable"
    | "auth_required"
    | "method_not_allowed"
    | "file_too_large"
    | "unsupported_file_type"
    | "validation_failed"
    | "missing_base_url"
    | "mock_mode"
    | "network_error"
    | "timeout"
    | "unauthorized"
    | "not_found"
    | "bad_request"
    | "payload_too_large"
    | "unsupported_media"
    | "validation_error"
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
  id?: string;
  internalKey?: string;
  title: string;
  value: string;
  note: string;
  metric: number;
}

export interface CapabilityCard {
  internalKey?: string;
  title: string;
  status: CapabilityStatus;
  summary: string;
  detail: string;
}

export interface CapabilityStatusItem {
  id: string;
  internalKey?: string;
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

export interface BackendDocumentSummary {
  id: string;
  title: string;
  source_filename: string;
  created_at?: string;
}

export interface BackendDocumentPipelineState {
  document_id: string;
  current_stage: string;
  stages_completed: string[];
  extraction_status: string;
  chunking_status: string;
  sectioning_status: string;
  metadata_status: string;
  error_count: number;
  text_length: number;
  chunk_count: number;
  section_count: number;
}

export interface BackendDocumentSection {
  section_id: string;
  document_id: string;
  title: string;
  level: number;
  order_index: number;
  start_chunk_index: number;
  end_chunk_index: number;
}

export interface BackendDocumentChunk {
  chunk_id: string;
  document_id: string;
}

export interface BackendEditalWarning {
  code: string;
  message: string;
  severity?: string;
}

export interface BackendEditalTopicCandidate {
  topic_id: string;
  title: string;
  confidence?: number;
}

export interface BackendEditalBibliographyCandidate {
  bibliography_id: string;
  title?: string;
  raw_reference: string;
}

export interface BackendEditalExtraction {
  edital_id: string;
  document_id: string;
  topics: BackendEditalTopicCandidate[];
  bibliography: BackendEditalBibliographyCandidate[];
  warnings: BackendEditalWarning[];
}

export interface BackendTopicCoverageCandidate {
  topic_id: string;
  topic_title: string;
  coverage_state: string;
}

export interface BackendCoverageGap {
  gap_id: string;
  gap_type: string;
  target_title: string;
  reason: string;
  severity?: string;
}

export interface BackendBibliographyAlignmentItem {
  bibliography_id: string;
  raw_reference: string;
  match_state: string;
}

export interface BackendAlignmentWarning {
  code: string;
  message: string;
  severity?: string;
}

export interface BackendBibliographyAlignment {
  alignment_id: string;
  edital_id: string;
  topic_coverage: BackendTopicCoverageCandidate[];
  gaps: BackendCoverageGap[];
  bibliography_alignments: BackendBibliographyAlignmentItem[];
  warnings: BackendAlignmentWarning[];
}

export interface WorkspaceSummaryMetric {
  id: string;
  label: string;
  value: string;
  detail: string;
}

export interface MaterialListItem {
  id: string;
  title: string;
  typeLabel: string;
  processingStatus: string;
  extractionStatus: string;
  sectionsCount: number | null;
  chunksCount: number | null;
  reviewState: string;
  source: ApiSource;
  relatedGaps: number;
}

export interface MaterialSectionPreview {
  id: string;
  title: string;
  level: number;
  chunkRangeLabel: string;
}

export interface MaterialDetail extends MaterialListItem {
  warnings: string[];
  sectionPreviews: MaterialSectionPreview[];
  sourceNote: string;
}

export interface MaterialsWorkspaceViewModel {
  connection: BackendConnectionInfo;
  summary: WorkspaceSummaryMetric[];
  items: MaterialListItem[];
}

export interface CoverageItem {
  id: string;
  title: string;
  coverageLabel: string;
  detail: string;
  source: ApiSource;
}

export interface GapItem {
  id: string;
  title: string;
  detail: string;
  severityLabel: string;
  source: ApiSource;
}

export interface EditalListItem {
  id: string;
  title: string;
  statusLabel: string;
  topicsCount: number;
  bibliographyItemsCount: number;
  gapsCount: number;
  reviewState: string;
  source: ApiSource;
}

export interface EditalDetail extends EditalListItem {
  topicCandidates: string[];
  bibliographyCandidates: string[];
  coverageItems: CoverageItem[];
  gapItems: GapItem[];
  warnings: string[];
  notes: string[];
}

export interface EditaisWorkspaceViewModel {
  connection: BackendConnectionInfo;
  summary: WorkspaceSummaryMetric[];
  items: EditalListItem[];
}

export interface PipelineStep {
  id: string;
  label: string;
  statusLabel: string;
  tone: "complete" | "current" | "warning" | "pending";
  detail: string;
}

export interface PipelineDetailViewModel {
  connection: BackendConnectionInfo;
  documentId: string;
  title: string;
  source: ApiSource;
  extractionStatus: string;
  reviewState: string;
  sectionsCount: number | null;
  chunksCount: number | null;
  notes: string[];
  steps: PipelineStep[];
}

export interface PscppPriorityBlock {
  id: string;
  title: string;
  detail: string;
}

export interface PscppPhaseItem {
  id: string;
  title: string;
  detail: string;
}

export interface PscppRotationSession {
  id: string;
  index: number;
  title: string;
  detail: string;
}

export interface PscppNotebookItem {
  id: string;
  title: string;
  detail: string;
}

export interface PscppQuestionGuidanceItem {
  id: string;
  title: string;
  detail: string;
}

export interface PscppWorkspaceViewModel {
  connection: BackendConnectionInfo;
  summary: WorkspaceSummaryMetric[];
  profileTitle: string;
  profileDescription: string;
  statusLabel: string;
  modeLabel: string;
  examProfileId: string;
  questionStyleProfileId: string;
  studyCycleProfileId: string;
  evidence: string[];
  evidenceNotes: string[];
  priorityBlocks: PscppPriorityBlock[];
}

export interface PscppCycleViewModel {
  connection: BackendConnectionInfo;
  summary: WorkspaceSummaryMetric[];
  modeLabel: string;
  weeklyGuidance: string;
  overrideLabel: string;
  baselineLabel: string;
  sessionStructure: string[];
  phasePlan: PscppPhaseItem[];
  notebookSystem: PscppNotebookItem[];
  rotation: PscppRotationSession[];
}

export interface PscppQuestionsViewModel {
  connection: BackendConnectionInfo;
  summary: WorkspaceSummaryMetric[];
  archetypes: PscppQuestionGuidanceItem[];
  sourceRules: PscppQuestionGuidanceItem[];
  reviewRules: PscppQuestionGuidanceItem[];
  relationToSimulado: string[];
}

export interface PscppCrosswalkMaterialRef {
  id: string;
  title: string;
  typeLabel: string;
  statusLabel: string;
  linkHref: string;
}

export interface PscppCrosswalkEditalRef {
  id: string;
  title: string;
  statusLabel: string;
  linkHref: string;
}

export interface PscppCrosswalkSessionRef {
  id: string;
  index: number;
  label: string;
  detail: string;
  emphasis?: "default" | "gap_focus";
}

export interface PscppCrosswalkBlockItem {
  id: string;
  priorityNumber: number;
  title: string;
  coverageLabel: string;
  reviewState: string;
  materialsCount: number;
  gapsCount: number;
  suggestedSessions: PscppCrosswalkSessionRef[];
  relatedMaterials: PscppCrosswalkMaterialRef[];
  relatedEditais: PscppCrosswalkEditalRef[];
  gaps: string[];
  notes: string[];
}

export interface PscppCrosswalkGapItem {
  id: string;
  title: string;
  affectedBlockTitle: string;
  whyItMatters: string;
  suggestedAction: string;
  reviewState: string;
  relatedSessions: PscppCrosswalkSessionRef[];
}

export interface PscppCrosswalkRelationshipItem {
  id: string;
  material: PscppCrosswalkMaterialRef;
  edital: PscppCrosswalkEditalRef;
  blockTitle: string;
  contributionLabel: string;
}

export interface PscppCrosswalkViewModel {
  connection: BackendConnectionInfo;
  summary: WorkspaceSummaryMetric[];
  blocks: PscppCrosswalkBlockItem[];
  mainGaps: PscppCrosswalkGapItem[];
  relationships: PscppCrosswalkRelationshipItem[];
  highlightedSessions: PscppCrosswalkSessionRef[];
}

export interface StudySessionChecklistItem {
  id: string;
  label: string;
}

export interface StudySessionRelatedGap {
  id: string;
  title: string;
  detail: string;
}

export interface StudySessionOutputExpectation {
  id: string;
  label: string;
  statusLabel: string;
}

export interface StudySessionListItem {
  id: string;
  sessionNumber: number;
  title: string;
  objective: string;
  priorityBlockTitle: string;
  durationLabel: string;
  relatedMaterialsCount: number;
  relatedGapsCount: number;
  statusLabel: string;
  note: string;
}

export interface StudySessionDetail extends StudySessionListItem {
  structure: string[];
  relatedMaterials: PscppCrosswalkMaterialRef[];
  relatedEditais: PscppCrosswalkEditalRef[];
  relatedGaps: StudySessionRelatedGap[];
  checklist: StudySessionChecklistItem[];
  outputs: StudySessionOutputExpectation[];
  cautions: string[];
}

export interface StudySessionWorkspaceViewModel {
  connection: BackendConnectionInfo;
  summary: WorkspaceSummaryMetric[];
  nextSuggestedSessionId: string;
  sessions: StudySessionListItem[];
  highlightedGaps: StudySessionRelatedGap[];
  starterMaterials: PscppCrosswalkMaterialRef[];
}

export type UploadValidationState =
  | "idle"
  | "validating"
  | "valid"
  | "invalid_type"
  | "invalid_size"
  | "missing_confirmation";

export type UploadEntryState =
  | "idle"
  | "validating"
  | "ready_to_send"
  | "sending"
  | "received"
  | "failed"
  | "mock_only"
  | "endpoint_unavailable";

export interface AcceptedUploadType {
  id: string;
  label: string;
  extensions: string[];
  mimeTypes: string[];
  note?: string;
}

export interface UploadMaterialResult {
  documentId: string;
  filename: string;
  originalFilename: string;
  contentType: string;
  sizeBytes: number;
  processingStatus: string;
  extractionStatus: string;
  reviewState: string;
  source: ApiSource;
  demoOnly: boolean;
}
