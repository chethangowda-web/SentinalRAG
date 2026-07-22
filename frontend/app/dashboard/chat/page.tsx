"use client";

import {
  useState,
  useRef,
  useEffect,
  useCallback,
  useMemo,
} from "react";
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
import { sendChatMessage } from "@/services/chat";
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
  ExternalLink,
} from "lucide-react";
import type {
  ChatResponse,
  CitationItem,
  GraphExecutionStep,
  ChatSession,
  RetrievalDetailItem,
} from "@/types";

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
  return cit.document_id?.substring(0, 12) + "…";
}

function confidenceColor(level: string) {
  switch (level) {
    case "HIGH":
      return "text-green-600 dark:text-green-400";
    case "MEDIUM":
      return "text-yellow-600 dark:text-yellow-400";
    default:
      return "text-red-600 dark:text-red-400";
  }
}

function confidenceBg(level: string) {
  switch (level) {
    case "HIGH":
      return "bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800/50";
    case "MEDIUM":
      return "bg-yellow-50 dark:bg-yellow-950/30 border-yellow-200 dark:border-yellow-800/50";
    default:
      return "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800/50";
  }
}

function confidenceBar(level: string) {
  switch (level) {
    case "HIGH":
      return "bg-green-500";
    case "MEDIUM":
      return "bg-yellow-500";
    default:
      return "bg-red-500";
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

function SmarterSuggestions({
  response,
  onSuggestionClick,
}: {
  response: ChatResponse;
  onSuggestionClick: (q: string) => void;
}) {
  const suggestions = useMemo(() => {
    const s: string[] = [];
    if (response.citations && response.citations.length > 0) {
      s.push("What are the key findings from the cited documents?");
    }
    if (response.confidence_level === "LOW") {
      s.push("Can you search again with more specific keywords?");
    }
    if (response.rewritten_question) {
      s.push("Show me the original vs rewritten query comparison");
    }
    s.push("Summarize the main points from this response");
    s.push("What related documents might be relevant?");
    return s.slice(0, 3);
  }, [response]);

  if (suggestions.length === 0) return null;

  return (
    <div className="rounded-lg border bg-card">
      <div className="px-3 py-2 text-xs font-medium text-muted-foreground flex items-center gap-1.5 border-b">
        <Lightbulb className="h-3.5 w-3.5" />
        Suggested follow-up questions
      </div>
      <div className="space-y-1 px-3 py-2">
        {suggestions.map((q, qi) => (
          <button
            key={qi}
            onClick={() => onSuggestionClick(q)}
            className="w-full text-left text-[11px] text-muted-foreground hover:text-foreground py-1.5 px-2 rounded-md hover:bg-secondary/50 transition-colors flex items-center gap-2"
          >
            <span className="text-primary/60">→</span>
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

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
                        <span className="shrink-0 text-[10px] tabular-nums text-muted-foreground">
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
                      <span>R:{rd.rerank_score.toFixed(3)}</span>
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
              {ci + 1}
            </span>
            <FileText className="h-3 w-3 shrink-0 text-muted-foreground/60" />
            <span className="max-w-[90px] truncate font-medium">
              {getSourceFilename(cit)}
            </span>
            {cit.page != null && (
              <span className="text-[10px] text-muted-foreground/60">p.{cit.page}</span>
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

/* ─── Main Chat Page ────────────────────────────────── */

export default function ChatPage() {
  const qc = useQueryClient();

  /* state */
  const [sidebarOpen, setSidebarOpen] = useState(true);
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
  const [streamError, setStreamError] = useState<string | null>(null);
  const [expandedReasoning, setExpandedReasoning] = useState<
    Record<string, boolean>
  >({});
  const [expandedEvidence, setExpandedEvidence] = useState<
    Record<string, boolean>
  >({});
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState<CitationItem | null>(null);

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
  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || isStreaming) return;

    setInput("");
    setIsStreaming(true);
    setStreamError(null);

    const userMsg: Message = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const response = await sendChatMessage({
        question,
        session_id: activeSessionId,
      });

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
    }
  }, [input, isStreaming, activeSessionId, qc]);

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
            <motion.aside
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
                <ScrollArea className="flex-1">
                  {sessionsLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    </div>
                  ) : sessions.length === 0 ? (
                    <div className="flex flex-col items-center py-8 text-center px-4">
                      <MessageSquare className="h-8 w-8 text-muted-foreground/50 mb-2" />
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
                                  <span className="text-[10px] text-muted-foreground/70">
                                    {s.message_count} msgs
                                  </span>
                                  {s.last_confidence_level && (
                                    <span
                                      className={cn(
                                        "text-[10px]",
                                        confidenceColor(
                                          s.last_confidence_level
                                        )
                                      )}
                                    >
                                      {s.last_confidence_level}
                                    </span>
                                  )}
                                  {s.pinned && (
                                    <Pin className="h-2.5 w-2.5 text-muted-foreground/50" />
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
                  className="flex h-full items-center justify-center px-4"
                >
                  <EmptyState
                    icon={MessageSquare}
                    title="Ask a question about your documents"
                    description="SentinelRAG uses hybrid search, reranking, and self-correction to find accurate answers with citations."
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
                            : "max-w-full sm:max-w-[90%] min-w-0"
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
                                {/* metadata bar */}
                                {msg.response && (
                                  <div
                                    className={cn(
                                      "flex flex-wrap items-center gap-x-3 gap-y-1.5 border-b px-4 py-2",
                                      confidenceBg(
                                        msg.response.confidence_level
                                      )
                                    )}
                                  >
                                    <div className="flex items-center gap-1.5">
                                      <Shield
                                        className={cn(
                                          "h-3.5 w-3.5",
                                          confidenceColor(
                                            msg.response.confidence_level
                                          )
                                        )}
                                      />
                                      <span
                                        className={cn(
                                          "text-xs font-bold tabular-nums",
                                          confidenceColor(
                                            msg.response.confidence_level
                                          )
                                        )}
                                      >
                                        {msg.response.confidence}%
                                      </span>
                                      <Badge
                                        variant={
                                          msg.response.confidence_level ===
                                          "HIGH"
                                            ? "success"
                                            : msg.response
                                                  .confidence_level === "MEDIUM"
                                              ? "warning"
                                              : "destructive"
                                        }
                                        className="text-[10px] h-5 px-1.5"
                                      >
                                        {msg.response.confidence_level}
                                      </Badge>
                                    </div>

                                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                      <Gauge className="h-3 w-3" />
                                      <span className="tabular-nums">
                                        {totalLatency(msg.response)}
                                      </span>
                                    </div>

                                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                      <BookOpen className="h-3 w-3" />
                                      <span>
                                        {msg.response.citations?.length ?? 0} sources
                                      </span>
                                    </div>

                                    {msg.response.retrieval_details && (
                                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                        <Layers className="h-3 w-3" />
                                        <span>{msg.response.retrieval_details.length} chunks</span>
                                      </div>
                                    )}

                                    {msg.response.retry_count > 0 && (
                                      <Badge variant="warning" className="text-[10px] h-5 px-1.5 gap-1">
                                        <RefreshCw className="h-3 w-3" />
                                        {msg.response.retry_count} correction{msg.response.retry_count > 1 ? "s" : ""}
                                      </Badge>
                                    )}

                                    {msg.response.model_used && (
                                      <div className="ml-auto text-[10px] text-muted-foreground/60 truncate max-w-[120px] hidden sm:block">
                                        {msg.response.model_used}
                                      </div>
                                    )}
                                  </div>
                                )}

                                {/* answer body */}
                                <div className="px-4 py-3">
                                  <div className="prose prose-sm dark:prose-invert max-w-none">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                      {msg.content}
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

                            {/* Smarter Suggestions */}
                            {msg.response && (
                              <SmarterSuggestions
                                response={msg.response}
                                onSuggestionClick={(q) => setInput(q)}
                              />
                            )}

                            {/* Low confidence warning */}
                            {msg.response &&
                              msg.response.confidence_level === "LOW" && (
                                <div className="rounded-lg border border-red-200 bg-red-50/50 dark:border-red-800/50 dark:bg-red-950/20 px-3 py-2.5">
                                  <div className="flex items-start gap-2">
                                    <AlertTriangle className="h-4 w-4 text-red-500 shrink-0 mt-0.5" />
                                    <div>
                                      <p className="text-xs font-medium text-red-700 dark:text-red-400">
                                        Low Confidence Response
                                      </p>
                                      <p className="text-[11px] text-red-600/70 dark:text-red-400/70 mt-0.5">
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

                            {/* Medium confidence nudge */}
                            {msg.response &&
                              msg.response.confidence_level === "MEDIUM" && (
                                <div className="rounded-lg border border-yellow-200 bg-yellow-50/50 dark:border-yellow-800/50 dark:bg-yellow-950/20 px-3 py-2">
                                  <div className="flex items-start gap-2">
                                    <AlertTriangle className="h-4 w-4 text-yellow-500 shrink-0 mt-0.5" />
                                    <p className="text-xs text-yellow-700 dark:text-yellow-400">
                                      Medium confidence ({msg.response.confidence}%).
                                      Consider verifying with additional sources.
                                    </p>
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
                          <div className="flex items-center gap-3">
                            <div className="flex gap-1">
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
                              Processing your question through the pipeline…
                            </span>
                          </div>
                          <div className="mt-2 grid grid-cols-4 gap-1.5">
                            {["Searching", "Analyzing", "Generating", "Verifying"].map((step, si) => (
                              <motion.div
                                key={step}
                                className="h-1 rounded-full bg-secondary overflow-hidden"
                              >
                                <motion.div
                                  className="h-full rounded-full bg-primary"
                                  initial={{ width: "0%" }}
                                  animate={{
                                    width: ["0%", "100%", "100%", "100%", "100%"],
                                  }}
                                  transition={{
                                    duration: 3,
                                    repeat: Infinity,
                                    delay: si * 0.75,
                                    ease: "easeInOut",
                                  }}
                                />
                              </motion.div>
                            ))}
                          </div>
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
                  className="absolute right-1.5 bottom-1.5 h-8 w-8 shrink-0 rounded-lg"
                >
                  {isStreaming ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <p className="mt-1.5 text-[10px] text-center text-muted-foreground/60 flex items-center justify-center gap-1.5">
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
              Source: {showPreview?.document_id?.slice(0, 12)}…
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
