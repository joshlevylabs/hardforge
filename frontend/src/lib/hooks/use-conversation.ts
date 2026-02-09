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
  lastSavedAt: Date | null;
  startConversation: (initialMessage?: string) => Promise<void>;
  resumeConversation: (id: string) => Promise<void>;
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
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const conversationIdRef = useRef<string | null>(null);

  const startConversation = useCallback(async (initialMessage?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.createConversation(initialMessage);
      const sessionId = response.session_id;

      setConversationId(sessionId);
      conversationIdRef.current = sessionId;

      // Fetch full session to get all messages
      const fullSession = await api.getConversation(sessionId);
      setMessages(fullSession.messages);
      setPhase(fullSession.phase);
      setGatheredSpec(fullSession.gathered_spec);
      setCircuitDesign(fullSession.circuit_design as CircuitDesign | null);
      setLastSavedAt(new Date());

      // Update URL to reflect the real session ID
      window.history.replaceState(null, "", `/design/${sessionId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start conversation");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const resumeConversation = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const fullSession = await api.getConversation(id);
      setConversationId(id);
      conversationIdRef.current = id;
      setMessages(fullSession.messages);
      setPhase(fullSession.phase);
      setGatheredSpec(fullSession.gathered_spec);
      setCircuitDesign(fullSession.circuit_design as CircuitDesign | null);
      setLastSavedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load conversation");
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
      setLastSavedAt(new Date());
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
    lastSavedAt,
    startConversation,
    resumeConversation,
    sendMessage,
  };
}
