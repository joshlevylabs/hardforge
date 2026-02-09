"use client";

import { useState, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type {
  ChatMessage,
  ConversationPhase,
  GatheredSpec,
  CircuitDesign,
} from "@/types";

interface UseConversationReturn {
  conversationId: string | null;
  messages: ChatMessage[];
  phase: ConversationPhase;
  gatheredSpec: GatheredSpec | null;
  circuitDesign: CircuitDesign | null;
  isLoading: boolean;
  error: string | null;
  startConversation: (initialMessage?: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
}

export function useConversation(): UseConversationReturn {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [phase, setPhase] = useState<ConversationPhase>("gathering");
  const [gatheredSpec, setGatheredSpec] = useState<GatheredSpec | null>(null);
  const [circuitDesign, setCircuitDesign] = useState<CircuitDesign | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const conversationIdRef = useRef<string | null>(null);

  const startConversation = useCallback(async (initialMessage?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.createConversation(initialMessage);

      // Fetch the conversation list and grab the newest one to get the ID
      const conversations = await api.listConversations();
      const latest = conversations.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )[0];

      if (latest) {
        setConversationId(latest.id);
        conversationIdRef.current = latest.id;

        // Fetch full session to get all messages
        const fullSession = await api.getConversation(latest.id);
        setMessages(fullSession.messages);
        setPhase(fullSession.phase);
        setGatheredSpec(fullSession.gathered_spec);
        setCircuitDesign(fullSession.circuit_design as CircuitDesign | null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start conversation");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    const currentId = conversationIdRef.current;
    if (!currentId) {
      setError("No active conversation");
      return;
    }

    // Optimistically add user message
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.sendConversationMessage(currentId, content);

      // Add assistant response
      setMessages((prev) => [...prev, response.message]);
      setPhase(response.phase);
      if (response.gathered_spec) {
        setGatheredSpec(response.gathered_spec);
      }
      if (response.circuit_design) {
        setCircuitDesign(response.circuit_design as CircuitDesign);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    conversationId,
    messages,
    phase,
    gatheredSpec,
    circuitDesign,
    isLoading,
    error,
    startConversation,
    sendMessage,
  };
}
