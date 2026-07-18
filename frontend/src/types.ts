// Mirrors backend/app/schema.py. Keep the two in sync.

export interface TranscriptRef {
  line: number | null;
  timestamp: string | null;
  speaker: string | null;
  quote: string | null;
}

export type RationaleStatus = "stated" | "not_stated";
export type OperabilityStatus = "not_applicable" | "cleared" | "not_confirmed";

export interface Finding {
  issue: string;
  evidence_ref: string;
  recommendation: string;
  recommendation_grade: string | null;
  match_confidence: number; // 0..1 — the agent's certainty it fits THIS patient
  rationale_status: RationaleStatus;
  patient_facing_note: string;
  live_question: string;
  source_agent: string;
  proposes_procedure: boolean;
  operability_status: OperabilityStatus;
  transcript_ref: TranscriptRef | null;
}

export interface ActionItem {
  action: string;
  owner: string;
  deadline: string | null;
  linked_finding: string | null;
}

export interface SourceRef {
  location: string;
  line: number | null;
  speaker: string | null;
  quote: string;
  grounded: boolean;
  grounding_note: string | null;
}

export interface InferredObservation {
  kind: string;
  summary: string;
  value: string | null;
  confidence: number;
  rationale: string;
  raises_check: string | null;
  source: SourceRef;
  inferred: true;
}

export interface Enrichment {
  inferred: InferredObservation[];
  rejected: InferredObservation[];
  model: string | null;
  skipped_reason: string | null;
}

export interface TriggeredCheck {
  raised_by: string;
  tool: string;
  input: Record<string, unknown>;
  result: Record<string, unknown>;
}

export interface AnalysisResult {
  findings: Finding[];
  action_ledger: ActionItem[];
  enrichment: Enrichment;
  // Tools an inference triggered (raises_check) with results — these gate findings.
  triggered_checks: TriggeredCheck[];
  truncated?: boolean;
}

export interface TranscriptLine {
  line: number;
  timestamp: string | null;
  speaker: string | null;
  text: string;
}

export interface MissingField {
  field: string;
  reason: string;
}

// Normalized case is intentionally loose on the frontend — it mirrors
// backend TumorBoardCase but we only strongly type what the UI reads.
export interface CaseResponse {
  record: Record<string, unknown>;
  case: Record<string, unknown>;
  completeness: MissingField[];
  transcript: TranscriptLine[];
}

// --- Patient data browser (data/cases/<case_id>/<specialty>/*.md) -------------

export interface Document {
  doc_id: string;
  folder: string;
  filename: string;
  title: string;
  date: string | null;
  body: string;
}

export interface Folder {
  name: string;
  label: string;
  documents: Document[];
}

export interface CaseSummary {
  case_id: string;
  cancer_type: string | null;
  patient_ref: string | null;
  line_of_therapy: string | null;
  board_date: string | null;
  folder_names: string[];
  document_count: number;
}

export interface CaseDetail extends CaseSummary {
  folders: Folder[];
  transcript: string | null;
}
