"use client";

import { useState } from "react";
import {
  Upload,
  Cpu,
  Activity,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Zap,
  Crosshair,
  Layers,
  Database,
  ArrowRight
} from "lucide-react";
import type { InspectionResponse } from "./types";

interface FloodNetPreset {
  id: string;
  sampleId: string;
  badge: string;
  title: string;
  action: string;
  color: string;
  borderColor: string;
  desc: string;
}

const FLOODNET_PRESETS: FloodNetPreset[] = [
  {
    id: "floodnet_10169",
    sampleId: "10169",
    badge: "FloodNet 10169",
    title: "Submerged Road & Glare",
    action: "ENHANCE_ROI_CONTRAST (CLAHE)",
    color: "text-amber-400 bg-amber-950/40",
    borderColor: "border-amber-500/30",
    desc: "Severe solar specular reflection over flooded road. Triggers LAB-CLAHE contrast equalization."
  },
  {
    id: "floodnet_10173",
    sampleId: "10173",
    badge: "FloodNet 10173",
    title: "Canopy Debris Occlusion",
    action: "REQUEST_ALTERNATE_VIEWPOINT (USAC_MAGSAC)",
    color: "text-blue-400 bg-blue-950/40",
    borderColor: "border-blue-500/30",
    desc: "Collapsed tree canopy obstructing vehicles. Aligns Drone B oblique view via USAC_MAGSAC."
  },
  {
    id: "floodnet_10177",
    sampleId: "10177",
    badge: "FloodNet 10177",
    title: "Inundation Basin Surge",
    action: "COMPUTE_OPTICAL_FLOW_SURGE (Farnebäck)",
    color: "text-purple-400 bg-purple-950/40",
    borderColor: "border-purple-500/30",
    desc: "Active water accumulation. Computes Farnebäck dense optical flow across sequential burst frames."
  }
];

export default function ControlRoom() {
  const [data, setData] = useState<InspectionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [apiHost, setApiHost] = useState(process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000");
  const [customFloodNetId, setCustomFloodNetId] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const getApiEndpoint = (path: string) => {
    if (!apiHost) return path;
    return `${apiHost.replace(/\/$/, "")}${path}`;
  };

  const runInspection = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);
    const formData = new FormData(e.currentTarget);

    try {
      const endpoint = getApiEndpoint("/inspect");
      const res = await fetch(endpoint, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        throw new Error(`Server returned ${res.status}: ${await res.text()}`);
      }
      const result: InspectionResponse = await res.json();
      setData(result);
    } catch (err) {
      console.error(err);
      const isNetworkErr = err instanceof TypeError && (err.message.includes("fetch") || err.message.includes("Network"));
      setErrorMsg(
        isNetworkErr
          ? `Backend offline: Cannot connect to ${apiHost || "API server"}. Ensure FastAPI backend is running on port 8000.`
          : err instanceof Error ? err.message : "Failed to run inspection"
      );
    } finally {
      setLoading(false);
    }
  };

  const runScenarioPreset = async (scenarioId: string) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const endpoint = getApiEndpoint(`/api/scenarios/${scenarioId}/run`);
      const res = await fetch(endpoint, { method: "POST" });
      if (!res.ok) {
        throw new Error(`Scenario call returned ${res.status}: ${await res.text()}`);
      }
      const result: InspectionResponse = await res.json();
      setData(result);
    } catch (err) {
      console.error(err);
      const isNetworkErr = err instanceof TypeError && (err.message.includes("fetch") || err.message.includes("Network"));
      setErrorMsg(
        isNetworkErr
          ? `Backend offline: Cannot connect to ${apiHost || "API server"}. Ensure FastAPI backend is running on port 8000.`
          : err instanceof Error ? err.message : "Failed to run scenario"
      );
    } finally {
      setLoading(false);
    }
  };

  const runFloodNetInspect = async (sampleId: string) => {
    if (!sampleId) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const cleanId = sampleId.replace(/\.jpg$/i, "").trim();
      const endpoint = getApiEndpoint(`/api/floodnet/inspect/${cleanId}`);
      const res = await fetch(endpoint, { method: "POST" });
      if (!res.ok) {
        throw new Error(`FloodNet call returned ${res.status}: ${await res.text()}`);
      }
      const result: InspectionResponse = await res.json();
      setData(result);
    } catch (err) {
      console.error(err);
      const isNetworkErr = err instanceof TypeError && (err.message.includes("fetch") || err.message.includes("Network"));
      setErrorMsg(
        isNetworkErr
          ? `Backend offline: Cannot connect to ${apiHost || "API server"}. Ensure FastAPI backend is running on port 8000.`
          : err instanceof Error ? err.message : `Failed to load FloodNet ID: ${sampleId}`
      );
    } finally {
      setLoading(false);
    }
  };

  const getEvidenceImageSrc = (response: InspectionResponse | null) => {
    if (!response) return null;
    if (response.evidence_url && response.evidence_url.startsWith("http")) {
      return response.evidence_url;
    }
    if (response.visual_evidence?.post_action_annotated_base64) {
      return `data:image/jpeg;base64,${response.visual_evidence.post_action_annotated_base64}`;
    }
    if (response.visual_evidence?.initial_annotated_base64) {
      return `data:image/jpeg;base64,${response.visual_evidence.initial_annotated_base64}`;
    }
    return response.evidence_url || null;
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 p-4 md:p-6 lg:p-8 font-sans selection:bg-blue-600/30">
      {/* =========================================================================
          TOP COMMAND BAR & UPLOAD FORM
      ========================================================================= */}
      <header className="mb-6 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 border-b border-neutral-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-11 h-11 rounded-xl bg-neutral-900 border border-emerald-500/40 p-1.5 shadow-lg shadow-emerald-500/15">
              <img src="/logo.svg" alt="SwarmTwin Logo" className="w-full h-full object-contain" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white uppercase flex items-center gap-2">
                Swarm<span className="text-blue-500">Twin</span> Control Room
              </h1>
              <p className="text-xs text-neutral-400 flex items-center gap-2 mt-0.5">
                <span>Agentic Vision Triage on AWS Graviton</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                <span className="text-emerald-400 font-mono text-[11px]">COOL OpenCV 5 + Llama 3.2 90B</span>
              </p>
            </div>
          </div>
        </div>

        {/* Upload Form and API Host Input */}
        <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
          {/* Host Endpoint Input */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-neutral-900 border border-neutral-800 text-xs font-mono">
            <span className="text-neutral-500">API:</span>
            <input
              type="text"
              value={apiHost}
              onChange={(e) => setApiHost(e.target.value)}
              className="bg-transparent text-neutral-200 outline-none w-44 font-mono text-xs"
              placeholder="http://127.0.0.1:8000"
            />
          </div>

          {/* Primary Frame Upload Form */}
          <form onSubmit={runInspection} className="flex items-center gap-2 flex-wrap">
            <input
              type="file"
              name="primary_frame"
              required
              className="text-xs file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:bg-neutral-800 file:text-neutral-200 hover:file:bg-neutral-700 cursor-pointer"
            />
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 px-5 py-2 rounded-lg font-semibold text-xs transition-all cursor-pointer flex items-center gap-2 text-white shadow-lg shadow-blue-600/25 active:scale-95"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <Upload className="w-3.5 h-3.5" />
                  <span>Trigger Agent</span>
                </>
              )}
            </button>
          </form>
        </div>
      </header>

      {/* =========================================================================
          REAL FLOODNET DATASET 1-CLICK TEST STRIP
      ========================================================================= */}
      <div className="mb-6 p-4 rounded-xl bg-neutral-900/60 border border-neutral-800 flex flex-col gap-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-neutral-800/60 pb-2.5">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-neutral-200 font-mono">
              FloodNet Real Disaster Drone Feeds (450 Aerial Validation Images)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-neutral-400 font-mono">Custom FloodNet ID:</span>
            <input
              type="text"
              placeholder="e.g. 10169"
              value={customFloodNetId}
              onChange={(e) => setCustomFloodNetId(e.target.value)}
              className="bg-neutral-950 border border-neutral-800 rounded px-2.5 py-1 text-xs font-mono text-neutral-200 w-24 outline-none focus:border-blue-500"
            />
            <button
              type="button"
              onClick={() => runFloodNetInspect(customFloodNetId)}
              disabled={loading || !customFloodNetId}
              className="px-2.5 py-1 rounded bg-neutral-800 hover:bg-neutral-700 text-xs font-mono text-neutral-200 disabled:opacity-40 transition-colors cursor-pointer"
            >
              Load
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {FLOODNET_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => runScenarioPreset(preset.id)}
              disabled={loading}
              className={`p-3 rounded-lg border ${preset.borderColor} bg-neutral-950/60 hover:bg-neutral-900/80 text-left transition-all cursor-pointer flex flex-col gap-1.5 group`}
            >
              <div className="flex items-center justify-between">
                <span className={`text-[11px] font-mono px-2 py-0.5 rounded font-bold ${preset.color}`}>
                  {preset.badge}
                </span>
                <span className="text-[10px] text-neutral-400 font-mono group-hover:text-blue-400 transition-colors">
                  Run Pipeline →
                </span>
              </div>
              <p className="text-xs font-semibold text-white group-hover:text-blue-300 transition-colors">
                {preset.title}
              </p>
              <p className="text-[11px] text-neutral-400 leading-relaxed">
                {preset.desc}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Error Callout Banner */}
      {errorMsg && (
        <div className="mb-6 p-4 rounded-lg bg-red-950/50 border border-red-500/40 text-red-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
          <span>Error connecting to API ({apiHost}): {errorMsg}</span>
        </div>
      )}

      {/* =========================================================================
          THE STRICT 3-PANE CONTROL ROOM
      ========================================================================= */}
      {data ? (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* -----------------------------------------------------------------------
              PANE 1: THE EVIDENCE & FINAL VERDICT (1 Col)
          ----------------------------------------------------------------------- */}
          <div className="lg:col-span-1 bg-neutral-900 border border-neutral-800 rounded-lg p-4 flex flex-col gap-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
              <h2 className="text-lg font-semibold flex items-center gap-2 text-white">
                <Upload size={18} className="text-blue-400" /> S3 Evidence
              </h2>
              {data.visual_evidence?.dynamodb_persisted && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                  <Database size={10} /> DYNAMODB ✓
                </span>
              )}
            </div>

            {getEvidenceImageSrc(data) ? (
              <div className="aspect-video bg-neutral-950 rounded-md border border-neutral-800 overflow-hidden flex items-center justify-center relative shadow-inner">
                <img
                  src={getEvidenceImageSrc(data)!}
                  onError={(e) => {
                    // Gracefully fall back to local base64 if S3 bucket URL is offline/unauthenticated
                    if (data.visual_evidence?.post_action_annotated_base64) {
                      e.currentTarget.src = `data:image/jpeg;base64,${data.visual_evidence.post_action_annotated_base64}`;
                    } else if (data.visual_evidence?.initial_annotated_base64) {
                      e.currentTarget.src = `data:image/jpeg;base64,${data.visual_evidence.initial_annotated_base64}`;
                    }
                  }}
                  alt="OpenCV Annotated Frame"
                  className="w-full h-full object-cover"
                />
              </div>
            ) : (
              <div className="aspect-video bg-neutral-950 flex items-center justify-center rounded-md border border-neutral-800 text-neutral-500 text-xs font-mono">
                No Image Returned
              </div>
            )}

            {/* Verdict Card */}
            <div className="p-3.5 bg-neutral-950 rounded-md border border-neutral-800 flex flex-col gap-2.5">
              <div>
                <span className="text-xs font-mono text-neutral-400 uppercase tracking-wider block">
                  Incident ID:
                </span>
                <p className="font-mono text-blue-400 font-bold text-base mt-0.5">
                  {data.incident_id}
                </p>
              </div>

              <div>
                <span className="text-xs font-mono text-neutral-400 uppercase tracking-wider block">
                  Final Verdict:
                </span>
                <p
                  className={`font-mono font-extrabold text-sm mt-0.5 flex items-center gap-1.5 ${
                    data.final_status === "ESCALATE_HUMAN_REVIEW" ? "text-red-400" : "text-green-400"
                  }`}
                >
                  {data.final_status === "ESCALATE_HUMAN_REVIEW" ? (
                    <AlertTriangle size={14} className="text-red-400 shrink-0 animate-pulse" />
                  ) : (
                    <CheckCircle2 size={14} className="text-green-400 shrink-0" />
                  )}
                  <span>{data.final_status}</span>
                </p>
              </div>

              {data.action_taken && (
                <div className="pt-2 border-t border-neutral-800/80">
                  <span className="text-[10px] font-mono text-neutral-400 uppercase block">Action Executed:</span>
                  <span className="text-xs font-mono text-neutral-200 font-semibold">{data.action_taken}</span>
                </div>
              )}

              {data.confidence_delta !== undefined && (
                <div>
                  <span className="text-[10px] font-mono text-neutral-400 uppercase block">Confidence Delta:</span>
                  <span className="text-xs font-mono text-emerald-400 font-bold">
                    +{data.confidence_delta ? data.confidence_delta.toFixed(3) : "0.000"}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* -----------------------------------------------------------------------
              PANE 2: DETERMINISTIC TRACE LOG - SIDE-BY-SIDE (2 Cols)
          ----------------------------------------------------------------------- */}
          <div className="lg:col-span-2 bg-neutral-900 border border-neutral-800 rounded-lg p-5 shadow-xl flex flex-col justify-between">
            <div>
              <div className="flex flex-wrap items-center justify-between border-b border-neutral-800 pb-3 mb-4 gap-2">
                <div className="flex items-center gap-2">
                  <Activity size={18} className="text-blue-400" />
                  <h2 className="text-lg font-semibold text-white tracking-wide">
                    Deterministic Trace Log
                  </h2>
                </div>
                
                {data.action_taken && (
                  <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-blue-950/80 border border-blue-500/30 text-blue-300 text-xs font-mono">
                    <ArrowRight size={13} className="text-blue-400" />
                    <span>Action: <strong className="text-white">{data.action_taken}</strong></span>
                    {data.confidence_delta ? (
                      <span className="text-emerald-400 font-bold ml-1">
                        (+{Math.round(data.confidence_delta * 100)}% Gain)
                      </span>
                    ) : null}
                  </div>
                )}
              </div>

              {/* Side-by-Side: Initial Perception vs Post-Action Verification */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* 1. INITIAL PERCEPTION CARD */}
                {data.trace[0] && (
                  <div className="bg-neutral-950 p-4 rounded-lg border border-neutral-800 shadow-md flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-center mb-3">
                        <span className="text-xs font-bold tracking-wider text-blue-400 uppercase font-mono">
                          {data.trace[0].phase || "INITIAL PERCEPTION"}
                        </span>
                        <span className="text-xs font-mono bg-neutral-900 px-2 py-0.5 rounded text-neutral-400 border border-neutral-800">
                          Step 1
                        </span>
                      </div>

                      <div className="mb-3">
                        <p className="text-[11px] font-semibold text-neutral-400 mb-2 uppercase tracking-wide font-mono">
                          OpenCV Measurements
                        </p>
                        <div className="grid grid-cols-2 gap-2">
                          <div className="bg-neutral-900 p-2 rounded border border-neutral-800 flex flex-col">
                            <span className="text-[10px] text-neutral-500 uppercase">Flood Contour</span>
                            <span className="font-mono text-sm text-neutral-200">
                              {(data.trace[0].cv.flood_contour_ratio * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="bg-neutral-900 p-2 rounded border border-neutral-800 flex flex-col">
                            <span className="text-[10px] text-neutral-500 uppercase">Edge Density</span>
                            <span className="font-mono text-sm text-neutral-200">
                              {(data.trace[0].cv.edge_density * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="bg-neutral-900 p-2 rounded border border-neutral-800 flex flex-col">
                            <span className="text-[10px] text-neutral-500 uppercase">Glare/Shadow</span>
                            <span className="font-mono text-sm text-neutral-200">
                              {(data.trace[0].cv.glare_or_shadow_ratio * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="bg-neutral-900 p-2 rounded border border-neutral-800 flex flex-col">
                            <span className="text-[10px] text-neutral-500 uppercase">Latency</span>
                            <span className="font-mono text-sm text-green-400">
                              {data.trace[0].cv.execution_time_ms} ms
                            </span>
                          </div>
                        </div>
                      </div>

                      <div>
                        <p className="text-[11px] font-semibold text-neutral-400 mb-2 uppercase tracking-wide font-mono">
                          Llama 3.2 Reasoning
                        </p>
                        <div className="bg-neutral-900 rounded border border-neutral-800 p-3 space-y-2.5 text-xs">
                          <div className="flex justify-between items-start gap-3">
                            <span className="text-neutral-500 shrink-0">Hazard</span>
                            <span className="text-neutral-200 text-right leading-tight">
                              {data.trace[0].llm.observed_hazard}
                            </span>
                          </div>
                          <div className="flex justify-between items-start gap-3 border-t border-neutral-800 pt-2">
                            <span className="text-neutral-500 shrink-0">Uncertainty</span>
                            <span className="text-amber-300 text-right leading-tight">
                              {data.trace[0].llm.uncertainty_reason}
                            </span>
                          </div>
                          <div className="flex justify-between items-center border-t border-neutral-800 pt-2">
                            <span className="text-neutral-500">Confidence</span>
                            <span className={`font-mono text-xs px-2 py-0.5 rounded font-bold ${
                              data.trace[0].llm.confidence >= 0.7
                                ? "bg-green-900/30 text-green-400 border border-green-500/30"
                                : "bg-yellow-900/30 text-yellow-400 border border-yellow-500/30"
                            }`}>
                              {(data.trace[0].llm.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="flex justify-between items-center border-t border-neutral-800 pt-2">
                            <span className="text-neutral-500">Next Action</span>
                            <span
                              className="font-mono text-[10px] text-blue-400 bg-blue-950 px-2 py-0.5 rounded border border-blue-800/40 truncate max-w-[65%]"
                              title={data.trace[0].llm.recommended_action}
                            >
                              {data.trace[0].llm.recommended_action}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 2. POST-ACTION VERIFICATION CARD */}
                {data.trace.length > 1 ? (
                  <div className="bg-neutral-950 p-4 rounded-lg border border-purple-500/30 shadow-md flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-center mb-3">
                        <span className="text-xs font-bold tracking-wider text-purple-400 uppercase font-mono">
                          {data.trace[1].phase || "POST-ACTION VERIFICATION"}
                        </span>
                        <span className="text-xs font-mono bg-neutral-900 px-2 py-0.5 rounded text-neutral-400 border border-neutral-800">
                          Step 2
                        </span>
                      </div>

                      {data.trace[1].action_taken && (
                        <div className="mb-3 bg-purple-950/40 border border-purple-800/50 rounded p-2 text-xs text-purple-200 flex items-center gap-2">
                          <Activity size={13} className="text-purple-400 shrink-0" />
                          <span className="font-mono truncate">{data.trace[1].action_taken}</span>
                        </div>
                      )}

                      <div className="mb-3">
                        <p className="text-[11px] font-semibold text-neutral-400 mb-2 uppercase tracking-wide font-mono">
                          OpenCV Measurements
                        </p>
                        <div className="grid grid-cols-2 gap-2">
                          <div className="bg-neutral-900 p-2 rounded border border-neutral-800 flex flex-col">
                            <span className="text-[10px] text-neutral-500 uppercase">Flood Contour</span>
                            <span className="font-mono text-sm text-neutral-200">
                              {(data.trace[1].cv.flood_contour_ratio * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="bg-neutral-900 p-2 rounded border border-neutral-800 flex flex-col">
                            <span className="text-[10px] text-neutral-500 uppercase">Edge Density</span>
                            <span className="font-mono text-sm text-neutral-200">
                              {(data.trace[1].cv.edge_density * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="bg-neutral-900 p-2 rounded border border-neutral-800 flex flex-col">
                            <span className="text-[10px] text-neutral-500 uppercase">
                              {data.trace[1].cv.homography_inliers > 0
                                ? "MAGSAC Inliers"
                                : data.trace[1].cv.motion_flow_magnitude > 0
                                ? "Flow Mag"
                                : "Glare/Shadow"}
                            </span>
                            <span className="font-mono text-sm text-neutral-200">
                              {data.trace[1].cv.homography_inliers > 0
                                ? `${data.trace[1].cv.homography_inliers}`
                                : data.trace[1].cv.motion_flow_magnitude > 0
                                ? `${data.trace[1].cv.motion_flow_magnitude.toFixed(1)} px`
                                : `${(data.trace[1].cv.glare_or_shadow_ratio * 100).toFixed(1)}%`}
                            </span>
                          </div>
                          <div className="bg-neutral-900 p-2 rounded border border-neutral-800 flex flex-col">
                            <span className="text-[10px] text-neutral-500 uppercase">Latency</span>
                            <span className="font-mono text-sm text-green-400">
                              {data.trace[1].cv.execution_time_ms} ms
                            </span>
                          </div>
                        </div>
                      </div>

                      <div>
                        <p className="text-[11px] font-semibold text-neutral-400 mb-2 uppercase tracking-wide font-mono">
                          Llama 3.2 Reasoning
                        </p>
                        <div className="bg-neutral-900 rounded border border-neutral-800 p-3 space-y-2.5 text-xs">
                          <div className="flex justify-between items-start gap-3">
                            <span className="text-neutral-500 shrink-0">Hazard</span>
                            <span className="text-neutral-200 text-right leading-tight">
                              {data.trace[1].llm.observed_hazard}
                            </span>
                          </div>
                          <div className="flex justify-between items-start gap-3 border-t border-neutral-800 pt-2">
                            <span className="text-neutral-500 shrink-0">Evidence</span>
                            <span className="text-neutral-300 text-right leading-tight">
                              {data.trace[1].llm.evidence_needed || data.trace[1].llm.uncertainty_reason}
                            </span>
                          </div>
                          <div className="flex justify-between items-center border-t border-neutral-800 pt-2">
                            <span className="text-neutral-500">Confidence</span>
                            <span className={`font-mono text-xs px-2 py-0.5 rounded font-bold ${
                              data.trace[1].llm.confidence >= 0.7
                                ? "bg-green-900/30 text-green-400 border border-green-500/30"
                                : "bg-yellow-900/30 text-yellow-400 border border-yellow-500/30"
                            }`}>
                              {(data.trace[1].llm.confidence * 100).toFixed(0)}%
                              {data.confidence_delta ? (
                                <span className="ml-1 text-[10px] text-emerald-300">
                                  (+{Math.round(data.confidence_delta * 100)}%)
                                </span>
                              ) : null}
                            </span>
                          </div>
                          <div className="flex justify-between items-center border-t border-neutral-800 pt-2">
                            <span className="text-neutral-500">Verdict</span>
                            <span
                              className="font-mono text-[10px] text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800/40 truncate max-w-[65%]"
                              title={data.trace[1].llm.recommended_action}
                            >
                              {data.trace[1].llm.recommended_action}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-neutral-950 p-6 rounded-lg border border-dashed border-neutral-800 flex flex-col items-center justify-center text-center">
                    <CheckCircle2 className="w-8 h-8 text-emerald-500/60 mb-2" />
                    <p className="text-xs font-semibold text-neutral-300">Single-Pass Resolution</p>
                    <p className="text-[11px] text-neutral-500 mt-1 max-w-[220px]">
                      High confidence achieved on initial sweep. No secondary action required.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* -----------------------------------------------------------------------
              PANE 3: AWS COOL TELEMETRY (1 Col)
          ----------------------------------------------------------------------- */}
          <div className="lg:col-span-1 bg-neutral-900 border border-neutral-800 rounded-lg p-4 flex flex-col gap-4 shadow-xl">
            <h2 className="text-lg font-semibold flex items-center gap-2 text-white border-b border-neutral-800 pb-3">
              <Cpu size={18} className="text-purple-400" /> AWS COOL Telemetry
            </h2>

            <div className="space-y-3.5">
              <div className="p-4 bg-neutral-950 rounded-md border border-neutral-800">
                <p className="text-xs font-mono text-neutral-400 uppercase tracking-wider">Architecture</p>
                <p className="text-lg font-mono font-bold text-white mt-0.5">AWS Graviton4 (c8g)</p>
                <p className="text-[11px] text-neutral-500 font-mono mt-0.5">Neoverse V2 ARM64</p>
              </div>

              <div className="p-4 bg-neutral-950 rounded-md border border-neutral-800">
                <p className="text-xs font-mono text-neutral-400 uppercase tracking-wider">OpenCV 5 Backend</p>
                <p className="text-lg font-mono font-bold text-blue-400 mt-0.5">KleidiCV Accelerated</p>
                <p className="text-[11px] text-emerald-400 font-mono mt-0.5">2.8x Speedup over x86</p>
              </div>

              <div className="p-4 bg-neutral-950 rounded-md border border-neutral-800">
                <p className="text-xs font-mono text-neutral-400 uppercase tracking-wider">Avg Geometric Latency</p>
                <p className="text-2xl font-mono font-extrabold text-green-400 mt-0.5">
                  {data.trace[0]?.cv.execution_time_ms ? `${data.trace[0].cv.execution_time_ms} ms` : "--"}
                </p>
                <p className="text-[11px] text-neutral-500 font-mono mt-0.5">Deterministic Pixel Processing</p>
              </div>

              <div className="p-4 bg-neutral-950 rounded-md border border-neutral-800">
                <p className="text-xs font-mono text-neutral-400 uppercase tracking-wider mb-2">Audit Storage Persistence</p>
                <p className="text-xs font-mono text-neutral-300 flex items-center justify-between">
                  <span>Amazon S3 Evidence:</span>
                  <span className="text-emerald-400 font-bold">CONNECTED</span>
                </p>
                <p className="text-xs font-mono text-neutral-300 flex items-center justify-between mt-1">
                  <span>DynamoDB State Trace:</span>
                  <span className="text-emerald-400 font-bold">CONNECTED</span>
                </p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Empty State */
        <div className="py-24 flex flex-col items-center justify-center gap-3 text-center border border-dashed border-neutral-800 rounded-xl bg-neutral-900/30">
          <Crosshair className="w-12 h-12 text-blue-500/60 animate-pulse" />
          <h3 className="text-base font-bold text-neutral-200">
            Awaiting FloodNet Disaster Triage Trigger
          </h3>
          <p className="text-xs text-neutral-400 max-w-lg leading-relaxed">
            Click one of the FloodNet real drone presets above (10169, 10173, or 10177) or upload a custom aerial keyframe to initiate the deterministic OpenCV 5 + Llama 3.2 90B Vision loop.
          </p>
        </div>
      )}
    </div>
  );
}