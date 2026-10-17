import pytest
import numpy as np
import cv2
import os

from backend.app.schemas import OpenCVMetrics, LlamaReasoningResult, InspectionResponse
from backend.app.cv_engine import SwarmCVEngine
from backend.app.nim_reasoner import NimVisionReasoner
from backend.app.agent_fsm import SwarmTwinAgent

@pytest.fixture
def cv_engine():
    return SwarmCVEngine()

@pytest.fixture
def reasoner(tmp_path):
    cache_file = os.path.join(tmp_path, "test_cache.db")
    return NimVisionReasoner(cache_path=cache_file)

@pytest.fixture
def agent(cv_engine, reasoner):
    return SwarmTwinAgent(cv_engine, reasoner)

def test_cv_engine_analyze_frame(cv_engine):
    h, w = 480, 640
    frame = np.full((h, w, 3), 120, dtype=np.uint8)
    # Add high-contrast flood contour
    cv2.circle(frame, (320, 240), 100, (20, 20, 20), -1)

    annotated, metrics = cv_engine.analyze_frame(frame)
    assert annotated.shape == (h, w, 3)
    assert isinstance(metrics, OpenCVMetrics)
    assert metrics.flood_contour_ratio >= 0.0
    assert metrics.edge_density >= 0.0
    assert metrics.glare_or_shadow_ratio >= 0.0
    assert metrics.execution_time_ms > 0.0

def test_cv_engine_enhance_roi_clahe(cv_engine):
    h, w = 480, 640
    frame = np.random.randint(50, 200, (h, w, 3), dtype=np.uint8)
    roi = [0.25, 0.25, 0.75, 0.75]

    composite = cv_engine.enhance_roi_clahe(frame, roi)
    assert isinstance(composite, np.ndarray)
    assert composite.shape == (h, w, 3)

def test_cv_engine_register_alternate_viewpoint(cv_engine):
    h, w = 480, 640
    img_a = np.full((h, w, 3), 128, dtype=np.uint8)
    # Draw rich feature grid for ORB
    for r in range(5):
        for c in range(8):
            cv2.rectangle(img_a, (c * 75 + 10, r * 90 + 10), (c * 75 + 50, r * 90 + 60), (30, 30, 30), -1)
            cv2.circle(img_a, (c * 75 + 30, r * 90 + 35), 8, (220, 220, 220), -1)

    # Perspective warp to simulate Drone B oblique angle
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[30, 15], [w - 35, 10], [w - 15, h - 20], [15, h - 15]])
    H = cv2.getPerspectiveTransform(src, dst)
    img_b = cv2.warpPerspective(img_a, H, (w, h))

    warped, inliers = cv_engine.register_alternate_viewpoint(img_a, img_b)
    assert isinstance(warped, np.ndarray)
    assert warped.shape == (h, w, 3)
    assert inliers >= 4

def test_cv_engine_compute_optical_flow(cv_engine):
    h, w = 480, 640
    frame1 = np.zeros((h, w, 3), dtype=np.uint8)
    cv2.circle(frame1, (300, 240), 50, (255, 255, 255), -1)

    frame2 = np.zeros((h, w, 3), dtype=np.uint8)
    # Shift circle by 15 pixels to simulate flow
    cv2.circle(frame2, (315, 240), 50, (255, 255, 255), -1)

    flow_vis, avg_mag = cv_engine.compute_optical_flow(frame1, frame2)
    assert isinstance(flow_vis, np.ndarray)
    assert flow_vis.shape == (h, w, 3)
    assert avg_mag > 0.0

def test_agent_fsm_glare_clahe_branch(agent):
    h, w = 480, 640
    # Create frame with heavy specular glare (> 240)
    frame = np.full((h, w, 3), 100, dtype=np.uint8)
    cv2.circle(frame, (320, 240), 160, (250, 250, 250), -1)

    response = agent.run_inspection_episode(frame)
    assert isinstance(response, InspectionResponse)
    assert response.action_taken == "ENHANCE_ROI_CONTRAST"
    assert len(response.trace) == 2
    
    # Verify trace schema integrity
    step1 = response.trace[0]
    step2 = response.trace[1]
    assert step1["step"] == 1
    assert step1["phase"] == "INITIAL_PERCEPTION"
    assert "cv" in step1 and "llm" in step1
    assert step2["step"] == 2
    assert step2["phase"] == "VERIFICATION_AFTER_ACTION"
    assert step2["action_taken"] == "ENHANCE_ROI_CONTRAST"
    assert response.final_status == "ESCALATE_HUMAN_REVIEW"
    
    # Dict-like indexing support
    assert response["final_status"] == response.final_status
    assert len(response["trace"]) == 2

def test_agent_fsm_alternate_viewpoint_branch(agent):
    h, w = 480, 640
    img_a = np.full((h, w, 3), 128, dtype=np.uint8)
    # Rich grid of patterns with high edge density
    for r in range(6):
        for c in range(10):
            cv2.rectangle(img_a, (c * 60 + 5, r * 75 + 5), (c * 60 + 45, r * 75 + 55), (35, 35, 35), -1)
            cv2.circle(img_a, (c * 60 + 25, r * 75 + 30), 10, (215, 215, 215), -1)

    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[30, 15], [w - 35, 10], [w - 15, h - 20], [15, h - 15]])
    H = cv2.getPerspectiveTransform(src, dst)
    img_b = cv2.warpPerspective(img_a, H, (w, h))

    response = agent.run_inspection_episode(img_a, alt_view_frame=img_b)
    assert response.action_taken == "REQUEST_ALTERNATE_VIEWPOINT"
    assert len(response.trace) == 2
    assert response.trace[1]["cv"]["homography_inliers"] >= 4
    assert response.final_status == "ESCALATE_HUMAN_REVIEW"

def test_agent_fsm_optical_flow_surge_branch(agent):
    h, w = 480, 640
    # Neutral background
    frame1 = np.full((h, w, 3), 120, dtype=np.uint8)
    # Flood channel with moving ripples
    cv2.rectangle(frame1, (0, 80), (w, 400), (40, 40, 30), -1)
    for x in range(40, w, 50):
        cv2.circle(frame1, (x, 240), 18, (200, 200, 200), -1)

    frame2 = frame1.copy()
    cv2.rectangle(frame2, (0, 80), (w, 400), (40, 40, 30), -1)
    for x in range(40, w, 50):
        cv2.circle(frame2, (x + 16, 240), 18, (200, 200, 200), -1)

    response = agent.run_inspection_episode(frame1, temporal_frame=frame2)
    assert response.action_taken == "COMPUTE_OPTICAL_FLOW_SURGE"
    assert len(response.trace) == 2
    assert response.trace[1]["cv"]["motion_flow_magnitude"] > 0.0

def test_nim_reasoner_cache_hit(reasoner):
    frame = np.full((100, 100, 3), 128, dtype=np.uint8)
    metrics = OpenCVMetrics(
        flood_contour_ratio=0.1,
        edge_density=0.05,
        glare_or_shadow_ratio=0.02,
        execution_time_ms=5.0
    )

    res1 = reasoner.reason_on_frame(frame, metrics, "Step 1 test")
    res2 = reasoner.reason_on_frame(frame, metrics, "Step 1 test")
    assert res1.observed_hazard == res2.observed_hazard
    assert res1.confidence == res2.confidence
    assert isinstance(res1, LlamaReasoningResult)
