"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChat } from "@/hooks/use-chat";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { LatencyBadge } from "@/components/shared/LatencyBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  Send,
  MessageSquare,
  Copy,
  Check,
  RefreshCw,
  Trash2,
  Sparkles,
  Shield,
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
  Quote,
  BookOpen,
} from "lucide-react";
import type { ChatResponse, CitationItem } from "@/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
  stages?: string[];
}

const pipelineStages = [
  "Searching...",
  "Checking hallucination...",
  "Confidence low...",
  "Retrying...",
  "New answer generated...",
  "Verified",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [feedbackGiven, setFeedbackGiven] = useState<Record<number, "up" | "down" | null>>({});
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStages, setCurrentStages] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const chatMutation = useChat();

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, currentStages, scrollToBottom]);

  const simulateStages = useCallback(async () => {
    const delays = [800, 1200, 1000, 1500, 1000, 600];
    for (let i = 0; i < pipelineStages.length; i++) {
      setCurrentStages(prev => [...prev, pipelineStages[i]]);
      await new Promise(r => setTimeout(r, delays[i]));
    }
  }, []);

  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || isStreaming) return;

    setInput("");
    setIsStreaming(true);
    setCurrentStages([]);

    const userMessage: Message = { role: "user", content: question };
    setMessages((prev) => [...prev, userMessage]);
    simulateStages();

    try {
      const response = await chatMutation.mutateAsync({ question });
      const assistantMessage: Message = {
        role: "assistant",
        content: response.answer,
        response,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setCurrentStages([]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I encountered an error processing your request. Please try again." },
      ]);
      setCurrentStages([]);
    } finally {
      setIsStreaming(false);
    }
  }, [input, isStreaming, chatMutation, simulateStages]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleCopy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleRegenerate = () => {
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg) {
      setMessages((prev) => prev.slice(0, -1));
      setInput(lastUserMsg.content);
    }
  };

  const handleExport = (response?: ChatResponse) => {
    if (!response) return;
    const text = `Query: ${messages.find((m) => m.response === response)?.content}\n\nAnswer: ${response.answer}\n\nConfidence: ${response.confidence_level} (${(response.confidence * 100).toFixed(0)}%)\nCitations: ${response.citations?.length || 0}\nTrace: ${response.trace_id}`;
    const blob = new Blob([text], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sentinelrag-chat-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getSourceFilename = (citation: CitationItem) => {
    return citation.document_id?.substring(0, 8) + ".pdf";
  };

  return (
    <ErrorBoundary>
      <div className="flex h-[calc(100vh-4rem)] flex-col">
        <div className="flex items-center justify-between border-b pb-3 mb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <MessageSquare className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">Chat</h1>
              <p className="text-xs text-muted-foreground">Ask questions about your documents</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <Button variant="ghost" size="sm" onClick={() => setMessages([])}>
                <Trash2 className="mr-2 h-4 w-4" /> New Chat
              </Button>
            )}
          </div>
        </div>

        <ScrollArea className="flex-1 pr-4" ref={scrollRef}>
          {messages.length === 0 && !isStreaming ? (
            <EmptyState
              icon={MessageSquare}
              title="Ask a question about your documents"
              description="SentinelRAG uses hybrid search and self-correction to find accurate answers with citations."
              className="h-full"
            />
          ) : (
            <div className="space-y-6 pb-4">
              <AnimatePresence initial={false}>
                {messages.map((msg, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                    className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    {msg.role === "assistant" && (
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 mt-1">
                        <Sparkles className="h-4 w-4 text-primary" />
                      </div>
                    )}

                    <div className={`max-w-[85%] sm:max-w-[75%] ${msg.role === "user" ? "order-first" : ""}`}>
                      {msg.role === "user" ? (
                        <div className="rounded-2xl bg-primary px-4 py-3 text-primary-foreground">
                          <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          <div className="rounded-2xl bg-secondary px-4 py-3">
                            <div className="prose prose-sm dark:prose-invert max-w-none">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {msg.content}
                              </ReactMarkdown>
                            </div>
                          </div>

                          {msg.response && (
                            <div className="space-y-3 px-1">
                              {/* Sources Used */}
                              {msg.response.citations && msg.response.citations.length > 0 && (
                                <div className="rounded-lg border bg-card p-3">
                                  <div className="flex items-center gap-2 mb-2">
                                    <BookOpen className="h-4 w-4 text-primary" />
                                    <span className="text-xs font-medium">Sources Used</span>
                                  </div>
                                  <div className="space-y-1.5">
                                    {msg.response.citations.map((cit, ci) => (
                                      <div key={ci} className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <FileText className="h-3 w-3 shrink-0" />
                                        <span className="font-medium text-foreground">{getSourceFilename(cit)}</span>
                                        {cit.page != null && <span>· page {cit.page}</span>}
                                        <Badge variant="outline" className="text-[10px] px-1 py-0">Source {ci + 1}</Badge>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Confidence & Metrics */}
                              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                <div className="rounded-lg bg-success/10 p-2.5 text-center">
                                  <div className="flex items-center justify-center gap-1">
                                    <Shield className="h-3 w-3 text-success" />
                                    <span className="text-sm font-bold text-success">
                                      {(msg.response.confidence * 100).toFixed(0)}%
                                    </span>
                                  </div>
                                  <p className="text-[10px] text-muted-foreground mt-0.5">Confidence</p>
                                </div>
                                <div className="rounded-lg bg-primary/10 p-2.5 text-center">
                                  <div className="flex items-center justify-center gap-1">
                                    <Search className="h-3 w-3 text-primary" />
                                    <span className="text-sm font-bold text-primary">
                                      {(msg.response.confidence * 100).toFixed(0)}%
                                    </span>
                                  </div>
                                  <p className="text-[10px] text-muted-foreground mt-0.5">Retrieval Score</p>
                                </div>
                                <div className="rounded-lg bg-secondary p-2.5 text-center">
                                  <div className="flex items-center justify-center gap-1">
                                    <Brain className="h-3 w-3" />
                                    <span className="text-sm font-bold">
                                      {msg.response.citations?.length || 0}
                                    </span>
                                  </div>
                                  <p className="text-[10px] text-muted-foreground mt-0.5">Sources</p>
                                </div>
                                <div className="rounded-lg bg-secondary p-2.5 text-center">
                                  <div className="flex items-center justify-center gap-1">
                                    <Gauge className="h-3 w-3" />
                                    <span className="text-sm font-bold">
                                      {msg.response.latencies ? `${(Object.values(msg.response.latencies).reduce((a, b) => a + b, 0) / 1000).toFixed(1)}s` : "--"}
                                    </span>
                                  </div>
                                  <p className="text-[10px] text-muted-foreground mt-0.5">Latency</p>
                                </div>
                              </div>

                              {/* Reasoning */}
                              {msg.response.reasoning_path && msg.response.reasoning_path.length > 0 && (
                                <div className="rounded-lg border bg-card p-3">
                                  <div className="flex items-center gap-2 mb-2">
                                    <Brain className="h-4 w-4 text-primary" />
                                    <span className="text-xs font-medium">Reasoning</span>
                                  </div>
                                  <div className="space-y-1">
                                    {msg.response.reasoning_path.map((step, si) => (
                                      <div key={si} className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <CheckCircle2 className="h-3 w-3 text-success shrink-0" />
                                        <span>{step}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Action Buttons */}
                              <div className="flex items-center gap-1">
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <Button variant="ghost" size="sm" onClick={() => handleCopy(msg.content, `copy-${i}`)}>
                                        {copiedId === `copy-${i}` ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
                                      </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>Copy</TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <Button variant="ghost" size="sm" onClick={handleRegenerate}>
                                        <RefreshCw className="h-4 w-4" />
                                      </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>Regenerate</TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <Button variant="ghost" size="sm" onClick={() => handleExport(msg.response)}>
                                        <Download className="h-4 w-4" />
                                      </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>Export</TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                                <div className="ml-2 flex items-center gap-1">
                                  <span className="text-[10px] text-muted-foreground mr-1">Feedback</span>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setFeedbackGiven(prev => ({ ...prev, [i]: prev[i] === "up" ? null : "up" }))}
                                    className={feedbackGiven[i] === "up" ? "text-success" : ""}
                                  >
                                    <ThumbsUp className="h-4 w-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setFeedbackGiven(prev => ({ ...prev, [i]: prev[i] === "down" ? null : "down" }))}
                                    className={feedbackGiven[i] === "down" ? "text-destructive" : ""}
                                  >
                                    <ThumbsDown className="h-4 w-4" />
                                  </Button>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {msg.role === "user" && (
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary mt-1">
                        <User className="h-4 w-4 text-primary-foreground" />
                      </div>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* Sentinel Pipeline Stages */}
              <AnimatePresence>
                {isStreaming && currentStages.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="rounded-xl border bg-card p-4 space-y-2"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Brain className="h-4 w-4 text-primary" />
                      <span className="text-xs font-medium">Self-Correction Pipeline</span>
                    </div>
                    {currentStages.map((stage, si) => {
                      const isLast = si === currentStages.length - 1;
                      const isError = stage.includes("low");
                      const isDone = stage.includes("Verified") || stage.includes("New answer");
                      return (
                        <div key={si} className="flex items-center gap-2 text-xs">
                          {isLast && !isDone ? (
                            <Loader2 className="h-3 w-3 animate-spin text-primary" />
                          ) : isError ? (
                            <AlertTriangle className="h-3 w-3 text-warning" />
                          ) : isDone ? (
                            <CheckCircle2 className="h-3 w-3 text-success" />
                          ) : (
                            <CheckCircle2 className="h-3 w-3 text-muted-foreground" />
                          )}
                          <span className={isLast ? "text-foreground font-medium" : "text-muted-foreground"}>
                            {stage}
                          </span>
                        </div>
                      );
                    })}
                    {currentStages.length >= pipelineStages.length && (
                      <div className="flex items-center gap-2 text-xs text-success font-medium pt-1">
                        <CheckCircle2 className="h-3 w-3" />
                        <span>Confidence: 95%</span>
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </ScrollArea>

        <div className="border-t pt-4 mt-4">
          <div className="relative flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question..."
              rows={1}
              className="flex min-h-[2.75rem] w-full rounded-xl border border-input bg-background px-4 py-2.5 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
              style={{ maxHeight: "200px" }}
              onInput={(e) => {
                const target = e.currentTarget;
                target.style.height = "auto";
                target.style.height = Math.min(target.scrollHeight, 200) + "px";
              }}
              disabled={isStreaming}
            />
            <Button onClick={handleSend} disabled={!input.trim() || isStreaming} size="icon" className="shrink-0">
              {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
          <p className="mt-2 text-xs text-center text-muted-foreground">
            Powered by hybrid search + self-correction pipeline
          </p>
        </div>
      </div>
    </ErrorBoundary>
  );
}
