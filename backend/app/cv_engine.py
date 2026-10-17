import cv2
import numpy as np
import time
import base64
from typing import Tuple, List, Optional
from .schemas import OpenCVMetrics

class SwarmCVEngine:
    """
    Deterministic Computer Vision Engine for SwarmTwin.
    Performs pixel mathematics, geometric homography, CLAHE contrast equalization,
    and Farneback dense optical flow.
    Designed for OpenCV 5 with Arm KleidiCV acceleration on AWS Graviton4.
    """
    def __init__(self):
        self.orb = cv2.ORB_create(nfeatures=2000)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

    @staticmethod
    def encode_base64(img: np.ndarray, quality: int = 85) -> str:
        """Helper to convert BGR image to JPEG base64 data string."""
        _, buffer = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        return base64.b64encode(buffer).decode("utf-8")

    def analyze_frame(self, img: np.ndarray) -> Tuple[np.ndarray, OpenCVMetrics]:
        """
        Executes baseline geometric and radiometric assessment:
        1. Adaptive Gaussian Thresholding (KleidiCV accelerated on ARM)
        2. Canny Edge Density & Flood/Debris Contour Area
        3. Glare/Shadow Ambiguity Index
        """
        t0 = time.perf_counter()
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. Adaptive Gaussian Thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 4
        )

        # 2. Canny edge detection + Contour filtering
        edges = cv2.Canny(gray, 60, 160)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        large_contours = [c for c in contours if cv2.contourArea(c) > 300]
        contour_area = sum(cv2.contourArea(c) for c in large_contours)

        # 3. Glare / deep shadow ambiguity index
        glare_shadow_mask = (gray > 240) | (gray < 25)
        glare_ratio = float(np.sum(glare_shadow_mask)) / float(h * w)

        annotated = img.copy()
        cv2.drawContours(annotated, large_contours, -1, (0, 255, 255), 2)

        # Draw visual HUD on annotated frame
        hud_text = f"Flood Area: {round(contour_area / (h * w) * 100, 1)}% | Glare: {round(glare_ratio * 100, 1)}%"
        cv2.putText(annotated, hud_text, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

        dt_ms = (time.perf_counter() - t0) * 1000.0
        metrics = OpenCVMetrics(
            flood_contour_ratio=round(contour_area / (h * w), 4),
            edge_density=round(float(np.count_nonzero(edges)) / (h * w), 4),
            glare_or_shadow_ratio=round(glare_ratio, 4),
            homography_inliers=0,
            motion_flow_magnitude=0.0,
            execution_time_ms=round(dt_ms, 2),
        )
        return annotated, metrics

    def enhance_roi_clahe(self, img: np.ndarray, roi: List[float]) -> np.ndarray:
        """
        Applies Contrast Limited Adaptive Histogram Equalization (CLAHE) on target ROI
        in the CIE LAB color space to penetrate solar glare without color distortion.
        Returns the full-frame composite with the enhanced ROI blended in.
        """
        h, w = img.shape[:2]
        x1, y1, x2, y2 = [int(roi[0] * w), int(roi[1] * h), int(roi[2] * w), int(roi[3] * h)]
        crop = img[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        if crop.size == 0 or crop.shape[0] < 5 or crop.shape[1] < 5:
            crop = img.copy()
            x1, y1, x2, y2 = 0, 0, w, h

        # Convert to LAB color space for luminance equalization without color distortion
        lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_eq = clahe.apply(l)
        enhanced_crop = cv2.cvtColor(cv2.merge((l_eq, a, b)), cv2.COLOR_LAB2BGR)

        # Create composite with cyan targeting boundary
        composite = img.copy()
        composite[max(0, y1):min(h, y2), max(0, x1):min(w, x2)] = enhanced_crop
        cv2.rectangle(composite, (max(0, x1), max(0, y1)), (min(w, x2), min(h, y2)), (255, 255, 0), 2)
        cv2.putText(composite, "CLAHE ENHANCED ROI", (max(0, x1) + 5, max(20, max(0, y1) - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)
        return composite

    def register_alternate_viewpoint(self, img_a: np.ndarray, img_b: np.ndarray) -> Tuple[np.ndarray, int]:
        """
        Aligns Drone B (oblique viewpoint) to Drone A (nadir coordinate space)
        using ORB feature matching and cv2.USAC_MAGSAC homography estimation.
        Returns:
            warped_view: Drone B perspective-warped into Drone A frame coordinates
            inliers: Number of geometrically verified inlier matches
        """
        kp1, des1 = self.orb.detectAndCompute(img_a, None)
        kp2, des2 = self.orb.detectAndCompute(img_b, None)
        if des1 is None or des2 is None or len(des1) < 4 or len(des2) < 4:
            return img_b, 0

        matches = self.bf.knnMatch(des1, des2, k=2)
        good = [m for m, n in matches if m.distance < 0.75 * n.distance]
        if len(good) < 10:
            return img_b, len(good)

        src_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)

        # USAC_MAGSAC is the recommended modern robust estimator in OpenCV 5
        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.USAC_MAGSAC, 5.0)
        inliers = int(np.sum(mask)) if mask is not None else 0
        h, w = img_a.shape[:2]
        warped = cv2.warpPerspective(img_b, H, (w, h)) if H is not None else img_b
        return warped, inliers

    def compute_optical_flow(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Calculates Farneback dense optical flow across consecutive frames to detect
        active flood surges, flowing debris, or static stranded objects.
        Returns:
            flow_vis_bgr: HSV-colored optical flow direction and magnitude map
            avg_magnitude: Mean pixel displacement per frame
        """
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
        )
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        hsv = np.zeros_like(prev_frame)
        hsv[..., 1] = 255
        hsv[..., 0] = (ang * 180 / np.pi / 2).astype(np.uint8)
        hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        bgr_flow = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        avg_magnitude = float(np.mean(mag))

        # Add motion status banner
        status = "DYNAMIC SURGE DETECTED" if avg_magnitude > 2.0 else "STATIC / SLOW MOVEMENT"
        color = (0, 0, 255) if avg_magnitude > 2.0 else (0, 255, 0)
        cv2.putText(bgr_flow, f"{status} (Avg Mag: {avg_magnitude:.2f} px)", (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        return bgr_flow, avg_magnitude
