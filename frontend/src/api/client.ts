import axios from "axios";
import type {
    UploadResponse,
    JobProgress,
    ExtractedRule,
    ConflictResult,
    ReviewedRule,
    PolicyMeta
} from "@/types";

const API_BASE = "http://35.245.2.116:8000";

const apiClient = axios.create({
    baseURL: API_BASE,
});

// --- API Response Types matching FastAPI logic ---
interface ApiExtractionResult {
    job_id: string;
    status: string;
    rules: ExtractedRule[];
    metadata: {
        policy_name: string;
        effective_date: string;
        applicable_jurisdictions: string[];
    } | null;
}

interface ApiComparisonResult {
    job_id: string;
    status: string;
    comparisons: any[];
    summary: any;
    missing_requirements: any[];
}

export interface ApiRuleReview {
    rule_id: string;
    action: "approve" | "deny" | "edit";
    notes?: string;
    edited_rule?: ExtractedRule;
}

interface ApiReportResult {
    report_id: string;
    job_id: string;
    policy_name: string;
    generated_at: string;
    rule_results: any[];
    missing_requirements: any[];
    summary: any;
}


// --- API Client Methods ---

export async function uploadPolicy(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    // Optional: Extract policy name from filename
    formData.append("policy_name", file.name.replace(".pdf", "").replace(/_/g, " "));

    const { data } = await apiClient.post("/upload", formData);

    return {
        policyId: data.job_id,
        filename: file.name,
    };
}

export async function getExtraction(jobId: string): Promise<ApiExtractionResult> {
    const { data } = await apiClient.get<ApiExtractionResult>(`/extract/${jobId}`);
    return data;
}

export async function getComparison(jobId: string): Promise<ApiComparisonResult> {
    const { data } = await apiClient.get<ApiComparisonResult>(`/compare/${jobId}`);
    return data;
}

export async function submitReviews(jobId: string, reviews: ApiRuleReview[]): Promise<void> {
    await apiClient.post(`/review/${jobId}`, { reviews });
}

export async function getReport(jobId: string): Promise<ApiReportResult> {
    const { data } = await apiClient.get<ApiReportResult>(`/report/${jobId}`);
    return data;
}

/**
 * Polling helper that queries both extract & compare endpoints
 * to build the JobProgress object for the Upload page stepper.
 */
export async function pollPipeline(jobId: string): Promise<JobProgress> {
    try {
        // We check extraction first
        const ext = await getExtraction(jobId);

        // Default phase mapping
        let phase = ext.status;
        let progress = 0;

        switch (ext.status) {
            case "pending":
            case "queued":
                return { phase: "upload", status: "queued", progress: 0 };
            case "parsing":
                return { phase: "parse", status: "processing", progress: 25 };
            case "extracting":
                return { phase: "extract", status: "processing", progress: 50 };
            case "comparing":
                return { phase: "compare", status: "processing", progress: 75 };
            case "error":
                return { phase: "compare", status: "error", progress: 100, error: "Extraction failed" };
            case "complete":
                // Extraction is complete, or comparing is complete? 
                // We know it's at least compare phase if complete.
                // Let's check comparison endpoint.
                const cmp = await getComparison(jobId);
                if (cmp.status === "complete") {
                    return { phase: "compare", status: "complete", progress: 100 };
                }
                return { phase: "compare", status: cmp.status === "error" ? "error" : "processing", progress: 85 };
            default:
                // fallback
                return { phase: "upload", status: "queued", progress: 0 };
        }
    } catch (error: any) {
        console.error("Pipeline poll error:", error);
        return { phase: "upload", status: "error", progress: 0, error: String(error) };
    }
}
