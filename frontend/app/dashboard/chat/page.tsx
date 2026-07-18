"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, User, PanelRightOpen, PanelRightClose, AlertCircle, Loader2 } from "lucide-react";
import { useChat } from "@/hooks/use-chat";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { ExplainabilityPanel } from "@/components/explainability/ExplainabilityPanel";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import type { ChatResponse } from "@/types";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
}

function ChatContent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [selectedResponse, setSelectedResponse] = useState<ChatResponse | null>(null);
  const [showPanel, setShowPanel] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const chat = useChat();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    const q = input.trim();
    if (!q || chat.isPending) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: q };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    try {
      const response = await chat.mutateAsync({ question: q });
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.answer,
        response,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: err instanceof Error ? err.message : "An error occurred. Please try again.",
      };
      setMessages((prev) => [...prev, errMsg]);
    }
  };

  const handleExplain = (response: ChatResponse) => {
    setSelectedResponse(response);
    setShowPanel(true);
  };

  return (
    <div className="flex h-[calc(100vh-10rem)] gap-0">
      <div className="flex flex-1 flex-col">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Chat</h1>
            <p className="text-sm text-muted-foreground">Ask questions about your documents</p>
          </div>
          <button
            onClick={() => setShowPanel(!showPanel)}
            className="flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-secondary transition-colors"
          >
            {showPanel ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
            Explain
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-4">
          {messages.length === 0 ? (
            <EmptyState
              icon={Bot}
              title="Ask a question"
              description="Ask questions about your uploaded documents to see the self-correcting RAG pipeline in action."
            />
          ) : (
            <div className="space-y-4">
              <AnimatePresence>
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div className={`flex gap-3 max-w-[80%] ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                      <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                        msg.role === "user" ? "bg-primary/10" : "bg-secondary"
                      }`}>
                        {msg.role === "user" ? (
                          <User className="h-4 w-4 text-primary" />
                        ) : (
                          <Bot className="h-4 w-4 text-muted-foreground" />
                        )}
                      </div>
                      <div>
                        <div className={`rounded-xl px-4 py-3 text-sm leading-relaxed ${
                          msg.role === "user"
                            ? "bg-primary text-primary-foreground"
                            : "bg-card border border-border"
                        }`}>
                          {msg.content}
                        </div>
                        {msg.response && (
                          <div className="mt-2 flex items-center gap-2">
                            <ConfidenceBadge level={msg.response.confidence_level} score={msg.response.confidence} />
                            <button
                              onClick={() => handleExplain(msg.response!)}
                              className="text-xs text-muted-foreground hover:text-primary transition-colors"
                            >
                              Show explainability
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {chat.isPending && (
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processing through self-correcting pipeline...
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="relative border-t border-border pt-4">
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
              placeholder="Ask a question about your documents..."
              rows={1}
              className="flex-1 resize-none rounded-xl border border-border bg-secondary px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
              disabled={chat.isPending}
            />
            <button
              type="submit"
              disabled={!input.trim() || chat.isPending}
              className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </form>
      </div>

      <ExplainabilityPanel
        response={selectedResponse}
        isOpen={showPanel}
        onClose={() => setShowPanel(false)}
      />
    </div>
  );
}

export default function ChatPage() {
  return (
    <ErrorBoundary>
      <ChatContent />
    </ErrorBoundary>
  );
}
