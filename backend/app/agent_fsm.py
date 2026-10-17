import numpy as np
import uuid
from typing import Optional, Dict, Any
from .cv_engine import SwarmCVEngine
from .nim_reasoner import NimVisionReasoner
from .floodnet_loader import create_synthetic_alternate_view, create_synthetic_temporal_surge
from .schemas import (
    InspectionResponse,
    TraceStep,
    VisualEvidence,
    OpenCVMetrics,
    LlamaReasoningResult
)

class SwarmTwinAgent:
    """
    Deterministic Agentic State Machine.
    Enforces the Perception -> Decision -> Action -> Verification loop:
    1. Phase 1 (Initial Perception): OpenCV calculates baseline metrics (flood contour ratio,
       edge density, glare/shadow ratio); Llama 3.2 Vision analyzes metrics alongside frame.
    2. Phase 2 (Action Execution): Triggers CLAHE (ENHANCE_ROI_CONTRAST), USAC_MAGSAC
       homography (REQUEST_ALTERNATE_VIEWPOINT), or Farnebäck dense optical flow (COMPUTE_OPTICAL_FLOW_SURGE).
    3. Phase 3 (Verification): Llama 3.2 Vision reviews post-action frame + updated OpenCV
       metrics to confirm/refute hypothesis and produces final verdict.
    """
    def __init__(self, cv_engine: SwarmCVEngine, reasoner: NimVisionReasoner):
        self.cv = cv_engine
        self.reasoner = reasoner

    def run_inspection_episode(
        self,
        primary_frame: np.ndarray,
        alt_view_frame: Optional[np.ndarray] = None,
        temporal_frame: Optional[np.ndarray] = None,
        incident_id: Optional[str] = None,
        force_action: Optional[str] = None
    ) -> InspectionResponse:
        inc_id = incident_id or f"INC-{uuid.uuid4().hex[:4].upper()}"
        trace: list[dict] = []
        visual_evidence = VisualEvidence()

        # =========================================================================
        # PHASE 1: INITIAL PERCEPTION & REASONING
        # =========================================================================
        annotated_1, metrics_1 = self.cv.analyze_frame(primary_frame)
        visual_evidence.initial_annotated_base64 = self.cv.encode_base64(annotated_1)

        decision_1 = self.reasoner.reason_on_frame(
            primary_frame,
            metrics_1,
            step_context="Initial pass from Drone A nadir feed."
        )

        trace.append({
            "step": 1,
            "phase": "INITIAL_PERCEPTION",
            "cv": metrics_1.model_dump(),
            "llm": decision_1.model_dump()
        })

        action = decision_1.recommended_action
        if force_action in ("ENHANCE_ROI_CONTRAST", "REQUEST_ALTERNATE_VIEWPOINT", "COMPUTE_OPTICAL_FLOW_SURGE"):
            action = force_action
        elif temporal_frame is not None:
            action = "COMPUTE_OPTICAL_FLOW_SURGE"
        elif alt_view_frame is not None:
            action = "REQUEST_ALTERNATE_VIEWPOINT"
        elif metrics_1.glare_or_shadow_ratio > 0.12 or action == "ENHANCE_ROI_CONTRAST":
            action = "ENHANCE_ROI_CONTRAST"

        # If decision is already terminal with high confidence and no tool needed
        if action in ("ESCALATE_HUMAN_REVIEW", "CLOSE_INCIDENT"):
            final_status = "ESCALATE_HUMAN_REVIEW" if decision_1.confidence >= 0.70 else "UNRESOLVED_LOW_CONFIDENCE"
            return InspectionResponse(
                incident_id=inc_id,
                final_status=final_status,
                action_taken=None,
                confidence_delta=0.0,
                trace=trace,
                metrics_summary=metrics_1.model_dump(),
                visual_evidence=visual_evidence
            )

        # =========================================================================
        # PHASE 2: PARAMETRIC OPENCV ACTION EXECUTION
        # =========================================================================
        post_img: np.ndarray
        metrics_2: OpenCVMetrics
        action_context: str

        if action == "ENHANCE_ROI_CONTRAST":
            next_img = self.cv.enhance_roi_clahe(primary_frame, decision_1.target_roi_normalized)
            annotated_2, metrics_2 = self.cv.analyze_frame(next_img)
            post_img = next_img
            action_context = f"Applied OpenCV CLAHE on ROI {decision_1.target_roi_normalized} to resolve {decision_1.uncertainty_reason}."
            visual_evidence.post_action_annotated_base64 = self.cv.encode_base64(annotated_2)

        elif action == "REQUEST_ALTERNATE_VIEWPOINT":
            # If caller didn't provide a secondary drone view, synthesize realistic oblique perspective
            drone_b_frame = alt_view_frame if alt_view_frame is not None else create_synthetic_alternate_view(primary_frame)
            warped, inliers = self.cv.register_alternate_viewpoint(primary_frame, drone_b_frame)
            annotated_2, metrics_2 = self.cv.analyze_frame(warped)
            metrics_2.homography_inliers = inliers
            post_img = warped
            action_context = f"Warped Drone B view with {inliers} USAC_MAGSAC inliers to resolve occlusion."
            visual_evidence.homography_warped_base64 = self.cv.encode_base64(warped)
            visual_evidence.post_action_annotated_base64 = self.cv.encode_base64(annotated_2)

        elif action == "COMPUTE_OPTICAL_FLOW_SURGE":
            # If caller didn't provide a burst frame, synthesize consecutive dynamic surge frame
            t1_frame = temporal_frame if temporal_frame is not None else create_synthetic_temporal_surge(primary_frame)
            flow_vis, avg_mag = self.cv.compute_optical_flow(primary_frame, t1_frame)
            _, metrics_2 = self.cv.analyze_frame(primary_frame)
            metrics_2.motion_flow_magnitude = round(avg_mag, 4)
            post_img = flow_vis
            action_context = f"Computed Farneback dense optical flow. Average vector magnitude: {avg_mag:.2f}px/frame."
            visual_evidence.flow_visualization_base64 = self.cv.encode_base64(flow_vis)
            visual_evidence.post_action_annotated_base64 = self.cv.encode_base64(flow_vis)

        else:
            final_status = "ESCALATE_HUMAN_REVIEW" if decision_1.confidence >= 0.70 else "UNRESOLVED_LOW_CONFIDENCE"
            return InspectionResponse(
                incident_id=inc_id,
                final_status=final_status,
                action_taken=action,
                confidence_delta=0.0,
                trace=[s if isinstance(s, dict) else s.model_dump() for s in trace],
                metrics_summary=metrics_1.model_dump(),
                visual_evidence=visual_evidence
            )

        # =========================================================================
        # PHASE 3: VERIFICATION REASONING AFTER OPENCV ACTION
        # =========================================================================
        decision_2 = self.reasoner.reason_on_frame(
            post_img,
            metrics_2,
            step_context=action_context
        )

        trace.append({
            "step": 2,
            "phase": "VERIFICATION_AFTER_ACTION",
            "action_taken": action,
            "cv": metrics_2.model_dump(),
            "llm": decision_2.model_dump()
        })

        conf_delta = round(decision_2.confidence - decision_1.confidence, 3)

        # Strictly output ESCALATE_HUMAN_REVIEW or UNRESOLVED_LOW_CONFIDENCE
        if decision_2.confidence >= 0.70:
            final_status = "ESCALATE_HUMAN_REVIEW"
        else:
            final_status = "UNRESOLVED_LOW_CONFIDENCE"

        # Ensure trace entries are plain dictionaries matching schema
        trace_dicts = [s if isinstance(s, dict) else s.model_dump() for s in trace]

        return InspectionResponse(
            incident_id=inc_id,
            final_status=final_status,
            action_taken=action,
            confidence_delta=conf_delta,
            trace=trace_dicts,
            metrics_summary=metrics_2.model_dump(),
            visual_evidence=visual_evidence
        )