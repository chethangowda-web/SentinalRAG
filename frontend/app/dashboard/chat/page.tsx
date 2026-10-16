"use client";

import {
  useState,
  useRef,
  useEffect,
  useCallback,
  useMemo,
} from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useQueryClient } from "@tanstack/react-query";
import {
  useChatSessions,
  useChatSessionMessages,
  useUpdateSession,
  useDeleteSession,
  useClearSessionMessages,
} from "@/hooks/use-chat";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { streamChatMessage } from "@/services/chat";
import { useDocuments } from "@/hooks/use-documents";
import { rerankPercent } from "@/lib/utils";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  Send,
  MessageSquare,
  Copy,
  Check,
  RefreshCw,
  Trash2,
  Sparkles,
  User,
  Download,
  Search,
  FileText,
  ThumbsUp,
  ThumbsDown,
  Gauge,
  Brain,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  BookOpen,
  PanelLeftClose,
  PanelLeft,
  Plus,
  MoreHorizontal,
  Pin,
  PinOff,
  PencilLine,
  Clock,
  Shield,
  Layers,
  ArrowUpDown,
  Lightbulb,
  ChevronDown,
  ExternalLink,
} from "lucide-react";
import type {
  ChatResponse,
  ChatStepEvent,
  CitationItem,
  GraphExecutionStep,
  ChatSession,
  RetrievalDetailItem,
  Document as DocumentItem,
} from "@/types";

/** Plain-language labels for the pipeline nodes streamed while an answer is produced. */
const STEP_LABELS: Record<string, string> = {
  retrieve: "Searched your documents",
  ambiguity_check: "Checked the question is specific enough",
  confidence_evaluate: "Checked retrieval confidence",
  rewrite_query: "Rewrote the question for a better search",
  retry_retrieve: "Searched again with the rewritten question",
  contradiction_detect: "Checked sources for contradictions",
  clarification: "Looked for ambiguity in the question",
  generate_answer: "Wrote the answer from the sources",
  fallback: "Not enough evidence — preparing a safe reply",
  relevance_gate: "Checked the documents cover this topic",
};

/* ─── types ─────────────────────────────────────────── */

interface Message {
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
}

/* ─── helpers ───────────────────────────────────────── */

const stageLabels: Record<string, string> = {
  retrieve: "Searching document knowledge base",
  rewrite_query: "Rewriting your question for better results",
  retry_retrieve: "Re-searching with improved query",
  confidence_evaluate: "Checking confidence in the evidence",
  contradiction_detect: "Scanning for contradictions in evidence",
  clarification: "Asking for clarification",
  generate_answer: "Generating final answer from evidence",
  fallback_low_confidence: "Falling back — confidence too low",
  __start__: "Starting pipeline",
  __end__: "Pipeline complete",
};

const stageIcons: Record<string, React.ReactNode> = {
  retrieve: <Search className="h-3 w-3" />,
  rewrite_query: <PencilLine className="h-3 w-3" />,
  retry_retrieve: <RefreshCw className="h-3 w-3" />,
  confidence_evaluate: <Shield className="h-3 w-3" />,
  contradiction_detect: <AlertTriangle className="h-3 w-3" />,
  clarification: <MessageSquare className="h-3 w-3" />,
  generate_answer: <Sparkles className="h-3 w-3" />,
  fallback_low_confidence: <XCircle className="h-3 w-3" />,
};

function formatLatency(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${ms.toFixed(0)}ms`;
}

function getSourceFilename(cit: CitationItem) {
  return cit.filename || cit.document_id?.substring(0, 12) + "…";
}

function confidenceColor(level: string) {
  switch (level) {
    case "HIGH":
      return "text-confidence-high";
    case "MEDIUM":
      return "text-confidence-medium";
    default:
      return "text-confidence-low";
  }
}

function confidenceBg(level: string) {
  switch (level) {
    case "HIGH":
      return "bg-confidence-high-bg border-confidence-high/30";
    case "MEDIUM":
      return "bg-confidence-medium-bg border-confidence-medium/30";
    default:
      return "bg-confidence-low-bg border-confidence-low/30";
  }
}

function confidenceBar(level: string) {
  switch (level) {
    case "HIGH":
      return "bg-confidence-high";
    case "MEDIUM":
      return "bg-confidence-medium";
    default:
      return "bg-confidence-low";
  }
}

/* ─── Confidence Breakdown Component ────────────────── */

function ConfidenceBreakdown({
  breakdown,
}: {
  breakdown: NonNullable<ChatResponse["confidence_breakdown"]>;
}) {
  const bars = [
    { label: "Vector Similarity", value: breakdown.vector_similarity * 100, color: "hsl(var(--chart-1))" },
    { label: "Content Coverage", value: breakdown.coverage * 100, color: "hsl(var(--chart-2))" },
    { label: "Cross-Encoder", value: breakdown.cross_encoder_score * 100, color: "hsl(var(--chart-3))" },
    { label: "Citation Strength", value: Math.min(breakdown.citation_count * 20, 100), color: "hsl(var(--chart-4))" },
  ];

  return (
    <div className="rounded-lg border bg-card">
      <div className="px-3 py-2 text-xs font-medium text-muted-foreground flex items-center gap-1.5 border-b">
        <Shield className="h-3.5 w-3.5" />
        Confidence Breakdown
      </div>
      <div className="space-y-2 px-3 py-2">
        {bars.map((bar) => (
          <div key={bar.label} className="space-y-0.5">
            <div className="flex justify-between text-[10px]">
              <span className="text-muted-foreground">{bar.label}</span>
              <span className="font-medium tabular-nums">{bar.value.toFixed(0)}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(bar.value, 100)}%` }}
                transition={{ duration: 0.6, ease: "easeOut" }}
                className="h-full rounded-full"
                style={{ backgroundColor: bar.color }}
              />
            </div>
          </div>
        ))}
        <div className="pt-1.5 border-t text-[10px] text-muted-foreground flex justify-between">
          <span>Raw score: {breakdown.raw_score.toFixed(3)}</span>
          <span>Final: {breakdown.final_score.toFixed(3)}</span>
          <span>Contradictions: {breakdown.contradiction_status}</span>
        </div>
      </div>
    </div>
  );
}

/* ─── Smarter Suggestions Component ─────────────────── */

/* ─── Reasoning Timeline Component ──────────────────── */

function ReasoningTimelineMini({
  graphExecution,
  isExpanded,
  onToggle,
}: {
  graphExecution: GraphExecutionStep[];
  isExpanded: boolean;
  onToggle: () => void;
}) {
  if (!graphExecution || graphExecution.length === 0) return null;
  return (
    <div className="rounded-lg border bg-card">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
      >
        <span className="flex items-center gap-1.5">
          <Brain className="h-3.5 w-3.5" />
          Pipeline Execution ({graphExecution.length} steps,{" "}
          {formatLatency(
            graphExecution.reduce((a, s) => a + s.execution_time_ms, 0)
          )}
          )
        </span>
        <ArrowUpDown className="h-3 w-3" />
      </button>
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t"
          >
            <div className="space-y-0 px-3 py-2">
              {graphExecution.map((step, si) => {
                const isLast = si === graphExecution.length - 1;
                const ico = stageIcons[step.node_name] || (
                  <Brain className="h-3 w-3" />
                );
                return (
                  <div
                    key={si}
                    className={cn(
                      "flex items-start gap-2 py-1.5 text-xs",
                      isLast
                        ? "text-foreground"
                        : "text-muted-foreground"
                    )}
                  >
                    <div
                      className={cn(
                        "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full",
                        isLast
                          ? "bg-primary/10 text-primary"
                          : "bg-muted"
                      )}
                    >
                      {ico}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="truncate font-medium">
                          {stageLabels[step.node_name] || step.node_name}
                        </span>
                        <span className="shrink-0 text-[10px] font-system-mono tabular-nums text-muted-foreground">
                          {formatLatency(step.execution_time_ms)}
                        </span>
                      </div>
                      {step.decision && (
                        <p className="truncate text-[10px] text-muted-foreground mt-0.5">
                          → {step.decision}
                        </p>
                      )}
                      {step.input && (
                        <p className="truncate text-[10px] text-muted-foreground">
                          in: {step.input}
                        </p>
                      )}
                      {step.output && (
                        <p className="truncate text-[10px] text-muted-foreground">
                          out: {step.output}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ─── Evidence Panel Component ──────────────────────── */

function EvidencePanel({
  retrievalDetails,
  isExpanded,
  onToggle,
}: {
  retrievalDetails: RetrievalDetailItem[];
  isExpanded: boolean;
  onToggle: () => void;
}) {
  if (!retrievalDetails || retrievalDetails.length === 0) return null;
  return (
    <div className="rounded-lg border bg-card">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
      >
        <span className="flex items-center gap-1.5">
          <BookOpen className="h-3.5 w-3.5" />
          Retrieved Evidence ({retrievalDetails.length} chunks)
        </span>
        <ArrowUpDown className="h-3 w-3" />
      </button>
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t"
          >
            <div className="space-y-2 px-3 py-2">
              {retrievalDetails.map((rd, ri) => (
                <div
                  key={ri}
                  className={cn(
                    "rounded-md border p-2.5 text-xs",
                    rd.selected
                      ? "border-primary/20 bg-primary/5"
                      : "border-border/50 bg-muted/30 opacity-60"
                  )}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center gap-1.5">
                      <Badge
                        variant={rd.selected ? "default" : "outline"}
                        className="text-[10px] h-5 px-1.5"
                      >
                        #{rd.final_rank}
                      </Badge>
                      <span className="text-muted-foreground truncate max-w-[120px]">
                        {rd.document_id.slice(0, 10)}…
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-muted-foreground tabular-nums">
                      <span>V:{rd.vector_score.toFixed(3)}</span>
                      <span>Relevance {rerankPercent(rd.rerank_score)}%</span>
                    </div>
                  </div>
                  <p className="leading-relaxed line-clamp-2 text-muted-foreground">
                    {rd.text}
                  </p>
                  {rd.reason && (
                    <p className="text-[10px] text-muted-foreground mt-1 italic">
                      {rd.reason}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ─── Citations Component ───────────────────────────── */

function CitationsRow({
  citations,
  onCitationClick,
}: {
  citations: CitationItem[];
  onCitationClick?: (c: CitationItem) => void;
}) {
  if (!citations || citations.length === 0) return null;
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
        Sources ({citations.length})
      </p>
      <div className="flex flex-wrap gap-2">
        {citations.map((cit, ci) => (
          <button
            key={ci}
            onClick={() => onCitationClick?.(cit)}
            className="group relative flex items-center gap-2 rounded-lg border border-border/60 bg-card px-3 py-2 text-[11px] text-muted-foreground hover:border-primary/40 hover:bg-primary/5 hover:shadow-sm transition-all duration-200"
          >
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-primary/10 text-[9px] font-bold text-primary group-hover:bg-primary/20 transition-colors">
              {cit.source ?? ci + 1}
            </span>
            <FileText className="h-3 w-3 shrink-0 text-muted-foreground" />
            <span className="max-w-[90px] truncate font-medium">
              {getSourceFilename(cit)}
            </span>
            {cit.page != null && (
              <span className="text-[10px] text-muted-foreground">p.{cit.page}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ─── Action Buttons ────────────────────────────────── */

function ActionButtons({
  content,
  response,
  index,
  copiedId,
  onCopy,
  onRegenerate,
  onExport,
  feedback,
  onFeedback,
}: {
  content: string;
  response?: ChatResponse;
  index: number;
  copiedId: string | null;
  onCopy: (text: string, id: string) => void;
  onRegenerate: () => void;
  onExport: (r: ChatResponse) => void;
  feedback: "up" | "down" | null;
  onFeedback: (v: "up" | "down" | null) => void;
}) {
  return (
    <div className="flex items-center gap-1 pt-1">
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              aria-label="Copy answer"
              onClick={() => onCopy(content, `copy-${index}`)}
            >
              {copiedId === `copy-${index}` ? (
                <Check className="h-3.5 w-3.5 text-green-500" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>Copy answer</TooltipContent>
        </Tooltip>
      </TooltipProvider>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              aria-label="Regenerate answer"
              onClick={onRegenerate}
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Regenerate</TooltipContent>
        </Tooltip>
      </TooltipProvider>
      {response && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0"
                aria-label="Export answer"
                onClick={() => onExport(response)}
              >
                <Download className="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Export</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
      <div className="ml-auto flex items-center gap-1">
        <span className="text-[10px] text-muted-foreground mr-0.5">
          Feedback
        </span>
        <Button
          variant="ghost"
          size="sm"
          aria-label="Good answer"
          aria-pressed={feedback === "up"}
          className={cn(
            "h-7 w-7 p-0",
            feedback === "up" && "text-green-500"
          )}
          onClick={() =>
            onFeedback(feedback === "up" ? null : "up")
          }
        >
          <ThumbsUp className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          aria-label="Poor answer"
          aria-pressed={feedback === "down"}
          className={cn(
            "h-7 w-7 p-0",
            feedback === "down" && "text-red-500"
          )}
          onClick={() =>
            onFeedback(feedback === "down" ? null : "down")
          }
        >
          <ThumbsDown className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

/* ─── Answer presentation helpers ───────────────────── */

/** Turn "[Source 2]" markers into links the markdown renderer shows as small numbered badges. */
function withSourceLinks(text: string): string {
  return text.replace(/\[Source (\d+)\]/g, "[$1](#source-$1)");
}

function sourceBadgeComponents(
  citations: CitationItem[] | undefined,
  open: (c: CitationItem) => void
) {
  return {
    a: ({ href, children }: { href?: string; children?: React.ReactNode }) => {
      const match = href?.match(/^#source-(\d+)$/);
      if (!match) {
        return (
          <a href={href} target="_blank" rel="noreferrer">
            {children}
          </a>
        );
      }
      const n = Number(match[1]);
      const citation = citations?.find((c) => (c.source ?? 0) === n);
      return (
        <button
          type="button"
          disabled={!citation}
          onClick={() => citation && open(citation)}
          aria-label={`Open source ${n}`}
          title={citation ? `Source ${n}: ${citation.filename ?? "document"}` : `Source ${n}`}
          className="mx-0.5 inline-flex h-[18px] min-w-[18px] -translate-y-px items-center justify-center rounded-md bg-primary/10 px-1 align-middle text-[10px] font-semibold text-primary hover:bg-primary/20 disabled:cursor-default"
        >
          {n}
        </button>
      );
    },
  };
}

function answerSeconds(r: ChatResponse): string {
  const ms = Object.entries(r.latencies ?? {})
    .filter(([k]) => k.endsWith("_node"))
    .reduce((sum, [, v]) => sum + v, 0);
  return ms > 0 ? formatLatency(ms) : "--";
}

/** One quiet line under the answer: how sure it is, how long it took. Details live behind a toggle. */
function AnswerSummary({ response }: { response: ChatResponse }) {
  const level = response.confidence_level;
  const label = level === "HIGH" ? "High confidence" : level === "MEDIUM" ? "Medium confidence" : "Low confidence";
  return (
    <div className="mb-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
      <span className="inline-flex items-center gap-1.5 font-medium text-foreground">
        <span
          className={cn(
            "h-2 w-2 rounded-full",
            level === "HIGH" && "bg-confidence-high",
            level === "MEDIUM" && "bg-confidence-medium",
            level === "LOW" && "bg-confidence-low"
          )}
        />
        {label}
        <span className="font-normal text-muted-foreground">({Math.round(response.confidence)}%)</span>
      </span>
      <span>{answerSeconds(response)}</span>
      {response.retry_count > 0 && <span>searched again {response.retry_count}×</span>}
      {response.model_used && <span className="hidden sm:inline">{response.model_used}</span>}
    </div>
  );
}

/** What the chat shows before the first question: example questions drawn from the user's own documents. */
function StarterQuestions({
  documents,
  scopedDocumentId,
  onPick,
}: {
  documents: DocumentItem[];
  scopedDocumentId: string | null;
  onPick: (q: string) => void;
}) {
  const indexed = documents.filter((d) => d.status === "embedded" || d.status === "completed");
  const scoped = scopedDocumentId ? indexed.find((d) => d.id === scopedDocumentId) : undefined;
  const pool = scoped ? [scoped] : indexed;
  const name = (d: DocumentItem) => d.filename.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ");
  const suggestions = pool.length
    ? [
        `Summarize ${name(pool[0])}`,
        pool.length > 1 ? `How does ${name(pool[0])} differ from ${name(pool[1])}?` : `What are the key points in ${name(pool[0])}?`,
        `What dates, limits or deadlines are mentioned in ${scoped ? name(scoped) : "my documents"}?`,
      ]
    : [];

  return (
    <div className="mx-auto flex max-w-xl flex-col items-center text-center">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
        <Sparkles className="h-7 w-7 text-primary" />
      </div>
      <h2 className="text-2xl font-semibold tracking-tight">
        {scoped ? `Ask about ${name(scoped)}` : "What would you like to know?"}
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        {indexed.length === 0
          ? "Upload a document first, then ask questions and get answers with sources."
          : `Answers come only from your ${scoped ? "document" : `${indexed.length} document${indexed.length === 1 ? "" : "s"}`}, with the source shown next to every claim.`}
      </p>
      {suggestions.length > 0 ? (
        <div className="mt-6 grid w-full gap-2">
          {suggestions.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => onPick(q)}
              className="rounded-xl border bg-card px-4 py-3 text-left text-sm shadow-sm transition-colors hover:border-primary/40 hover:bg-primary/5"
            >
              {q}
            </button>
          ))}
        </div>
      ) : (
        <Link href="/dashboard/upload">
          <Button className="mt-6">Upload a document</Button>
        </Link>
      )}
    </div>
  );
}

/* ─── Main Chat Page ────────────────────────────────── */

export default function ChatPage() {
  const qc = useQueryClient();
  const searchParams = useSearchParams();
  const router = useRouter();
  const chatDocumentId = searchParams.get("document_id");

  /* state */
  // Closed until we know the screen is wide enough: a 280px panel leaves no room for chat on a phone.
  const [sidebarOpen, setSidebarOpen] = useState(false);
  useEffect(() => {
    if (window.matchMedia("(min-width: 1024px)").matches) setSidebarOpen(true);
  }, []);
  const [searchQuery, setSearchQuery] = useState("");
  const [renameId, setRenameId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [feedbackGiven, setFeedbackGiven] = useState<
    Record<string, "up" | "down" | null>
  >({});
  const [isStreaming, setIsStreaming] = useState(false);
  const [liveSteps, setLiveSteps] = useState<ChatStepEvent[]>([]);
  const [liveAnswer, setLiveAnswer] = useState("");
  const [streamError, setStreamError] = useState<string | null>(null);
  const [expandedReasoning, setExpandedReasoning] = useState<
    Record<string, boolean>
  >({});
  const [expandedEvidence, setExpandedEvidence] = useState<
    Record<string, boolean>
  >({});
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState<CitationItem | null>(null);
  const [expandedDetails, setExpandedDetails] = useState<Record<string, boolean>>({});
  const { data: documents } = useDocuments();

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  /* queries */
  const { data: sessionsData, isLoading: sessionsLoading } =
    useChatSessions({ search: searchQuery || undefined });
  const { data: sessionMessages, refetch: refetchMessages } =
    useChatSessionMessages(activeSessionId);
  const updateSessionMut = useUpdateSession();
  const deleteSessionMut = useDeleteSession();
  const clearMessagesMut = useClearSessionMessages();

  const sessions = useMemo(
    () => sessionsData?.sessions ?? [],
    [sessionsData]
  );

  /* load messages when session changes */
  useEffect(() => {
    if (sessionMessages && sessionMessages.length > 0) {
      const loaded = sessionMessages.map((m) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
        response: m.response ?? undefined,
      }));
      setMessages(loaded);
    } else if (activeSessionId && sessionMessages?.length === 0) {
      setMessages([]);
    }
  }, [sessionMessages, activeSessionId]);

  /* scroll */
  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  /* send */
  const sendQuestion = useCallback(async (question: string, skipClarification = false) => {
    if (!question || isStreaming) return;

    setIsStreaming(true);
    setLiveSteps([]);
    setLiveAnswer("");
    setStreamError(null);

    const userMsg: Message = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const response = await streamChatMessage(
        {
          question,
          session_id: activeSessionId,
          document_id: chatDocumentId || undefined,
          skip_clarification: skipClarification || undefined,
        },
        (step) => setLiveSteps((prev) => [...prev, step]),
        (text) => setLiveAnswer((prev) => prev + text)
      );

      const assistantMsg: Message = {
        role: "assistant",
        content: response.answer,
        response,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      if (!activeSessionId && response.session_id) {
        setActiveSessionId(response.session_id);
      }

      qc.invalidateQueries({ queryKey: ["chat-sessions"] });
      if (response.session_id) {
        qc.invalidateQueries({
          queryKey: ["chat-session-messages", response.session_id],
        });
      }
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Request failed";
      setStreamError(msg);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Sorry, I encountered an error: ${msg}`,
        },
      ]);
    } finally {
      setIsStreaming(false);
      setLiveSteps([]);
      setLiveAnswer("");
    }
  }, [isStreaming, activeSessionId, chatDocumentId, qc]);

  // A question typed on the dashboard arrives as ?q=...; ask it once, then drop it from the URL
  const initialQuestion = searchParams.get("q");
  const askedInitial = useRef(false);
  useEffect(() => {
    if (initialQuestion && !askedInitial.current) {
      askedInitial.current = true;
      router.replace(chatDocumentId ? `/dashboard/chat?document_id=${chatDocumentId}` : "/dashboard/chat");
      sendQuestion(initialQuestion);
    }
  }, [initialQuestion, chatDocumentId, router, sendQuestion]);

  const handleSend = useCallback(() => {
    const question = input.trim();
    if (!question) return;
    setInput("");
    sendQuestion(question);
  }, [input, sendQuestion]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  /* copy */
  const handleCopy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  /* regenerate (remove last assistant msg, keep input) */
  const handleRegenerate = () => {
    const lastUserIdx = [...messages]
      .reverse()
      .findIndex((m) => m.role === "user");
    if (lastUserIdx >= 0) {
      const actualIdx = messages.length - 1 - lastUserIdx;
      const lastUserMsg = messages[actualIdx];
      setMessages((prev) => prev.slice(0, actualIdx));
      setInput(lastUserMsg.content);
    }
  };

  /* export */
  const handleExport = (response: ChatResponse) => {
    const userText =
      messages.find((m) => m.response === response)?.content ?? "";
    const text = [
      `# SentinelRAG Chat Export`,
      ``,
      `**Query:** ${userText}`,
      `**Answer:** ${response.answer}`,
      `**Confidence:** ${response.confidence_level} (${response.confidence}%)`,
      `**Citations:** ${response.citations?.length || 0}`,
      `**Trace:** ${response.trace_id}`,
      `**Model:** ${response.model_used || "unknown"}`,
      ``,
      response.confidence_breakdown
        ? `**Confidence Breakdown:**\n- Vector: ${response.confidence_breakdown.vector_similarity}\n- Cross-encoder: ${response.confidence_breakdown.cross_encoder_score}\n- Coverage: ${response.confidence_breakdown.coverage}`
        : "",
    ]
      .filter(Boolean)
      .join("\n");

    const blob = new Blob([text], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sentinelrag-chat-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  /* session handlers */
  const handleNewSession = async () => {
    setActiveSessionId(null);
    setMessages([]);
    setInput("");
    setStreamError(null);
  };

  const handleSelectSession = (sid: string) => {
    setActiveSessionId(sid);
    setMessages([]);
  };

  const handleRenameSession = (sid: string, currentTitle: string) => {
    setRenameId(sid);
    setRenameValue(currentTitle);
  };

  const handleRenameSubmit = async () => {
    if (renameId && renameValue.trim()) {
      await updateSessionMut.mutateAsync({
        sessionId: renameId,
        title: renameValue.trim(),
      });
    }
    setRenameId(null);
  };

  const handleTogglePin = async (sid: string, pinned: boolean) => {
    await updateSessionMut.mutateAsync({ sessionId: sid, pinned: !pinned });
  };

  const handleDeleteConfirm = async () => {
    if (confirmDeleteId) {
      await deleteSessionMut.mutateAsync(confirmDeleteId);
      if (activeSessionId === confirmDeleteId) {
        setActiveSessionId(null);
        setMessages([]);
      }
      setConfirmDeleteId(null);
    }
  };

  /* compute total latency */
  const totalLatency = useCallback(
    (r: ChatResponse) => {
      if (!r.latencies) return "--";
      return formatLatency(
        Object.values(r.latencies).reduce((a, b) => a + b, 0)
      );
    },
    []
  );

  return (
    <ErrorBoundary>
      <div className="flex h-[calc(100vh-4rem)]">
        {/* ── Sidebar ── */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.aside aria-label="Chat history"
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 280, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              className="shrink-0 border-r bg-card overflow-hidden"
            >
              <div className="flex h-full flex-col">
                {/* header */}
                <div className="flex items-center justify-between border-b px-3 py-2.5">
                  <span className="text-sm font-semibold">Chat History</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2"
                    onClick={handleNewSession}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    New
                  </Button>
                </div>

                {/* search */}
                <div className="border-b px-3 py-2">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                    <input
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search sessions…"
                      className="w-full rounded-md border border-input bg-background py-1.5 pl-8 pr-3 text-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    />
                  </div>
                </div>

                {/* list */}
                <ScrollArea className="flex-1 [&>div>div]:!block">
                  {sessionsLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    </div>
                  ) : sessions.length === 0 ? (
                    <div className="flex flex-col items-center py-8 text-center px-4">
                      <MessageSquare className="h-8 w-8 text-muted-foreground mb-2" />
                      <p className="text-xs text-muted-foreground">
                        {searchQuery
                          ? "No sessions match your search"
                          : "No chat history yet"}
                      </p>
                    </div>
                  ) : (
                    <div className="py-1">
                      {sessions.map((s) => (
                        <div
                          key={s.id}
                          className={cn(
                            "group flex items-center gap-2 px-3 py-2.5 text-sm cursor-pointer transition-colors",
                            activeSessionId === s.id
                              ? "bg-primary/10 text-foreground"
                              : "text-muted-foreground hover:bg-muted/50"
                          )}
                        >
                          {renameId === s.id ? (
                            <div className="flex w-full items-center gap-1">
                              <input
                                autoFocus
                                value={renameValue}
                                onChange={(e) =>
                                  setRenameValue(e.target.value)
                                }
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") handleRenameSubmit();
                                  if (e.key === "Escape") setRenameId(null);
                                }}
                                onBlur={handleRenameSubmit}
                                className="flex-1 rounded border border-input bg-background px-2 py-1 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                              />
                            </div>
                          ) : (
                            <>
                              <div
                                className="flex-1 min-w-0"
                                onClick={() => handleSelectSession(s.id)}
                              >
                                <p className="truncate text-xs font-medium">
                                  {s.title}
                                </p>
                                <div className="flex items-center gap-2 mt-0.5">
                                  <span className="text-[10px] text-muted-foreground">
                                    {s.message_count} msgs
                                  </span>
                                  {s.last_confidence_level && (
                                    <span
                                      className="inline-flex items-center gap-1 text-[10px] text-muted-foreground"
                                      title={`${s.last_confidence_level.toLowerCase()} confidence`}
                                    >
                                      <span
                                        className={cn(
                                          "h-1.5 w-1.5 rounded-full",
                                          s.last_confidence_level === "HIGH" && "bg-confidence-high",
                                          s.last_confidence_level === "MEDIUM" && "bg-confidence-medium",
                                          s.last_confidence_level === "LOW" && "bg-confidence-low"
                                        )}
                                      />
                                      {s.last_confidence_level.toLowerCase()}
                                    </span>
                                  )}
                                  {s.pinned && (
                                    <Pin className="h-2.5 w-2.5 text-muted-foreground" />
                                  )}
                                </div>
                              </div>
                              <div className="flex shrink-0 items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-6 w-6 p-0"
                                        aria-label={s.pinned ? "Unpin chat" : "Pin chat"}
                                        onClick={() =>
                                          handleTogglePin(s.id, s.pinned)
                                        }
                                      >
                                        {s.pinned ? (
                                          <PinOff className="h-3 w-3" />
                                        ) : (
                                          <Pin className="h-3 w-3" />
                                        )}
                                      </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                      {s.pinned ? "Unpin" : "Pin"}
                                    </TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-6 w-6 p-0"
                                        aria-label="Rename chat"
                                        onClick={() =>
                                          handleRenameSession(s.id, s.title)
                                        }
                                      >
                                        <PencilLine className="h-3 w-3" />
                                      </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>Rename</TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-6 w-6 p-0 text-destructive"
                                        aria-label="Delete chat"
                                        onClick={() =>
                                          setConfirmDeleteId(s.id)
                                        }
                                      >
                                        <Trash2 className="h-3 w-3" />
                                      </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>Delete</TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                              </div>
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </div>
            </motion.aside>
          )}
        </AnimatePresence>

          {/* ── Main ── */}
        <div className="flex flex-1 flex-col min-w-0">
          {/* header */}
          <div className="flex items-center justify-between border-b px-3 sm:px-4 py-2.5">
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                aria-label={sidebarOpen ? "Hide chat history" : "Show chat history"}
                aria-expanded={sidebarOpen}
                onClick={() => setSidebarOpen(!sidebarOpen)}
              >
                {sidebarOpen ? (
                  <PanelLeftClose className="h-4 w-4" />
                ) : (
                  <PanelLeft className="h-4 w-4" />
                )}
              </Button>
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
                  <MessageSquare className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <h1 className="text-sm font-bold tracking-tight">Chat</h1>
                  <p className="text-[10px] text-muted-foreground hidden sm:block">
                    Ask questions about your documents
                  </p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {messages.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={handleNewSession}
                >
                  <Plus className="h-3.5 w-3.5 mr-1" />
                  <span className="hidden sm:inline">New Chat</span>
                </Button>
              )}
            </div>
          </div>

          {/* messages */}
          <ScrollArea className="flex-1 px-3 sm:px-4" ref={scrollRef}>
            <AnimatePresence mode="wait">
              {messages.length === 0 && !isStreaming ? (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex min-h-full items-center justify-center px-4 py-10"
                >
                  <StarterQuestions
                    documents={documents ?? []}
                    scopedDocumentId={chatDocumentId}
                    onPick={(q) => sendQuestion(q)}
                  />
                </motion.div>
              ) : (
                <motion.div
                  key="messages"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="space-y-4 sm:space-y-5 py-4 max-w-3xl mx-auto"
                >
                  {messages.map((msg, i) => (
                    <motion.div
                      key={`${i}-${msg.role}`}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.2 }}
                      className={`flex gap-2 sm:gap-3 ${
                        msg.role === "user" ? "justify-end" : "justify-start"
                      }`}
                    >
                      {/* assistant avatar */}
                      {msg.role === "assistant" && (
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 mt-1">
                          <Sparkles className="h-3.5 w-3.5 text-primary" />
                        </div>
                      )}

                      <div
                        className={cn(
                          msg.role === "user" ? "order-first" : "",
                          msg.role === "user"
                            ? "max-w-[85%] sm:max-w-[70%]"
                            : "w-full sm:max-w-[90%] min-w-0"
                        )}
                      >
                        {msg.role === "user" ? (
                          <div className="rounded-2xl bg-primary px-3.5 py-2.5 sm:px-4 text-primary-foreground shadow-sm">
                            <p className="text-sm whitespace-pre-wrap leading-relaxed">
                              {msg.content}
                            </p>
                          </div>
                        ) : (
                          <div className="space-y-2.5">
                            {/* Answer Card */}
                            <Card className="overflow-hidden border-border/60 shadow-sm">
                              <CardContent className="p-0">
                                {/* answer body */}
                                <div className="px-5 py-4">
                                  <div className="prose dark:prose-invert max-w-none text-[15px] leading-relaxed prose-p:my-2">
                                    <ReactMarkdown
                                      remarkPlugins={[remarkGfm]}
                                      components={sourceBadgeComponents(msg.response?.citations, setShowPreview)}
                                    >
                                      {withSourceLinks(msg.content)}
                                    </ReactMarkdown>
                                  </div>
                                </div>

                                {/* citations */}
                                {msg.response && (
                                  <div className="border-t px-4 py-2.5">
                                    <CitationsRow
                                      citations={msg.response.citations}
                                      onCitationClick={setShowPreview}
                                    />
                                  </div>
                                )}

                                {/* actions */}
                                {msg.response && (
                                  <div className="border-t px-4 py-1.5">
                                    <AnswerSummary response={msg.response} />
                                    <ActionButtons
                                      content={msg.content}
                                      response={msg.response}
                                      index={i}
                                      copiedId={copiedId}
                                      onCopy={handleCopy}
                                      onRegenerate={handleRegenerate}
                                      onExport={handleExport}
                                      feedback={
                                        feedbackGiven[`msg-${i}`] ?? null
                                      }
                                      onFeedback={(v) =>
                                        setFeedbackGiven((prev) => ({
                                          ...prev,
                                          [`msg-${i}`]: v,
                                        }))
                                      }
                                    />
                                  </div>
                                )}
                              </CardContent>
                            </Card>

                            {/* How this answer was made */}
                            {msg.response && (
                              <div>
                                <button
                                  type="button"
                                  onClick={() => setExpandedDetails((prev) => ({ ...prev, [`msg-${i}`]: !prev[`msg-${i}`] }))}
                                  aria-expanded={expandedDetails[`msg-${i}`] ?? false}
                                  className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                                >
                                  <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", (expandedDetails[`msg-${i}`] ?? false) && "rotate-180")} />
                                  How this answer was made
                                </button>
                                {(expandedDetails[`msg-${i}`] ?? false) && (
                                  <div className="mt-2 space-y-2.5">
                            {/* Reasoning Timeline */}
                            {msg.response &&
                              msg.response.graph_execution &&
                              msg.response.graph_execution.length > 0 && (
                                <ReasoningTimelineMini
                                  graphExecution={
                                    msg.response.graph_execution
                                  }
                                  isExpanded={
                                    expandedReasoning[`msg-${i}`] ?? false
                                  }
                                  onToggle={() =>
                                    setExpandedReasoning((prev) => ({
                                      ...prev,
                                      [`msg-${i}`]: !prev[`msg-${i}`],
                                    }))
                                  }
                                />
                              )}

                            {/* Evidence Panel */}
                            {msg.response &&
                              msg.response.retrieval_details &&
                              msg.response.retrieval_details.length > 0 && (
                                <EvidencePanel
                                  retrievalDetails={
                                    msg.response.retrieval_details
                                  }
                                  isExpanded={
                                    expandedEvidence[`msg-${i}`] ?? false
                                  }
                                  onToggle={() =>
                                    setExpandedEvidence((prev) => ({
                                      ...prev,
                                      [`msg-${i}`]: !prev[`msg-${i}`],
                                    }))
                                  }
                                />
                              )}

                            {/* Confidence Breakdown */}
                            {msg.response?.confidence_breakdown && (
                              <ConfidenceBreakdown
                                breakdown={msg.response.confidence_breakdown}
                              />
                            )}

                                  </div>
                                )}
                              </div>
                            )}

                            {/* Low confidence warning */}
                            {msg.response &&
                              msg.response.confidence_level === "LOW" && (
                                <div className="rounded-lg border border-confidence-low/30 bg-confidence-low-bg px-3 py-2.5">
                                  <div className="flex items-start gap-2">
                                    <AlertTriangle className="h-4 w-4 text-confidence-low shrink-0 mt-0.5" />
                                    <div>
                                      <p className="text-xs font-medium text-confidence-low">
                                        Low Confidence Response
                                      </p>
                                      <p className="text-[11px] text-confidence-low/70 mt-0.5">
                                        The model had low confidence (
                                        {msg.response.confidence}%) in this
                                        answer. The retrieved evidence may be
                                        insufficient. Consider rephrasing your
                                        question or uploading more relevant
                                        documents.
                                      </p>
                                    </div>
                                  </div>
                                </div>
                              )}

                            {/* clarification */}
                            {msg.response?.clarification_needed &&
                              msg.response.clarification_question && (
                                <div className="rounded-lg border border-blue-200 bg-blue-50/50 dark:border-blue-800/50 dark:bg-blue-950/20 px-3 py-2.5">
                                  <div className="flex items-start gap-2">
                                    <MessageSquare className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />
                                    <div>
                                      <p className="text-xs font-medium text-blue-700 dark:text-blue-400">
                                        Clarification Needed
                                      </p>
                                      <p className="text-[11px] text-blue-600/70 dark:text-blue-400/70 mt-0.5">
                                        {msg.response.clarification_question}
                                      </p>
                                      {i > 0 && messages[i - 1].role === "user" && (
                                        <Button
                                          variant="outline"
                                          size="sm"
                                          className="mt-2 h-7 text-xs"
                                          disabled={isStreaming}
                                          onClick={() => sendQuestion(messages[i - 1].content, true)}
                                        >
                                          Answer anyway
                                        </Button>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              )}
                          </div>
                        )}
                      </div>

                      {/* user avatar */}
                      {msg.role === "user" && (
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary mt-0.5">
                          <User className="h-3.5 w-3.5 text-primary-foreground" />
                        </div>
                      )}
                    </motion.div>
                  ))}

                  {/* Streaming indicator */}
                  {isStreaming && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-start gap-3"
                    >
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 mt-1">
                        <Sparkles className="h-3.5 w-3.5 text-primary" />
                      </div>
                      <Card className="flex-1 border-border/60 shadow-sm">
                        <CardContent className="px-4 py-3">
                          <div className="flex items-center gap-3" role="status" aria-live="polite">
                            <div className="flex gap-1" aria-hidden="true">
                              <motion.span
                                className="h-2 w-2 rounded-full bg-primary"
                                animate={{ scale: [1, 1.5, 1] }}
                                transition={{ duration: 1, repeat: Infinity, delay: 0 }}
                              />
                              <motion.span
                                className="h-2 w-2 rounded-full bg-primary"
                                animate={{ scale: [1, 1.5, 1] }}
                                transition={{ duration: 1, repeat: Infinity, delay: 0.2 }}
                              />
                              <motion.span
                                className="h-2 w-2 rounded-full bg-primary"
                                animate={{ scale: [1, 1.5, 1] }}
                                transition={{ duration: 1, repeat: Infinity, delay: 0.4 }}
                              />
                            </div>
                            <span className="text-sm text-muted-foreground">
                              {liveSteps.length === 0
                                ? "Starting the pipeline…"
                                : liveAnswer
                                  ? "Writing the answer…"
                                  : "Working on your question…"}
                            </span>
                          </div>
                          {liveAnswer && (
                            <div className="prose prose-sm dark:prose-invert max-w-none mt-3 text-sm">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{liveAnswer}</ReactMarkdown>
                            </div>
                          )}
                          {liveSteps.length > 0 && (
                            <ul className="mt-3 space-y-1.5">
                              {liveSteps.map((step, si) => (
                                <motion.li
                                  key={`${step.node}-${si}`}
                                  initial={{ opacity: 0, x: -6 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  className="flex items-center gap-2 text-xs text-muted-foreground"
                                >
                                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-primary" />
                                  <span>{STEP_LABELS[step.node] ?? step.node}</span>
                                  {step.execution_time_ms != null && (
                                    <span className="ml-auto tabular-nums">
                                      {Math.round(step.execution_time_ms)} ms
                                    </span>
                                  )}
                                </motion.li>
                              ))}
                            </ul>
                          )}
                        </CardContent>
                      </Card>
                    </motion.div>
                  )}

                  {/* Error display */}
                  {streamError && !isStreaming && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center gap-3"
                    >
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-destructive/10">
                        <XCircle className="h-3.5 w-3.5 text-destructive" />
                      </div>
                      <Card className="flex-1 border-destructive/30 bg-destructive/5">
                        <CardContent className="flex items-center gap-2 px-4 py-2.5">
                          <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
                          <p className="text-xs text-destructive">
                            {streamError}
                          </p>
                        </CardContent>
                      </Card>
                    </motion.div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </ScrollArea>

          {/* input area */}
          <div className="border-t px-3 sm:px-4 py-3 bg-background">
            <div className="mx-auto max-w-3xl">
              <div className="relative flex items-end gap-2">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question about your documents…"
                  rows={1}
                  className="flex min-h-[2.75rem] w-full rounded-xl border border-input bg-background px-4 py-2.5 pr-12 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-primary/50 resize-none transition-all shadow-sm"
                  style={{ maxHeight: "200px" }}
                  onInput={(e) => {
                    const target = e.currentTarget;
                    target.style.height = "auto";
                    target.style.height =
                      Math.min(target.scrollHeight, 200) + "px";
                  }}
                  disabled={isStreaming}
                />
                <Button
                  onClick={handleSend}
                  disabled={!input.trim() || isStreaming}
                  size="icon"
                  aria-label="Send question"
                  className="absolute right-1.5 bottom-1.5 h-8 w-8 shrink-0 rounded-lg"
                >
                  {isStreaming ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <p className="mt-1.5 text-[10px] text-center text-muted-foreground flex items-center justify-center gap-1.5">
                <Sparkles className="h-3 w-3" />
                Powered by hybrid search + self-correction pipeline
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Delete Confirm Dialog ── */}
      <Dialog
        open={!!confirmDeleteId}
        onOpenChange={(v) => !v && setConfirmDeleteId(null)}
      >
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle className="text-sm">Delete Chat Session</DialogTitle>
          </DialogHeader>
          <p className="text-xs text-muted-foreground">
            This will permanently delete this chat session and all its messages.
            This action cannot be undone.
          </p>
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setConfirmDeleteId(null)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDeleteConfirm}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Citation Preview Dialog ── */}
      <Dialog
        open={!!showPreview}
        onOpenChange={(v) => !v && setShowPreview(null)}
      >
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-sm">
              <FileText className="h-4 w-4 text-primary" />
              Source: {showPreview?.filename || `${showPreview?.document_id?.slice(0, 12)}…`}
            </DialogTitle>
          </DialogHeader>
          {showPreview?.text && (
            <div className="rounded-md bg-muted/50 p-3 max-h-[300px] overflow-y-auto">
              <p className="text-xs leading-relaxed whitespace-pre-wrap">
                {showPreview.text}
              </p>
            </div>
          )}
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>Chunk: {showPreview?.chunk_id?.slice(0, 12)}…</span>
            {showPreview?.page != null && <span>Page {showPreview.page}</span>}
          </div>
        </DialogContent>
      </Dialog>
    </ErrorBoundary>
  );
}
