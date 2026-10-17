<div align="center">

<img src="./public/logo.svg" alt="SwarmTwin Logo" width="90" height="90" />

# SwarmTwin Control Room

### Multi-Drone Agentic Aerial Disaster Triage Dashboard
**Next.js 16 (Turbopack) & Tailwind CSS v4 Control Room for AWS Graviton4 + Llama 3.2 90B Vision**

[![Next.js 16](https://img.shields.io/badge/Next.js-16_Turbopack-000000.svg?style=flat&logo=next.js&logoColor=white)](https://nextjs.org)
[![React 19](https://img.shields.io/badge/React-19.3.0-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://react.dev)
[![Tailwind CSS v4](https://img.shields.io/badge/Tailwind_CSS-v4.0-06B6D4.svg?style=flat&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![FastAPI Backend](https://img.shields.io/badge/API-FastAPI_v1.1-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![OpenCV 5](https://img.shields.io/badge/Engine-OpenCV_5_COOL-5C3EE8.svg?style=flat&logo=opencv&logoColor=white)](https://opencv.org)

</div>

---

## 🎯 Product Overview

**SwarmTwin Control Room** is the mission-critical human-in-the-loop (HITL) interface designed for disaster coordinators, emergency managers, and drone swarm operators. It connects front-line responders with SwarmTwin's autonomous **Perception $\rightarrow$ Decision $\rightarrow$ Action $\rightarrow$ Verification** triage pipeline.

During catastrophic disasters (flash floods, hurricanes, collapsed infrastructure), drone feeds are overwhelmed by glare, canopy occlusion, and ambiguous flood motion. This Control Room empowers dispatchers to visualize ground-truth mathematical transformations, audit multimodal LLM decisions, and approve rescue operations with verifiable confidence.

---

## 🚀 Key Product Features

### 1. Multi-Drone Multi-Frame Ingestion
- **Primary Nadir Feed (Drone A):** High-resolution top-down aerial imagery for baseline geographic and geometric assessment.
- **Secondary Oblique Feed (Drone B):** Angled perspectives ingested autonomously or manually to look under fallen trees and structural canopies.
- **Temporal Burst Frame:** Consecutive temporal video frames for dense optical flow surge vectoring.

### 2. Direct FloodNet Challenge Integration
- Built-in support for the **FloodNet Dataset** (1,895+ high-resolution drone disaster frames).
- **One-Click Presets:**
  - **FloodNet 10169:** Submerged residential roadway obscured by specular water reflection $\rightarrow$ Triggers **OpenCV LAB-CLAHE**.
  - **FloodNet 10173:** Canopy debris and foliage occlusion $\rightarrow$ Triggers **`USAC_MAGSAC` Multi-View Homography**.
  - **FloodNet 10177:** Active floodwater accumulation basin $\rightarrow$ Triggers **Farnebäck Dense Optical Flow**.
- **Direct ID Inspector:** Type any sample ID (e.g., `10809`, `6331`, `6428`) to instantly fetch and triage real drone frames.

### 3. Visual Evidence HUD & Inspection Tabs
- **Post-Action Enhanced View:** Highlighted CLAHE regions, warped multi-view perspectives, or HSV optical flow vectors.
- **Initial Nadir Sweep:** Baseline view with yellow flood contour overlays and real-time geometric telemetry.
- **Optical Flow Surge Map:** Color-coded velocity magnitude and direction vectors.
- **Homography Warped Alignment:** Geometrically aligned perspective projection proving inlier matches.

### 4. Verifiable Multimodal Audit Trail
- **Step-by-Step Reasoner Trace:** Displays calibrated metrics (Flood Contour Area %, Canny Edge Density, Glare/Shadow Index, Homography Inliers, Flow Velocity).
- **Llama 3.2 90B Vision Analysis:** Displays the exact natural language hazard observation, reasons for uncertainty, and required visual evidence.
- **Confidence Gain Meter:** Quantifies the mathematical confidence jump before and after the OpenCV tool action ($\Delta \text{Confidence}$).

### 5. Emergency Response Dispatch Actions
- **Approve Rescue Dispatch:** Instantly commits the incident record and routes emergency watercraft or heavy extraction teams.
- **Request Secondary Drone Sweep:** Repositions the aerial swarm for further geometric validation.
- **Close Incident:** Flags area as cleared of acute life-safety hazards.

---

## 🛠️ Tech Stack & Architecture

- **Framework:** Next.js 16 with Turbopack bundler and App Router
- **Runtime:** React 19 with Server/Client Components
- **Styling:** Tailwind CSS v4 with curated dark-mode glassmorphism
- **Icons:** Lucide React
- **Backend API Integration:** Proxied via Next.js `rewrites()` to FastAPI on `http://127.0.0.1:8000`

---

## 🏁 Getting Started

### 1. Prerequisites
- Node.js 18+ and `npm`
- Running SwarmTwin FastAPI backend (`uvicorn backend.app.main:app --port 8000`)

### 2. Installation & Running

```bash
# Enter the swarmtwin-ui directory
cd swarmtwin-ui

# Install dependencies
npm install

# Start the Turbopack development server
npm run dev
```

Open **`http://localhost:3000`** in your browser.

### 3. Environment Configuration (Optional)

Create a `.env.local` file if you wish to customize the backend URL:
```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```
*(By default, Next.js proxies all `/inspect` and `/api/*` calls directly to the local FastAPI backend).*

---

## 📦 Production Build

```bash
npm run build
npm run start
```
Compiles an optimized production bundle with full static and dynamic route prefetching.

---

<div align="center">
<sub>SwarmTwin Control Room • Built for the AWS Graviton4 COOL & NVIDIA NIM Challenges</sub>
</div>
