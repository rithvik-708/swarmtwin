import os
import cv2
import numpy as np

def generate_sample_disaster_datasets(output_dir: str = "data/sample_incident"):
    os.makedirs(output_dir, exist_ok=True)
    h, w = 720, 1280

    print(f"Generating synthetic disaster aerial datasets in '{output_dir}'...")

    # -------------------------------------------------------------------------
    # Scenario A: Specular Solar Glare over Flooded Roadway & Stranded Vehicle
    # -------------------------------------------------------------------------
    img_a = np.zeros((h, w, 3), dtype=np.uint8)
    # Background terrain (olive/brown muddy earth)
    img_a[:] = (45, 65, 80)
    # Flooded road channel (murky dark brown/blue flood water)
    cv2.rectangle(img_a, (150, 0), (1130, h), (90, 85, 60), -1)
    # Submerged road markings (dashed yellow line)
    for y in range(0, h, 60):
        cv2.rectangle(img_a, (635, y), (645, y + 35), (20, 160, 180), -1)

    # Road edges and debris contours
    for _ in range(35):
        cx = np.random.randint(200, 1080)
        cy = np.random.randint(50, 670)
        radius = np.random.randint(15, 45)
        cv2.circle(img_a, (cx, cy), radius, (50, 45, 30), -1)

    # Submerged vehicle roof (partially visible)
    car_x1, car_y1, car_x2, car_y2 = 560, 310, 720, 410
    cv2.rectangle(img_a, (car_x1, car_y1), (car_x2, car_y2), (180, 40, 30), -1) # Red vehicle
    cv2.rectangle(img_a, (car_x1 + 25, car_y1 + 15), (car_x2 - 25, car_y2 - 15), (70, 70, 70), -1) # Windshield

    # Intense specular solar glare spot over the vehicle ROI
    # Glare creates pixels with value > 240 triggering glare_ratio > 0.16
    glare_mask = np.zeros((h, w), dtype=np.float32)
    cv2.circle(glare_mask, (640, 360), 220, 1.0, -1)
    glare_mask = cv2.GaussianBlur(glare_mask, (101, 101), 40)
    glare_rgb = np.repeat((glare_mask * 230)[:, :, np.newaxis], 3, axis=2).astype(np.uint8)
    img_a_glare = cv2.add(img_a, glare_rgb)

    cv2.imwrite(os.path.join(output_dir, "scenario_a_glare_flood.jpg"), img_a_glare)
    print(" -> Generated Scenario A: scenario_a_glare_flood.jpg (Specular Glare)")

    # -------------------------------------------------------------------------
    # Scenario B: Canopy Occlusion (Drone A Nadir vs Drone B Oblique View)
    # -------------------------------------------------------------------------
    # Base town scene with distinct geometric landmarks for ORB matching
    base_b = np.zeros((h, w, 3), dtype=np.uint8)
    base_b[:] = (55, 75, 50) # Grassy background

    # Concrete road intersection
    cv2.rectangle(base_b, (0, 300), (w, 420), (120, 120, 120), -1)
    cv2.rectangle(base_b, (580, 0), (700, h), (120, 120, 120), -1)

    # Distinct buildings (sharp corners for feature matching)
    buildings = [
        (100, 100, 260, 240, (180, 150, 140)),
        (320, 80, 480, 220, (140, 170, 190)),
        (800, 90, 980, 250, (160, 140, 170)),
        (1040, 120, 1200, 260, (190, 180, 150)),
        (120, 480, 300, 660, (150, 160, 180)),
        (850, 460, 1050, 640, (170, 150, 140)),
    ]
    for bx1, by1, bx2, by2, col in buildings:
        cv2.rectangle(base_b, (bx1, by1), (bx2, by2), col, -1)
        cv2.rectangle(base_b, (bx1, by1), (bx2, by2), (40, 40, 40), 3) # Sharp border

    # Add high-frequency textures for rich ORB descriptors
    for _ in range(80):
        tx = np.random.randint(50, w - 50)
        ty = np.random.randint(50, h - 50)
        cv2.circle(base_b, (tx, ty), 4, (200, 200, 200), -1)

    drone_a_nadir = base_b.copy()

    # In Drone A (Nadir), vehicle is occluded by fallen tree canopy
    # Draw trapped blue truck at center intersection
    cv2.rectangle(drone_a_nadir, (610, 330), (670, 390), (190, 80, 20), -1)
    # Canopy foliage completely covers it from above
    for _ in range(45):
        fx = np.random.randint(590, 690)
        fy = np.random.randint(310, 410)
        cv2.circle(drone_a_nadir, (fx, fy), np.random.randint(18, 36), (25, 110, 35), -1)

    cv2.imwrite(os.path.join(output_dir, "scenario_b_drone_a_nadir.jpg"), drone_a_nadir)
    print(" -> Generated Scenario B: scenario_b_drone_a_nadir.jpg (Canopy Occlusion)")

    # In Drone B (Oblique), drone is viewing at an angle
    # Create homography perspective warp of the base environment
    src_corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    # Tilted oblique camera matrix
    dst_corners = np.float32([[90, 60], [w - 120, 30], [w - 40, h - 50], [40, h - 30]])
    H_sim = cv2.getPerspectiveTransform(src_corners, dst_corners)
    drone_b_oblique = cv2.warpPerspective(base_b, H_sim, (w, h))

    # In Drone B oblique view, the camera looks under the angled canopy,
    # clearly revealing the trapped truck's cabin and hazard markings
    truck_oblique_center = cv2.perspectiveTransform(
        np.float32([[[640, 360]]]), H_sim
    )[0][0].astype(int)
    tx, ty = int(truck_oblique_center[0]), int(truck_oblique_center[1])

    # Visible truck cabin and hazard warning beacon
    cv2.rectangle(drone_b_oblique, (tx - 35, ty - 25), (tx + 35, ty + 25), (220, 110, 30), -1)
    cv2.circle(drone_b_oblique, (tx, ty), 12, (0, 255, 255), -1) # Flashing beacon
    cv2.putText(drone_b_oblique, "TRUCK DETECTED", (tx - 60, ty - 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

    cv2.imwrite(os.path.join(output_dir, "scenario_b_drone_b_oblique.jpg"), drone_b_oblique)
    print(" -> Generated Scenario B: scenario_b_drone_b_oblique.jpg (Oblique Viewpoint)")

    # -------------------------------------------------------------------------
    # Scenario C: Dynamic Flash Flood Surge (Frame t0 vs Frame t1)
    # -------------------------------------------------------------------------
    flow_t0 = np.zeros((h, w, 3), dtype=np.uint8)
    flow_t0[:] = (60, 80, 65) # Riverbanks (static)
    # Center flood channel
    cv2.rectangle(flow_t0, (0, 180), (w, 540), (140, 110, 60), -1)

    # Static buildings on banks
    for x in range(80, w, 180):
        cv2.rectangle(flow_t0, (x, 40), (x + 110, 150), (170, 160, 150), -1)
        cv2.rectangle(flow_t0, (x, 570), (x + 110, 680), (150, 140, 170), -1)

    # High-texture flood water waves and debris (moving along x-axis)
    np.random.seed(42)
    debris_coords = []
    for _ in range(120):
        dx = np.random.randint(0, w)
        dy = np.random.randint(200, 520)
        dr = np.random.randint(6, 18)
        color = (np.random.randint(80, 210), np.random.randint(70, 180), np.random.randint(30, 120))
        debris_coords.append((dx, dy, dr, color))
        cv2.circle(flow_t0, (dx, dy), dr, color, -1)

    # Frame t1: Riverbanks and buildings stay completely static,
    # water and debris surge forward by 8-14 pixels downstream
    flow_t1 = flow_t0.copy()
    # Redraw water channel with shifted wave ripples
    cv2.rectangle(flow_t1, (0, 180), (w, 540), (140, 110, 60), -1)
    displacement = 12
    for dx, dy, dr, color in debris_coords:
        new_dx = (dx + displacement) % w
        cv2.circle(flow_t1, (new_dx, dy), dr, color, -1)

    cv2.imwrite(os.path.join(output_dir, "scenario_c_flow_t0.jpg"), flow_t0)
    cv2.imwrite(os.path.join(output_dir, "scenario_c_flow_t1.jpg"), flow_t1)
    print(" -> Generated Scenario C: scenario_c_flow_t0.jpg & scenario_c_flow_t1.jpg (Flash Flood Surge)")

    print(f"All sample datasets generated successfully in '{output_dir}'.")

if __name__ == "__main__":
    generate_sample_disaster_datasets()
