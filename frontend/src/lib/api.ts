import type { SendMessageResponse, ConversationSession, ConversationSummary } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
}

class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data: unknown
  ) {
    super(`API Error ${status}: ${statusText}`);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options;

  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
    ...rest,
  });

  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new ApiError(res.status, res.statusText, data);
  }

  return res.json();
}

export const api = {
  // AI Pipeline
  parseIntent: (description: string) =>
    request("/api/parse-intent", { method: "POST", body: { description } }),

  analyzeFeasibility: (intent: unknown) =>
    request("/api/analyze-feasibility", { method: "POST", body: { intent } }),

  designCircuit: (intent: unknown, topology?: string) =>
    request("/api/design-circuit", { method: "POST", body: { intent, topology } }),

  // Computation
  calculateComponents: (params: unknown) =>
    request("/api/calculate-components", { method: "POST", body: params }),

  calculateImpedance: (tsParams: unknown) =>
    request("/api/calculate-impedance", { method: "POST", body: tsParams }),

  simulate: (design: unknown) =>
    request("/api/simulate", { method: "POST", body: design }),

  // Export
  generateSchematic: (design: unknown) =>
    request("/api/generate-schematic", { method: "POST", body: design }),

  generateGerber: (design: unknown) =>
    request("/api/generate-gerber", { method: "POST", body: design }),

  generateBom: (design: unknown) =>
    request("/api/generate-bom", { method: "POST", body: design }),

  // Library
  getDrivers: (params?: { search?: string; type?: string; manufacturer?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.set("search", params.search);
    if (params?.type) searchParams.set("type", params.type);
    if (params?.manufacturer) searchParams.set("manufacturer", params.manufacturer);
    const qs = searchParams.toString();
    return request(`/api/library/drivers${qs ? `?${qs}` : ""}`);
  },

  getDriver: (id: string) => request(`/api/library/drivers/${id}`),

  getTopologies: () => request("/api/library/topologies"),

  // Conversations
  createConversation: (initialMessage?: string) =>
    request<SendMessageResponse>("/api/conversations", {
      method: "POST",
      body: initialMessage ? { content: initialMessage } : undefined,
    }),

  sendConversationMessage: (conversationId: string, content: string) =>
    request<SendMessageResponse>(`/api/conversations/${conversationId}/messages`, {
      method: "POST",
      body: { content },
    }),

  getConversation: (conversationId: string) =>
    request<ConversationSession>(`/api/conversations/${conversationId}`),

  listConversations: () =>
    request<ConversationSummary[]>("/api/conversations"),

  deleteConversation: (conversationId: string) =>
    request<{ status: string }>(`/api/conversations/${conversationId}`, {
      method: "DELETE",
    }),
};

export { ApiError };
