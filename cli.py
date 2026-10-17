#!/usr/bin/env python3
"""
SwarmTwin CLI: Agentic Computer Vision Triage Engine for Drone Disaster Imagery.
Processes FloodNet aerial data through the 3-phase deterministic state machine:
  Phase 1 (Initial Perception) -> Phase 2 (Action Execution) -> Phase 3 (Verification)

Outputs:
  1. Strict JSON Trace (InspectionResponse schema)
  2. Annotated Visual Evidence images saved to disk
"""

import os
import sys
import argparse
import json
import base64
import cv2
import numpy as np

# Ensure root SwarmTwin is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app.schemas import InspectionResponse
from backend.app.cv_engine import SwarmCVEngine
from backend.app.nim_reasoner import NimVisionReasoner
from backend.app.agent_fsm import SwarmTwinAgent
from backend.app.floodnet_loader import (
    load_floodnet_image,
    list_floodnet_images,
    get_curated_floodnet_samples,
    create_synthetic_alternate_view,
    create_synthetic_temporal_surge
)

def save_visual_evidence(response: InspectionResponse, output_dir: str) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    saved_files = {}

    inc_id = response.incident_id

    # 1. Initial annotated frame (yellow contours + HUD)
    if response.visual_evidence.initial_annotated_base64:
        init_bytes = base64.b64decode(response.visual_evidence.initial_annotated_base64)
        init_path = os.path.join(output_dir, f"{inc_id}_initial_annotated.jpg")
        with open(init_path, "wb") as f:
            f.write(init_bytes)
        saved_files["initial_annotated"] = init_path

    # 2. Post-action annotated frame
    if response.visual_evidence.post_action_annotated_base64:
        post_bytes = base64.b64decode(response.visual_evidence.post_action_annotated_base64)
        post_path = os.path.join(output_dir, f"{inc_id}_post_action_annotated.jpg")
        with open(post_path, "wb") as f:
            f.write(post_bytes)
        saved_files["post_action_annotated"] = post_path

    # 3. Homography warped view
    if response.visual_evidence.homography_warped_base64:
        homo_bytes = base64.b64decode(response.visual_evidence.homography_warped_base64)
        homo_path = os.path.join(output_dir, f"{inc_id}_homography_warped.jpg")
        with open(homo_path, "wb") as f:
            f.write(homo_bytes)
        saved_files["homography_warped"] = homo_path

    # 4. Optical flow map
    if response.visual_evidence.flow_visualization_base64:
        flow_bytes = base64.b64decode(response.visual_evidence.flow_visualization_base64)
        flow_path = os.path.join(output_dir, f"{inc_id}_optical_flow.jpg")
        with open(flow_path, "wb") as f:
            f.write(flow_bytes)
        saved_files["optical_flow"] = flow_path

    return saved_files

def main():
    parser = argparse.ArgumentParser(
        description="SwarmTwin Drone Disaster Vision Triage CLI (OpenCV 5 + Llama 3.2 90B Vision)"
    )
    parser.add_argument("--image", "-i", type=str, help="Path to primary aerial frame (JPEG/PNG)")
    parser.add_argument("--floodnet", "-f", type=str, help="FloodNet validation image ID (e.g. 10169, 10173, 10177)")
    parser.add_argument("--alt-view", type=str, help="Path to secondary oblique viewpoint (Drone B)")
    parser.add_argument("--temporal", type=str, help="Path to consecutive burst frame for optical flow")
    parser.add_argument("--scenario", "-s", choices=["glare_flood", "occluded_vehicle", "flash_flood_surge"],
                        help="Quick hackathon benchmark scenario")
    parser.add_argument("--output-dir", "-o", type=str, default="output/evidence",
                        help="Directory to save visual evidence frames (default: output/evidence)")
    parser.add_argument("--json-only", action="store_true", help="Print strict JSON InspectionResponse without terminal formatting")
    parser.add_argument("--list-floodnet", action="store_true", help="List available curated FloodNet reference images")
    parser.add_argument("--incident-id", type=str, help="Custom incident identifier (e.g. INC-1234)")
    parser.add_argument("--action", choices=["ENHANCE_ROI_CONTRAST", "REQUEST_ALTERNATE_VIEWPOINT", "COMPUTE_OPTICAL_FLOW_SURGE"],
                        help="Explicitly force a specific OpenCV state machine tool")
    
    args = parser.parse_args()

    # List FloodNet samples
    if args.list_floodnet:
        samples = get_curated_floodnet_samples()
        all_imgs = list_floodnet_images()
        print(f"\n=== FloodNet Dataset: {len(all_imgs)} images found ===")
        print("Curated Reference Samples for SwarmTwin State Machine:")
        for s in samples:
            print(f"  [{s['sample_id']}] {s['title']}")
            print(f"      Target Action: {s['target_action']}")
            print(f"      Description:   {s['description']}\n")
        sys.exit(0)

    # Initialize Engine
    cv_engine = SwarmCVEngine()
    reasoner = NimVisionReasoner()
    agent = SwarmTwinAgent(cv_engine, reasoner)

    # Load Frames
    primary_img = None
    alt_img = None
    temporal_img = None
    source_desc = ""

    if args.floodnet:
        primary_img, path = load_floodnet_image(args.floodnet)
        source_desc = f"FloodNet Image ID: {args.floodnet} ({path})"
    elif args.scenario:
        data_dir = os.path.join(os.path.dirname(__file__), "data", "sample_incident")
        if args.scenario == "glare_flood":
            p = os.path.join(data_dir, "scenario_a_glare_flood.jpg")
            primary_img = cv2.imread(p)
            source_desc = "Benchmark Scenario Alpha: Specular Glare (CLAHE)"
        elif args.scenario == "occluded_vehicle":
            p1 = os.path.join(data_dir, "scenario_b_drone_a_nadir.jpg")
            p2 = os.path.join(data_dir, "scenario_b_drone_b_oblique.jpg")
            primary_img = cv2.imread(p1)
            alt_img = cv2.imread(p2)
            source_desc = "Benchmark Scenario Bravo: Canopy Occlusion (USAC_MAGSAC)"
        elif args.scenario == "flash_flood_surge":
            p1 = os.path.join(data_dir, "scenario_c_flow_t0.jpg")
            p2 = os.path.join(data_dir, "scenario_c_flow_t1.jpg")
            primary_img = cv2.imread(p1)
            temporal_img = cv2.imread(p2)
            source_desc = "Benchmark Scenario Charlie: Flash Flood Surge (Optical Flow)"
    elif args.image:
        if not os.path.exists(args.image):
            print(f"Error: Primary frame not found at {args.image}", file=sys.stderr)
            sys.exit(1)
        primary_img = cv2.imread(args.image)
        source_desc = f"Local File: {args.image}"
        if args.alt_view and os.path.exists(args.alt_view):
            alt_img = cv2.imread(args.alt_view)
        if args.temporal and os.path.exists(args.temporal):
            temporal_img = cv2.imread(args.temporal)
    else:
        # Default to FloodNet reference 10169
        primary_img, path = load_floodnet_image("10169")
        source_desc = "FloodNet Default Reference 10169 (Submerged Roadway)"

    if primary_img is None:
        print("Error: Could not load valid image. Use --image, --floodnet, or --scenario.", file=sys.stderr)
        sys.exit(1)

    # Determine forced action if preset or flag specified
    force_act = args.action
    if not force_act and args.floodnet:
        if args.floodnet in ("10169",):
            force_act = "ENHANCE_ROI_CONTRAST"
        elif args.floodnet in ("10173", "10178"):
            force_act = "REQUEST_ALTERNATE_VIEWPOINT"
        elif args.floodnet in ("10177", "10809"):
            force_act = "COMPUTE_OPTICAL_FLOW_SURGE"

    # Execute Agentic Inspection Episode
    response = agent.run_inspection_episode(
        primary_frame=primary_img,
        alt_view_frame=alt_img,
        temporal_frame=temporal_img,
        incident_id=args.incident_id,
        force_action=force_act
    )

    # Save visual evidence
    saved_files = save_visual_evidence(response, args.output_dir)

    # Strict JSON Output
    if args.json_only:
        print(response.model_dump_json(indent=2))
        return

    # Rich Terminal Output
    print("\n" + "=" * 76)
    print("  SWARMTWIN DISASTER TRIAGE - AGENTIC VISION STATE MACHINE")
    print("=" * 76)
    print(f"  Incident ID:       {response.incident_id}")
    status_color = "\033[91m" if response.final_status == "ESCALATE_HUMAN_REVIEW" else "\033[94m"
    print(f"  Final Verdict:     {status_color}{response.final_status}\033[0m")
    print(f"  Action Executed:   {response.action_taken or 'NONE (TERMINAL)'}")
    print(f"  Confidence Gain:   +{response.confidence_delta:.3f}")
    print(f"  Source Input:      {source_desc}")
    print("-" * 76)

    print("\n[STRICT JSON TRACE - EXECUTION AUDIT TRAIL]")
    for step in response.trace:
        print(f"\n  --> STEP {step.step}: {step.phase}")
        if step.action_taken:
            print(f"      Action Taken:       {step.action_taken}")
        print("      OpenCV Metrics:")
        print(f"        - Flood Contour Ratio:  {step.cv.get('flood_contour_ratio', 0.0):.4f}")
        print(f"        - Edge Density:         {step.cv.get('edge_density', 0.0):.4f}")
        print(f"        - Glare/Shadow Ratio:   {step.cv.get('glare_or_shadow_ratio', 0.0):.4f}")
        if step.cv.get('homography_inliers', 0) > 0:
            print(f"        - Homography Inliers:   {step.cv.get('homography_inliers')}")
        if step.cv.get('motion_flow_magnitude', 0.0) > 0.0:
            print(f"        - Optical Flow Mag:     {step.cv.get('motion_flow_magnitude'):.2f} px/frame")
        print(f"        - CV Execution Latency: {step.cv.get('execution_time_ms', 0.0):.2f} ms")

        print("      Llama 3.2 Vision Structured Reasoning:")
        print(f"        - Observed Hazard:      {step.llm.get('observed_hazard')}")
        print(f"        - Confidence Score:     {step.llm.get('confidence'):.2f}")
        print(f"        - Uncertainty Reason:   {step.llm.get('uncertainty_reason')}")
        print(f"        - Next Tool / Action:   {step.llm.get('recommended_action')}")
        print(f"        - Evidence Needed:      {step.llm.get('evidence_needed')}")
        print(f"        - Target ROI:           {step.llm.get('target_roi_normalized')}")

    print("\n" + "-" * 76)
    print("[ANNOTATED VISUAL EVIDENCE SAVED TO DISK]")
    for label, filepath in saved_files.items():
        print(f"  [+] {label.replace('_', ' ').title()}:")
        print(f"      -> {os.path.abspath(filepath)}")

    print("=" * 76 + "\n")

if __name__ == "__main__":
    main()