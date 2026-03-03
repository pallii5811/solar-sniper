export const BACKEND_URL: string = typeof window !== "undefined" ? window.location.origin : "";

export type JobState = "queued" | "running" | "done" | "error";

export type AuditSignals = {
  has_facebook_pixel: boolean;
  has_tiktok_pixel: boolean;
  has_gtm: boolean;
  has_ssl: boolean;
  is_mobile_responsive: boolean;
  missing_instagram: boolean;
  instagram_missing?: boolean;
};

export type BusinessResult = {
  result_index: number;
  business_name: string;
  address?: string | null;
  lat?: number | null;
  lon?: number | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  website_status: "HAS_WEBSITE" | "MISSING_WEBSITE";
  tech_stack?: string;
  load_speed_s?: number | null;
  load_speed?: number | null;
  domain_creation_date?: string | null;
  domain_expiration_date?: string | null;
  website_http_status?: number | null;
  website_error?: string | null;
  website_has_html?: boolean;
  website_error_line?: number | null;
  website_error_hint?: string | null;
  instagram_missing?: boolean | null;
  tiktok_missing?: boolean | null;
  pixel_missing?: boolean | null;
  solar_score?: number;
  solar_potential_bucket?: "LOW" | "GOOD" | "EXCELLENT";
  roof_type?: string;
  plant_estimate?: string;
  estimated_area_m2?: number | null;
  estimated_kwp?: number | null;
  annual_kwh?: number | null;
  annual_co2_tons?: number | null;
  annual_savings_eur?: number | null;
  payback_years?: number | null;
  business_case?: string | null;
  diamond_target?: boolean | null;
  whatsapp_message?: string | null;
  audit: AuditSignals;
};

export type JobStatus = {
  id: string;
  state: JobState;
  progress: number;
  message: string;
  started_at: number;
  finished_at?: number | null;
  error?: string | null;
  results_count?: number;
};

export type TechnicalIssue = {
  code: string;
  severity: string;
  message: string;
  line?: number | null;
  context?: string | null;
};

export type TechnicalAuditResult = {
  url: string;
  final_url: string;
  http_status: number;
  issues: TechnicalIssue[];
  has_critical: boolean;
};

export async function startJob(
  category: string,
  city: string,
  zone?: string,
): Promise<JobStatus> {
  const r = await fetch(`${BACKEND_URL}/api/scrape`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category, city, zone: zone ?? "" }),
  });
  if (!r.ok) {
    let detail = "";
    try {
      const t = await r.text();
      detail = t;
    } catch {
      detail = "";
    }
    throw new Error(`Failed to start job (${r.status}): ${detail}`);
  }
  return (await r.json()) as JobStatus;
}

export async function fetchResults(jobId: string): Promise<BusinessResult[]> {
  const r = await fetch(`${BACKEND_URL}/jobs/${jobId}/results`);
  if (!r.ok) throw new Error("Failed to fetch results");
  return (await r.json()) as BusinessResult[];
}

export async function fetchJob(jobId: string): Promise<JobStatus> {
  const r = await fetch(`${BACKEND_URL}/jobs/${jobId}`);
  if (!r.ok) throw new Error("Failed to fetch job");
  return (await r.json()) as JobStatus;
}

export async function fetchTechnicalAudit(
  jobId: string,
  resultIndex: number,
): Promise<TechnicalAuditResult> {
  const r = await fetch(
    `${BACKEND_URL}/jobs/${jobId}/results/${resultIndex}/technical-audit`,
  );
  if (!r.ok) throw new Error("Failed to fetch technical audit");
  return (await r.json()) as TechnicalAuditResult;
}
