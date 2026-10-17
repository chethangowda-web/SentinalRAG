import type { Page, Route } from "@playwright/test";

export const USER = {
  id: "u1",
  name: "E2E User",
  email: "e2e@example.com",
  created_at: "2026-01-01T00:00:00Z",
  total_documents: 1,
  total_sessions: 0,
  total_evaluations: 0,
  is_admin: false,
};

const json = (route: Route, body: unknown, status = 200) =>
  route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

export function sse(events: [string, unknown][]): string {
  return events.map(([name, data]) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`).join("");
}

export function chatResult(overrides: Record<string, unknown> = {}) {
  return {
    answer: "Customers may request a refund within 30 days [Source 1].",
    confidence: 82.4,
    confidence_level: "HIGH",
    reasoning_path: ["retrieve", "relevance_gate", "ambiguity_check", "confidence_evaluate", "generate_answer"],
    citations: [{ document_id: "d1", filename: "refund_policy.pdf", chunk_id: "c1", page: 2, text: "Refunds within 30 days." }],
    clarification_question: null,
    clarification_needed: false,
    latencies: {},
    trace_id: "t1",
    session_id: "s1",
    graph_execution: [],
    retrieval_details: [],
    confidence_breakdown: null,
    llm_observability: null,
    rewritten_question: null,
    retry_count: 0,
    contradiction_detected: false,
    contradiction_reason: null,
    model_used: "test-model",
    ...overrides,
  };
}

const DOCUMENT = {
  id: "d1",
  filename: "refund_policy.pdf",
  file_type: "pdf",
  status: "embedded",
  pages: 2,
  word_count: 300,
  char_count: 1800,
  ocr_used: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  file_size: 20000,
  chunk_count: 3,
};

/** Pretend to be a signed-in user and answer every API call the pages make on load. */
export async function signedIn(page: Page, theme: "light" | "dark" = "light") {
  await page.addInitScript(
    ([t]) => {
      localStorage.setItem("sentinelrag_token", "e2e-token");
      localStorage.setItem("sentinelrag-theme", t);
    },
    [theme]
  );
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/auth/me")) return json(route, USER);
    if (path.endsWith("/auth/config")) return json(route, { registration_open: true });
    if (path.endsWith("/chat/history/sessions")) return json(route, { total: 0, sessions: [] });
    if (path.endsWith("/documents")) return json(route, [DOCUMENT]);
    if (path.endsWith("/health")) return json(route, { status: "ok", version: "test", uptime_seconds: 60 });
    if (path.endsWith("/dashboard/daily-stats") || path.endsWith("/evaluation/history")) return json(route, []);
    if (path.endsWith("/evaluation/latest")) {
      return json(route, { report: null, run: null, benchmark: { ready: false, loading: false, documents: [] } });
    }
    if (path.endsWith("/evaluations/dashboard")) {
      return json(route, {
        total_evaluated: 0, avg_overall_score: 0, avg_faithfulness: 0, avg_correctness: 0, avg_answer_relevancy: 0,
        avg_context_recall: 0, avg_precision: 0, avg_hallucination_rate: 0, avg_retrieval_score: 0,
        avg_processing_time: 0, total_questions: 0,
      });
    }
    if (path.endsWith("/dashboard/stats")) {
      return json(route, {
        total_documents: 1,
        total_chunks: 3,
        total_sessions: 0,
        docs_by_status: { embedded: 1 },
        total_chars: 1800,
        total_words: 300,
        total_pages: 2,
        avg_ocr_confidence: null,
        document_types: {},
        recent_documents: [],
        avg_response_ms: null,
        self_correction_rate: null,
        questions_answered: 0,
      });
    }
    return json(route, {});
  });
}

function pipeline(answer: string | null, extra: Record<string, unknown> = {}) {
  return {
    answer, confidence_score: 70, confidence_level: "HIGH", latencies: {}, citations: [], reasoning_path: ["retrieve", "generate_answer"],
    contradiction_detected: false, contradiction_reason: null, clarification_needed: false, clarification_question: null, retry_count: 0,
    ...extra,
  };
}

const metric = (baseline: number, sentinel: number) => [{ value: baseline, success: true, error: null, details: {} }, { value: sentinel, success: true, error: null, details: {} }];

export const EVALUATION_REPORT = (() => {
  const keys: [string, number, number][] = [
    ["avg_faithfulness", 0.81, 0.78], ["avg_hallucination", 0.19, 0.22], ["avg_answer_relevancy", 0.26, 0.22],
    ["avg_context_precision", 0.75, 0.76], ["avg_context_recall", 0.7, 0.7], ["avg_correctness", 0.615, 0.624],
    ["avg_unsupported_answer_rate", 0.19, 0.22], ["latency", 6900, 9800],
  ];
  const baseline: Record<string, unknown> = {};
  const sentinel: Record<string, unknown> = {};
  for (const [k, b, s] of keys) {
    const [mb, ms] = metric(b, s);
    baseline[k] = mb;
    sentinel[k] = ms;
  }
  return {
    evaluation_id: "run-1", timestamp: "2026-10-17T10:00:00Z", dataset: "benchmark", total_questions: 3,
    summary: { baseline, sentinel, comparison: {} },
    behaviour: [
      { label: "Specific questions answered", description: "Easy, medium and hard questions get a real answer", total: 1, baseline: 1, sentinel: 1 },
      { label: "Unanswerable questions refused", description: "Questions the documents cannot answer are declined, not invented", total: 1, baseline: 0, sentinel: 1 },
      { label: "Vague questions clarified", description: "Ambiguous questions get a clarifying question", total: 1, baseline: 0, sentinel: 1 },
    ],
    per_question: [
      { id: "1", question: "When does scheduled maintenance take place?", ground_truth: "Every Sunday 02:00-04:00 UTC.", category: "easy", has_contradiction: false, needs_clarification: false, has_context: true,
        baseline: pipeline("Every Sunday between 02:00 and 04:00 UTC [Source 1]."), sentinel: pipeline("Every Sunday between 02:00 and 04:00 UTC [Source 1].", { retry_count: 1 }) },
      { id: "2", question: "What is the 5G standalone roaming charge?", ground_truth: "I don't have enough information to answer this question.", category: "missing_context", has_contradiction: false, needs_clarification: false, has_context: false,
        baseline: pipeline("Based on the retrieved documents (source: d1):\n\nraw text"), sentinel: pipeline("I don't have enough information to answer this question.") },
      { id: "3", question: "What is the deadline?", ground_truth: "Needs clarification.", category: "ambiguous", has_contradiction: false, needs_clarification: true, has_context: true,
        baseline: pipeline("It depends."), sentinel: pipeline(null, { clarification_needed: true, clarification_question: "Which deadline do you mean?" }) },
    ],
    failure_modes: {},
  };
})();

/** Signed in, with a finished evaluation report available. */
export async function withEvaluationReport(page: Page, theme: "light" | "dark" = "light") {
  await signedIn(page, theme);
  await page.route("**/api/v1/evaluation/latest", (route) =>
    json(route, { report: EVALUATION_REPORT, run: { evaluation_id: "run-1", status: "completed", progress: 3, total: 3, error: null }, benchmark: { ready: true, loading: false, documents: [] } })
  );
  await page.route("**/api/v1/evaluation/history", (route) => json(route, [{ evaluation_id: "run-1", timestamp: "2026-10-17T10:00:00Z", total_questions: 3, dataset: "benchmark" }]));
}
