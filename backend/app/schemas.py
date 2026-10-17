from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Any, Optional

class OpenCVMetrics(BaseModel):
    flood_contour_ratio: float = Field(..., description="Ratio of flood/debris contour area to total frame area")
    edge_density: float = Field(..., description="Ratio of non-zero Canny edge pixels to total pixels")
    glare_or_shadow_ratio: float = Field(..., description="Ratio of overexposed (>240) or underexposed (<25) pixels")
    homography_inliers: int = Field(default=0, description="Number of USAC_MAGSAC inlier matches between viewpoints")
    motion_flow_magnitude: float = Field(default=0.0, description="Mean Farneback dense optical flow vector magnitude in pixels")
    execution_time_ms: float = Field(..., description="Execution time of the OpenCV operation in milliseconds")

class LlamaReasoningResult(BaseModel):
    observed_hazard: str = Field(..., description="Concise description of flood, debris, road blockage, or stranded entity")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Calibrated confidence score between 0.0 and 1.0")
    uncertainty_reason: str = Field(..., description="Specific reason for uncertainty (e.g., glare, occlusion, shadow, oblique angle, none)")
    recommended_action: Literal[
        "ENHANCE_ROI_CONTRAST",
        "REQUEST_ALTERNATE_VIEWPOINT",
        "COMPUTE_OPTICAL_FLOW_SURGE",
        "ESCALATE_HUMAN_REVIEW",
        "CLOSE_INCIDENT"
    ] = Field(..., description="Next deterministic action recommended by the reasoning engine")
    evidence_needed: str = Field(..., description="Specific visual or geometric evidence needed to confirm hypothesis")
    target_roi_normalized: List[float] = Field(
        default=[0.0, 0.0, 1.0, 1.0],
        description="[x1, y1, x2, y2] normalized 0.0 to 1.0 bounding box for targeted ROI processing"
    )

class TraceStep(BaseModel):
    step: int
    phase: str
    action_taken: Optional[str] = None
    cv: Dict[str, Any]
    llm: Dict[str, Any]
    context: Optional[str] = None

class VisualEvidence(BaseModel):
    initial_annotated_base64: Optional[str] = None
    post_action_annotated_base64: Optional[str] = None
    flow_visualization_base64: Optional[str] = None
    homography_warped_base64: Optional[str] = None
    s3_primary_url: Optional[str] = None
    s3_post_action_url: Optional[str] = None
    dynamodb_persisted: bool = False

class InspectionResponse(BaseModel):
    incident_id: str
    final_status: str
    trace: List[dict]
    action_taken: Optional[str] = None
    confidence_delta: float = 0.0
    metrics_summary: Optional[Dict[str, Any]] = None
    visual_evidence: Optional[VisualEvidence] = None
    evidence_url: Optional[str] = None

    def __getitem__(self, item: str) -> Any:
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item)


class BenchmarkResult(BaseModel):
    operation: str
    iterations: int
    mean_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_fps: float
    kleidicv_speedup_factor: Optional[float] = None
    hardware: str
