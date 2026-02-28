import type { UploadResponse, JobProgress, JobPhase } from "@/types";

// ─── Simulated API calls ────────────────────────────────────────────
// These will be replaced with real fetch() calls when the backend is ready.

function delay(ms: number) {
    return new Promise((r) => setTimeout(r, ms));
}

export async function uploadPolicy(file: File): Promise<UploadResponse> {
    await delay(1200);
    return {
        policyId: `pol_${Date.now()}`,
        filename: file.name,
    };
}

// ─── Pipeline simulation ────────────────────────────────────────────
// Simulates the multi-phase extraction pipeline.

const PHASES: JobPhase[] = ["upload", "parse", "extract", "compare"];
const PHASE_DURATIONS: Record<JobPhase, number> = {
    upload: 800,
    parse: 1200,
    extract: 2000,
    compare: 1000,
};

interface PipelineState {
    currentPhaseIdx: number;
    phaseProgress: number;
    startedAt: number;
}

const pipelineStates = new Map<string, PipelineState>();

export function startPipeline(policyId: string) {
    pipelineStates.set(policyId, {
        currentPhaseIdx: 0,
        phaseProgress: 0,
        startedAt: Date.now(),
    });
}

export async function pollPipeline(policyId: string): Promise<JobProgress> {
    await delay(300);

    const state = pipelineStates.get(policyId);
    if (!state) {
        return { phase: "upload", status: "error", progress: 0, error: "Pipeline not found" };
    }

    const phase = PHASES[state.currentPhaseIdx];
    const elapsed = Date.now() - state.startedAt;
    let cumulativeTime = 0;

    for (let i = 0; i <= state.currentPhaseIdx; i++) {
        cumulativeTime += PHASE_DURATIONS[PHASES[i]];
    }

    if (elapsed >= cumulativeTime) {
        // Move to next phase
        if (state.currentPhaseIdx < PHASES.length - 1) {
            state.currentPhaseIdx++;
            state.startedAt = Date.now() - (elapsed - cumulativeTime);
            return {
                phase: PHASES[state.currentPhaseIdx],
                status: "processing",
                progress: Math.round(((state.currentPhaseIdx) / PHASES.length) * 100),
            };
        }
        // All phases done
        return { phase: "compare", status: "complete", progress: 100 };
    }

    // Still in current phase
    const phaseStart = cumulativeTime - PHASE_DURATIONS[phase];
    const phaseProgress = Math.min(95, ((elapsed - phaseStart) / PHASE_DURATIONS[phase]) * 100);

    return {
        phase,
        status: "processing",
        progress: Math.round(((state.currentPhaseIdx + phaseProgress / 100) / PHASES.length) * 100),
    };
}
