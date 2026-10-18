export interface OpenCVMetrics {
  flood_contour_ratio: number;
  edge_density: number;
  glare_or_shadow_ratio: number;
  homography_inliers: number;
  motion_flow_magnitude: number;
  execution_time_ms: number;
}

export interface LlamaReasoning {
  observed_hazard: string;
  confidence: number;
  uncertainty_reason: string;
  recommended_action: string;
  evidence_needed?: string;
  target_roi_normalized?: number[];
}

export interface TraceStep {
  step: number;
  phase: string;
  action_taken?: string;
  cv: OpenCVMetrics;
  llm: LlamaReasoning;
  context?: string;
}

export interface VisualEvidence {
  initial_annotated_base64?: string;
  post_action_annotated_base64?: string;
  flow_visualization_base64?: string;
  homography_warped_base64?: string;
  s3_primary_url?: string;
  s3_post_action_url?: string;
  dynamodb_persisted?: boolean;
}

export interface InspectionResponse {
  incident_id: string;
  final_status: string;
  trace: TraceStep[];
  evidence_url?: string; // S3 URL returned from Phase 2
  action_taken?: string;
  confidence_delta?: number;
  metrics_summary?: Record<string, unknown>;
  visual_evidence?: VisualEvidence;
  gps?: { lat: number; lng: number };
}
export interface LiveDisaster {
  id: string;
  title: string;
  source: string;
  status: string;
  url: string;
  lat?: number | null;
  lng?: number | null;
}
