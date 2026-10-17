"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import {
  Upload,
  MapPin,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Bug,
  Radio,
  Share2,
  Compass,
  RefreshCw,
  Zap,
  Crosshair,
  ArrowRight,
  Database
} from "lucide-react";
import type { InspectionResponse } from "./types";

// Dynamically import the Leaflet map to prevent Next.js SSR window is not defined errors
const GISMap = dynamic(() => import("../components/Map"), {
  ssr: false,
  loading: () => (
    <div className="h-[300px] bg-slate-200 animate-pulse rounded-md flex items-center justify-center text-slate-500 font-mono text-xs">
      Loading Sat-Map...
    </div>
  ),
});

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
    color: "text-amber-800 bg-amber-100 border-amber-300",
    borderColor: "border-amber-200 hover:border-amber-400",
    desc: "Severe solar specular reflection over flooded road. Triggers LAB-CLAHE contrast equalization."
  },
  {
    id: "floodnet_10173",
    sampleId: "10173",
    badge: "FloodNet 10173",
    title: "Canopy Debris Occlusion",
    action: "REQUEST_ALTERNATE_VIEWPOINT (USAC_MAGSAC)",
    color: "text-blue-800 bg-blue-100 border-blue-300",
    borderColor: "border-blue-200 hover:border-blue-400",
    desc: "Collapsed tree canopy obstructing vehicles. Aligns Drone B oblique view via USAC_MAGSAC."
  },
  {
    id: "floodnet_10177",
    sampleId: "10177",
    badge: "FloodNet 10177",
    title: "Inundation Basin Surge",
    action: "COMPUTE_OPTICAL_FLOW_SURGE (Farnebäck)",
    color: "text-purple-800 bg-purple-100 border-purple-300",
    borderColor: "border-purple-200 hover:border-purple-400",
    desc: "Active water accumulation. Computes Farnebäck dense optical flow across sequential burst frames."
  }
];

export default function ControlRoom() {
  const [data, setData] = useState<InspectionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [debugMode, setDebugMode] = useState(false);
  const [dispatchStatus, setDispatchStatus] = useState<string | null>(null);
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
    setDispatchStatus(null);
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
      result.gps = { lat: 29.7604, lng: -95.3698 };
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
    setDispatchStatus(null);
    try {
      const endpoint = getApiEndpoint(`/api/scenarios/${scenarioId}/run`);
      const res = await fetch(endpoint, { method: "POST" });
      if (!res.ok) {
        throw new Error(`Scenario call returned ${res.status}: ${await res.text()}`);
      }
      const result: InspectionResponse = await res.json();
      result.gps = { lat: 29.7604, lng: -95.3698 };
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
    setDispatchStatus(null);
    try {
      const cleanId = sampleId.replace(/\.jpg$/i, "").trim();
      const endpoint = getApiEndpoint(`/api/floodnet/inspect/${cleanId}`);
      const res = await fetch(endpoint, { method: "POST" });
      if (!res.ok) {
        throw new Error(`FloodNet call returned ${res.status}: ${await res.text()}`);
      }
      const result: InspectionResponse = await res.json();
      result.gps = { lat: 29.7604, lng: -95.3698 };
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
    <div className="min-h-screen bg-slate-100 text-slate-900 p-4 md:p-6 lg:p-8 font-sans selection:bg-blue-600/20">
      {/* =========================================================================
          TOP COMMAND BAR & ACTIONS (Daylight Tactical Mode)
      ========================================================================= */}
      <header className="mb-6 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 border-b border-slate-300 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-11 h-11 rounded-xl bg-white border border-slate-300 p-1.5 shadow-sm">
              <img src="/logo.svg" alt="SwarmTwin Logo" className="w-full h-full object-contain" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-slate-900 flex items-center gap-2">
                SwarmTwin <span className="text-blue-600 text-sm md:text-base font-mono px-2 py-0.5 bg-blue-100 border border-blue-200 rounded font-bold">TACTICAL CMD</span>
              </h1>
              <p className="text-xs text-slate-600 font-semibold flex items-center gap-2 mt-0.5">
                <span>Field Triage & Geospatial Dispatch</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span className="text-emerald-700 font-mono text-[11px]">SAR Readiness Active</span>
              </p>
            </div>
          </div>
        </div>

        {/* Tactical Controls & Upload Form */}
        <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
          {/* Debug Mode Button */}
          <button
            type="button"
            onClick={() => setDebugMode(!debugMode)}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-md text-xs font-bold border transition-colors cursor-pointer shadow-sm ${
              debugMode
                ? "bg-amber-100 text-amber-800 border-amber-300"
                : "bg-slate-200 text-slate-700 border-slate-300 hover:bg-slate-300"
            }`}
          >
            <Bug size={15} />
            <span>{debugMode ? "Debug Mode: ON" : "Debug Mode"}</span>
          </button>

          {/* Primary Frame Form */}
          <form onSubmit={runInspection} className="flex items-center gap-2 flex-wrap">
            <input
              type="file"
              name="primary_frame"
              required
              className="text-xs file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:bg-slate-200 file:text-slate-800 file:font-semibold hover:file:bg-slate-300 cursor-pointer"
            />
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-5 py-2 rounded-md font-bold text-xs transition-colors shadow-md flex items-center gap-2 cursor-pointer active:scale-95"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Scanning...</span>
                </>
              ) : (
                <>
                  <Upload className="w-3.5 h-3.5" />
                  <span>Analyze Feed</span>
                </>
              )}
            </button>
          </form>
        </div>
      </header>

      {/* =========================================================================
          FLOODNET REAL DISASTER SAR PRESETS STRIP
      ========================================================================= */}
      <div className="mb-6 p-4 rounded-xl bg-white border border-slate-300 shadow-sm flex flex-col gap-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-2.5">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-500" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-800 font-mono">
              FloodNet Real Disaster SAR Scenarios (450 Aerial Feeds)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-500 font-mono font-semibold">Custom ID:</span>
            <input
              type="text"
              placeholder="e.g. 10169"
              value={customFloodNetId}
              onChange={(e) => setCustomFloodNetId(e.target.value)}
              className="bg-slate-50 border border-slate-300 rounded px-2.5 py-1 text-xs font-mono text-slate-800 w-24 outline-none focus:border-blue-500"
            />
            <button
              type="button"
              onClick={() => runFloodNetInspect(customFloodNetId)}
              disabled={loading || !customFloodNetId}
              className="px-2.5 py-1 rounded bg-slate-200 hover:bg-slate-300 text-xs font-mono text-slate-800 font-bold disabled:opacity-40 transition-colors cursor-pointer"
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
              className={`p-3 rounded-lg border ${preset.borderColor} bg-slate-50 hover:bg-blue-50/50 text-left transition-all cursor-pointer flex flex-col gap-1.5 group shadow-xs`}
            >
              <div className="flex items-center justify-between">
                <span className={`text-[11px] font-mono px-2 py-0.5 rounded border font-bold ${preset.color}`}>
                  {preset.badge}
                </span>
                <span className="text-[10px] text-slate-500 font-mono font-bold group-hover:text-blue-600 transition-colors">
                  Run SAR Triage →
                </span>
              </div>
              <p className="text-xs font-bold text-slate-900 group-hover:text-blue-700 transition-colors">
                {preset.title}
              </p>
              <p className="text-[11px] text-slate-600 leading-relaxed font-medium">
                {preset.desc}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Error Callout Banner */}
      {errorMsg && (
        <div className="mb-6 p-4 rounded-lg bg-red-100 border border-red-300 text-red-800 text-xs font-semibold flex items-center gap-2 shadow-sm">
          <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
          <span>Error connecting to API ({apiHost}): {errorMsg}</span>
        </div>
      )}

      {/* =========================================================================
          THE TACTICAL 3-PANE SAR GRID
      ========================================================================= */}
      {data ? (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* -----------------------------------------------------------------------
              LEFT: THE TARGET VISUAL & ONE-CLICK DISPATCH (1 Col)
          ----------------------------------------------------------------------- */}
          <div className="lg:col-span-1 bg-white border border-slate-300 shadow-sm rounded-lg p-4 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                <Upload size={18} className="text-blue-600" /> Target Visual
              </h2>
              {data.visual_evidence?.dynamodb_persisted && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300 font-bold flex items-center gap-1">
                  <Database size={10} /> DYNAMODB ✓
                </span>
              )}
            </div>

            {getEvidenceImageSrc(data) ? (
              <div className="aspect-video bg-slate-900 rounded-md border border-slate-300 overflow-hidden flex items-center justify-center relative shadow-sm">
                <img
                  src={getEvidenceImageSrc(data)!}
                  onError={(e) => {
                    if (data.visual_evidence?.post_action_annotated_base64) {
                      e.currentTarget.src = `data:image/jpeg;base64,${data.visual_evidence.post_action_annotated_base64}`;
                    } else if (data.visual_evidence?.initial_annotated_base64) {
                      e.currentTarget.src = `data:image/jpeg;base64,${data.visual_evidence.initial_annotated_base64}`;
                    }
                  }}
                  alt="Drone Target Visual Feed"
                  className="w-full h-full object-cover"
                />
              </div>
            ) : (
              <div className="aspect-video bg-slate-100 flex items-center justify-center rounded-md border border-slate-300 text-slate-500 text-xs font-mono">
                No Visual Feed Returned
              </div>
            )}

            <div className="p-4 bg-slate-50 rounded-md border border-slate-200 space-y-4">
              <div>
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
                  Incident ID
                </span>
                <p className="font-mono text-lg font-extrabold text-slate-900">
                  {data.incident_id}
                </p>
              </div>

              <div>
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">
                  Final Verdict
                </span>
                <div
                  className={`px-3 py-2 rounded-md font-bold text-sm text-center uppercase tracking-wide flex items-center justify-center gap-2 shadow-xs ${
                    data.final_status === "ESCALATE_HUMAN_REVIEW"
                      ? "bg-red-100 text-red-700 border border-red-300 animate-pulse"
                      : "bg-green-100 text-green-700 border border-green-300"
                  }`}
                >
                  {data.final_status === "ESCALATE_HUMAN_REVIEW" ? (
                    <AlertTriangle size={18} className="text-red-600 shrink-0" />
                  ) : (
                    <CheckCircle2 size={18} className="text-green-600 shrink-0" />
                  )}
                  <span>{data.final_status}</span>
                </div>
              </div>

              {/* One-Click Dispatch Tools */}
              <div className="space-y-2 pt-2 border-t border-slate-200">
                {dispatchStatus ? (
                  <div className="p-2.5 rounded bg-emerald-100 border border-emerald-300 text-emerald-800 text-xs font-bold flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <CheckCircle2 size={14} className="text-emerald-600" />
                      {dispatchStatus}
                    </span>
                    <button
                      type="button"
                      onClick={() => setDispatchStatus(null)}
                      className="text-xs text-emerald-700 underline font-mono cursor-pointer"
                    >
                      Clear
                    </button>
                  </div>
                ) : null}

                <button
                  type="button"
                  onClick={() => setDispatchStatus("Watercraft Rescue Unit Authorized & Dispatched.")}
                  className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-2.5 px-4 rounded-md flex items-center justify-center gap-2 shadow-sm transition-colors cursor-pointer text-xs uppercase tracking-wide active:scale-95"
                >
                  <Radio size={16} /> Dispatch Rescue
                </button>
                <button
                  type="button"
                  onClick={() => setDispatchStatus("Incident Packet Relayed to Ground SAR Team Alpha.")}
                  className="w-full bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold py-2.5 px-4 rounded-md flex items-center justify-center gap-2 transition-colors cursor-pointer text-xs uppercase tracking-wide active:scale-95"
                >
                  <Share2 size={16} /> Relay to Ground Team
                </button>
              </div>
            </div>
          </div>

          {/* -----------------------------------------------------------------------
              MIDDLE: OPERATIONAL TRACE (2 Cols - Side by Side Comparison)
          ----------------------------------------------------------------------- */}
          <div className="lg:col-span-2 bg-white border border-slate-300 shadow-sm rounded-lg p-5 flex flex-col justify-between">
            <div>
              <div className="flex flex-wrap items-center justify-between border-b border-slate-200 pb-3 mb-4 gap-2">
                <div className="flex items-center gap-2">
                  <Activity size={18} className="text-blue-600" />
                  <h2 className="text-base font-bold text-slate-900 tracking-wide uppercase">
                    Operational Trace
                  </h2>
                </div>

                {data.action_taken && (
                  <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-mono font-bold">
                    <ArrowRight size={13} className="text-blue-600" />
                    <span>Action: {data.action_taken}</span>
                    {data.confidence_delta ? (
                      <span className="text-emerald-700 font-bold ml-1">
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
                  <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 shadow-xs flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-center mb-3">
                        <span className="text-xs font-bold tracking-wider text-blue-600 uppercase font-mono">
                          {data.trace[0].phase || "INITIAL PERCEPTION"}
                        </span>
                        <span className="text-xs font-mono bg-white px-2 py-0.5 rounded text-slate-700 border border-slate-300 font-bold">
                          Step 1
                        </span>
                      </div>

                      {/* Highlighted Actionable Intelligence */}
                      <div className="mb-3">
                        <div className="flex items-start gap-3 bg-white p-3 rounded-lg border border-slate-200 shadow-xs">
                          <AlertTriangle className="text-amber-500 shrink-0 mt-0.5" size={18} />
                          <div>
                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">
                              Observed Hazard
                            </p>
                            <p className="text-xs font-bold text-slate-900 leading-snug">
                              {data.trace[0].llm.observed_hazard}
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="bg-white rounded-lg border border-slate-200 p-3 space-y-2 text-xs mb-3">
                        <div className="flex justify-between items-start gap-3">
                          <span className="text-slate-500 font-semibold shrink-0">Uncertainty</span>
                          <span className="text-amber-700 font-medium text-right leading-tight">
                            {data.trace[0].llm.uncertainty_reason}
                          </span>
                        </div>
                        <div className="flex justify-between items-center border-t border-slate-100 pt-2">
                          <span className="text-slate-500 font-semibold">Confidence</span>
                          <span className={`font-mono text-xs px-2 py-0.5 rounded font-bold ${
                            data.trace[0].llm.confidence >= 0.7
                              ? "bg-green-100 text-green-800 border border-green-300"
                              : "bg-yellow-100 text-yellow-800 border border-yellow-300"
                          }`}>
                            {(data.trace[0].llm.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="flex justify-between items-center border-t border-slate-100 pt-2">
                          <span className="text-slate-500 font-semibold">Next Protocol</span>
                          <span
                            className="font-mono text-[10px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 truncate max-w-[65%]"
                            title={data.trace[0].llm.recommended_action}
                          >
                            {data.trace[0].llm.recommended_action}
                          </span>
                        </div>
                      </div>

                      {/* Developer Telemetry (Hidden behind Debug Mode) */}
                      {debugMode && (
                        <div className="mt-3 p-3 bg-slate-900 rounded-md text-slate-300 text-xs font-mono overflow-x-auto shadow-inner">
                          <p className="text-amber-400 font-bold mb-1">// RAW OPENCV METRICS</p>
                          <pre className="text-[10px] leading-tight text-neutral-300">
                            {JSON.stringify(data.trace[0].cv, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* 2. POST-ACTION VERIFICATION CARD */}
                {data.trace.length > 1 ? (
                  <div className="bg-slate-50 p-4 rounded-lg border border-purple-200 shadow-xs flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-center mb-3">
                        <span className="text-xs font-bold tracking-wider text-purple-700 uppercase font-mono">
                          {data.trace[1].phase || "POST-ACTION VERIFICATION"}
                        </span>
                        <span className="text-xs font-mono bg-white px-2 py-0.5 rounded text-slate-700 border border-slate-300 font-bold">
                          Step 2
                        </span>
                      </div>

                      {data.trace[1].action_taken && (
                        <div className="mb-3 bg-blue-100 border border-blue-200 rounded p-2 text-xs text-blue-800 font-bold flex items-center gap-2">
                          <Activity size={14} className="text-blue-600 shrink-0" />
                          <span className="font-mono truncate">OpenCV Protocol: {data.trace[1].action_taken}</span>
                        </div>
                      )}

                      {/* Highlighted Actionable Intelligence */}
                      <div className="mb-3">
                        <div className="flex items-start gap-3 bg-white p-3 rounded-lg border border-slate-200 shadow-xs">
                          <CheckCircle2 className="text-emerald-600 shrink-0 mt-0.5" size={18} />
                          <div>
                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">
                              Confirmed Hazard
                            </p>
                            <p className="text-xs font-bold text-slate-900 leading-snug">
                              {data.trace[1].llm.observed_hazard}
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="bg-white rounded-lg border border-slate-200 p-3 space-y-2 text-xs mb-3">
                        <div className="flex justify-between items-start gap-3">
                          <span className="text-slate-500 font-semibold shrink-0">Evidence</span>
                          <span className="text-slate-800 font-medium text-right leading-tight">
                            {data.trace[1].llm.evidence_needed || data.trace[1].llm.uncertainty_reason}
                          </span>
                        </div>
                        <div className="flex justify-between items-center border-t border-slate-100 pt-2">
                          <span className="text-slate-500 font-semibold">Confidence</span>
                          <span className={`font-mono text-xs px-2 py-0.5 rounded font-bold ${
                            data.trace[1].llm.confidence >= 0.7
                              ? "bg-green-100 text-green-800 border border-green-300"
                              : "bg-yellow-100 text-yellow-800 border border-yellow-300"
                          }`}>
                            {(data.trace[1].llm.confidence * 100).toFixed(0)}%
                            {data.confidence_delta ? (
                              <span className="ml-1 text-[10px] text-emerald-700">
                                (+{Math.round(data.confidence_delta * 100)}%)
                              </span>
                            ) : null}
                          </span>
                        </div>
                        <div className="flex justify-between items-center border-t border-slate-100 pt-2">
                          <span className="text-slate-500 font-semibold">Verdict</span>
                          <span
                            className="font-mono text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-300 truncate max-w-[65%]"
                            title={data.trace[1].llm.recommended_action}
                          >
                            {data.trace[1].llm.recommended_action}
                          </span>
                        </div>
                      </div>

                      {/* Developer Telemetry (Hidden behind Debug Mode) */}
                      {debugMode && (
                        <div className="mt-3 p-3 bg-slate-900 rounded-md text-slate-300 text-xs font-mono overflow-x-auto shadow-inner">
                          <p className="text-amber-400 font-bold mb-1">// RAW OPENCV METRICS</p>
                          <pre className="text-[10px] leading-tight text-neutral-300">
                            {JSON.stringify(data.trace[1].cv, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="bg-slate-50 p-6 rounded-lg border border-dashed border-slate-300 flex flex-col items-center justify-center text-center">
                    <CheckCircle2 className="w-8 h-8 text-emerald-600 mb-2" />
                    <p className="text-xs font-bold text-slate-800">Single-Pass Resolution</p>
                    <p className="text-[11px] text-slate-500 mt-1 max-w-[220px]">
                      High confidence achieved on initial sweep. No secondary action required.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* -----------------------------------------------------------------------
              RIGHT: GEOSPATIAL MAP INTEGRATION (1 Col)
          ----------------------------------------------------------------------- */}
          <div className="lg:col-span-1 bg-white border border-slate-300 shadow-sm rounded-lg p-4 flex flex-col">
            <h2 className="text-base font-bold text-slate-800 mb-3 flex items-center gap-2">
              <MapPin size={18} className="text-blue-600" /> GIS Coordinates
            </h2>
            <div className="flex justify-between items-center mb-3 bg-slate-100 p-2.5 rounded-md border border-slate-200">
              <div className="flex items-center gap-2 text-xs font-mono font-bold text-slate-700">
                <Compass size={16} className="text-blue-600" />
                <span>
                  {data.gps ? `${data.gps.lat.toFixed(4)}° N, ${Math.abs(data.gps.lng).toFixed(4)}° W` : "29.7604° N, 95.3698° W"}
                </span>
              </div>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 border border-blue-200 font-bold">
                SAT-GPS
              </span>
            </div>
            <div className="flex-1 min-h-[300px] rounded-md overflow-hidden border border-slate-300">
              <GISMap
                lat={data.gps?.lat || 29.7604}
                lng={data.gps?.lng || -95.3698}
                hazard={data.trace[0]?.llm.observed_hazard || "Submerged vehicle hazard"}
              />
            </div>
          </div>
        </div>
      ) : (
        /* Empty State */
        <div className="py-24 flex flex-col items-center justify-center gap-3 text-center border-2 border-dashed border-slate-300 rounded-xl bg-white shadow-xs">
          <Crosshair className="w-12 h-12 text-blue-600/70 animate-pulse" />
          <h3 className="text-base font-bold text-slate-800">
            Awaiting Aerial Feed Ingestion
          </h3>
          <p className="text-xs text-slate-600 max-w-lg leading-relaxed font-medium">
            Select one of the FloodNet SAR scenarios above or upload an aerial drone keyframe to initiate automated computer vision triage and geospatial positioning.
          </p>
        </div>
      )}
    </div>
  );
}