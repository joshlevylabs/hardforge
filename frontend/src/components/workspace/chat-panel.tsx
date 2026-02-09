"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { ChatMessage, ConversationPhase } from "@/types";
import { cn } from "@/lib/utils";

interface ChatPanelProps {
  messages: ChatMessage[];
  onSendMessage?: (content: string) => void;
  isLoading?: boolean;
  phase?: ConversationPhase;
}

const PHASE_LABELS: Record<ConversationPhase, string> = {
  gathering: "Gathering Requirements",
  clarifying: "Clarifying Details",
  confirming: "Confirming Specification",
  designing: "Designing Circuit",
  reviewing: "Reviewing Design",
  complete: "Design Complete",
};

const PHASE_PLACEHOLDERS: Record<ConversationPhase, string> = {
  gathering: "Describe your hardware project...",
  clarifying: "Answer the question above...",
  confirming: "Confirm or correct the specification...",
  designing: "Design in progress...",
  reviewing: "Ask about the design or request changes...",
  complete: "Design complete. Start a new conversation to design more.",
};

function renderMarkdown(text: string): React.ReactNode {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];

  lines.forEach((line, i) => {
    // Headers
    if (line.startsWith("### ")) {
      elements.push(<h4 key={i} className="font-semibold text-sm mt-2 mb-1">{line.slice(4)}</h4>);
      return;
    }
    if (line.startsWith("## ")) {
      elements.push(<h3 key={i} className="font-semibold text-base mt-2 mb-1">{line.slice(3)}</h3>);
      return;
    }

    // Bullet points
    if (line.startsWith("- ") || line.startsWith("  - ")) {
      const indent = line.startsWith("  - ");
      const content = line.replace(/^\s*- /, "");
      elements.push(
        <div key={i} className={cn("flex gap-1.5", indent && "ml-4")}>
          <span className="text-text-muted select-none">•</span>
          <span>{renderInlineMarkdown(content)}</span>
        </div>
      );
      return;
    }

    // Empty lines
    if (line.trim() === "") {
      elements.push(<div key={i} className="h-2" />);
      return;
    }

    // Regular text with inline formatting
    elements.push(<div key={i}>{renderInlineMarkdown(line)}</div>);
  });

  return <>{elements}</>;
}

function renderInlineMarkdown(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    const codeMatch = remaining.match(/`(.+?)`/);

    let firstMatch: { type: "bold" | "code"; index: number; full: string; content: string } | null = null;

    if (boldMatch && boldMatch.index !== undefined) {
      firstMatch = { type: "bold", index: boldMatch.index, full: boldMatch[0], content: boldMatch[1] };
    }
    if (codeMatch && codeMatch.index !== undefined) {
      if (!firstMatch || codeMatch.index < firstMatch.index) {
        firstMatch = { type: "code", index: codeMatch.index, full: codeMatch[0], content: codeMatch[1] };
      }
    }

    if (!firstMatch) {
      parts.push(remaining);
      break;
    }

    if (firstMatch.index > 0) {
      parts.push(remaining.slice(0, firstMatch.index));
    }

    if (firstMatch.type === "bold") {
      parts.push(<strong key={key++} className="font-semibold">{firstMatch.content}</strong>);
    } else {
      parts.push(
        <code key={key++} className="rounded bg-surface px-1 py-0.5 text-[11px] font-mono">
          {firstMatch.content}
        </code>
      );
    }

    remaining = remaining.slice(firstMatch.index + firstMatch.full.length);
  }

  return <>{parts}</>;
}

export function ChatPanel({ messages, onSendMessage, isLoading, phase }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSend = () => {
    if (input.trim() && onSendMessage && !isLoading) {
      onSendMessage(input.trim());
      setInput("");
    }
  };

  const currentPhase = phase || "gathering";
  const isInputDisabled = isLoading || currentPhase === "designing";

  return (
    <div className="flex h-full flex-col">
      {/* Phase badge */}
      {phase && (
        <div className="border-b border-border px-4 py-2">
          <Badge variant="outline" className="text-[10px]">
            {PHASE_LABELS[currentPhase]}
          </Badge>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              "flex",
              msg.role === "user" ? "justify-end" : "justify-start"
            )}
          >
            <div
              className={cn(
                "max-w-[85%] rounded-lg px-4 py-3 text-sm",
                msg.role === "user"
                  ? "bg-accent text-white"
                  : msg.role === "system"
                  ? "bg-surface border border-border text-text-secondary italic"
                  : "bg-surface-overlay text-text-primary"
              )}
            >
              <div className="whitespace-pre-wrap">
                {msg.role === "assistant" ? renderMarkdown(msg.content) : msg.content}
              </div>
              <p
                className={cn(
                  "mt-1 text-[10px]",
                  msg.role === "user"
                    ? "text-white/60"
                    : "text-text-muted"
                )}
              >
                {new Date(msg.timestamp).toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-surface-overlay rounded-lg px-4 py-3">
              <div className="flex items-center gap-1.5">
                <div className="h-2 w-2 rounded-full bg-text-muted animate-pulse" />
                <div className="h-2 w-2 rounded-full bg-text-muted animate-pulse [animation-delay:150ms]" />
                <div className="h-2 w-2 rounded-full bg-text-muted animate-pulse [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-border p-3">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={PHASE_PLACEHOLDERS[currentPhase]}
            disabled={isInputDisabled}
            className="flex-1 rounded-md border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-50"
          />
          <Button size="icon" onClick={handleSend} disabled={!input.trim() || isInputDisabled}>
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
