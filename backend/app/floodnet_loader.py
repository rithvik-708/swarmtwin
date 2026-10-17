import os
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

FLOODNET_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'FloodNet', 'FloodNet-Supervised_v1.0', 'val', 'val-org-img'
))

def get_floodnet_dir() -> str:
    if os.path.isdir(FLOODNET_DIR):
        return FLOODNET_DIR
    alt = os.path.abspath(os.path.join(os.getcwd(), 'FloodNet', 'FloodNet-Supervised_v1.0', 'val', 'val-org-img'))
    if os.path.isdir(alt):
        return alt
    return FLOODNET_DIR

def list_floodnet_images() -> List[str]:
    d = get_floodnet_dir()
    if not os.path.exists(d):
        return []
    files = [f for f in os.listdir(d) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    return sorted(files)

def load_floodnet_image(image_id_or_filename: str, max_dim: int = 1280) -> Tuple[np.ndarray, str]:
    d = get_floodnet_dir()
    name = image_id_or_filename if '.' in image_id_or_filename else f'{image_id_or_filename}.jpg'
    path = os.path.join(d, name)
    if not os.path.exists(path):
        if os.path.exists(image_id_or_filename):
            path = image_id_or_filename
        else:
            raise FileNotFoundError(f'FloodNet image not found: {path}')

    img = cv2.imread(path)
    if img is None:
        raise ValueError(f'Could not decode image at {path}')

    h, w = img.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    return img, path

def create_synthetic_alternate_view(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([
        [w * 0.04, h * 0.03],
        [w * 0.96, h * 0.02],
        [w * 0.92, h * 0.96],
        [w * 0.08, h * 0.97]
    ])
    H = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, H, (w, h), borderMode=cv2.BORDER_REFLECT)
    return warped

def create_synthetic_temporal_surge(img: np.ndarray, shift_px: float = 8.0) -> np.ndarray:
    h, w = img.shape[:2]
    y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)
    flow_x = x_coords - shift_px - (np.sin(y_coords / 25.0) * 2.5).astype(np.float32)
    flow_y = y_coords - (shift_px * 0.6) - (np.cos(x_coords / 35.0) * 2.0).astype(np.float32)
    flow_x = np.clip(flow_x, 0, w - 1)
    flow_y = np.clip(flow_y, 0, h - 1)
    temporal_frame = cv2.remap(img, flow_x, flow_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return temporal_frame

def get_curated_floodnet_samples() -> List[Dict[str, Any]]:
    return [
        {
            'sample_id': '10169',
            'title': 'FloodNet 10169: Submerged Residential Road (Glare & Specular Reflection)',
            'description': 'Severe specular glare over murky water surfaces obscure structural boundaries of roads and driveways. Triggers LAB-CLAHE contrast equalization on target ROI.',
            'target_action': 'ENHANCE_ROI_CONTRAST',
            'has_mask': True,
            'default_alt_view': False,
            'default_temporal': False
        },
        {
            'sample_id': '10173',
            'title': 'FloodNet 10173: Dense Debris & Canopy Occlusion (Multi-View Alignment)',
            'description': 'Heavy tree canopy and collapsed structural debris occlude ground vehicles. Triggers Drone B oblique viewpoint alignment via USAC_MAGSAC homography.',
            'target_action': 'REQUEST_ALTERNATE_VIEWPOINT',
            'has_mask': True,
            'default_alt_view': True,
            'default_temporal': False
        },
        {
            'sample_id': '10177',
            'title': 'FloodNet 10177: Active Inundation Basin (Optical Flow Surge Vectoring)',
            'description': 'Extensive floodwater accumulation covering residential parcels. Triggers Farneback dense optical flow across burst frames to measure motion flow magnitude.',
            'target_action': 'COMPUTE_OPTICAL_FLOW_SURGE',
            'has_mask': True,
            'default_alt_view': False,
            'default_temporal': True
        }
    ]