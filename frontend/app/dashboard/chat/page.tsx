"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChat } from "@/hooks/use-chat";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
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
  StopCircle,
  Download,
  Search,
  Plus,
} from "lucide-react";
import type { ChatResponse } from "@/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const chatMutation = useChat();

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || isStreaming) return;

    setInput("");
    setIsStreaming(true);

    const userMessage: Message = { role: "user", content: question };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await chatMutation.mutateAsync({ question });
      const assistantMessage: Message = {
        role: "assistant",
        content: response.answer,
        response,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I encountered an error processing your request. Please try again.",
        },
      ]);
    } finally {
      setIsStreaming(false);
    }
  }, [input, isStreaming, chatMutation]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
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
    const text = `Query: ${messages.find((m) => m.response === response)?.content}\n\nAnswer: ${response.answer}\n\nConfidence: ${response.confidence_level} (${response.confidence})\nTrace: ${response.trace_id}`;
    const blob = new Blob([text], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sentinelrag-chat-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
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
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setMessages([])}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Clear
              </Button>
            )}
          </div>
        </div>

        <ScrollArea className="flex-1 pr-4" ref={scrollRef}>
          {messages.length === 0 ? (
            <EmptyState
              icon={MessageSquare}
              title="Start a conversation"
              description="Ask questions about your documents. SentinelRAG will retrieve relevant context and generate accurate answers with citations."
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

                    <div
                      className={`max-w-[85%] sm:max-w-[75%] ${
                        msg.role === "user" ? "order-first" : ""
                      }`}
                    >
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
                            <div className="space-y-2 px-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                <ConfidenceBadge
                                  level={msg.response.confidence_level}
                                  score={msg.response.confidence}
                                />
                                {msg.response.latencies && (
                                  <span className="text-xs text-muted-foreground">
                                    {(msg.response.latencies.total / 1000).toFixed(1)}s
                                  </span>
                                )}
                                {msg.response.citations && msg.response.citations.length > 0 && (
                                  <span className="text-xs text-muted-foreground">
                                    {msg.response.citations.length} sources
                                  </span>
                                )}
                              </div>

                              {msg.response.citations && msg.response.citations.length > 0 && (
                                <div className="flex flex-wrap gap-2">
                                  {msg.response.citations.slice(0, 3).map((cit, ci) => (
                                    <span
                                      key={ci}
                                      className="inline-flex items-center gap-1 rounded-lg border bg-card px-2 py-1 text-xs text-muted-foreground"
                                    >
                                      <Shield className="h-3 w-3" />
                                      Source {ci + 1}
                                    </span>
                                  ))}
                                  {msg.response.citations.length > 3 && (
                                    <span className="text-xs text-muted-foreground">
                                      +{msg.response.citations.length - 3} more
                                    </span>
                                  )}
                                </div>
                              )}

                              <div className="flex items-center gap-1">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleCopy(msg.content, `copy-${i}`)}
                                >
                                  {copiedId === `copy-${i}` ? (
                                    <Check className="h-4 w-4 text-success" />
                                  ) : (
                                    <Copy className="h-4 w-4" />
                                  )}
                                </Button>
                                <Button variant="ghost" size="sm" onClick={handleRegenerate}>
                                  <RefreshCw className="h-4 w-4" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleExport(msg.response)}
                                >
                                  <Download className="h-4 w-4" />
                                </Button>
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
              placeholder="Ask a question about your documents..."
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
            <Button
              onClick={handleSend}
              disabled={!input.trim() || isStreaming}
              size="icon"
              className="shrink-0"
            >
              {isStreaming ? (
                <StopCircle className="h-4 w-4" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          <p className="mt-2 text-xs text-center text-muted-foreground">
            Responses are generated using retrieved context. Verify important information.
          </p>
        </div>
      </div>
    </ErrorBoundary>
  );
}
