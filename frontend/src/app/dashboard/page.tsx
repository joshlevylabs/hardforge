"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Clock, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { ConversationSummary, ConversationPhase } from "@/types";

const phaseBadge: Record<
  ConversationPhase,
  { label: string; variant: "default" | "secondary" | "success" | "warning" | "outline" }
> = {
  gathering: { label: "Draft", variant: "secondary" },
  clarifying: { label: "Draft", variant: "secondary" },
  confirming: { label: "Draft", variant: "secondary" },
  designing: { label: "Designing", variant: "default" },
  reviewing: { label: "Designing", variant: "default" },
  complete: { label: "Complete", variant: "success" },
};

export default function DashboardPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listConversations()
      .then(setConversations)
      .catch(() => setConversations([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Your hardware design projects
          </p>
        </div>
        <Button onClick={() => router.push("/design/new")}>
          <Plus className="h-4 w-4 mr-1" />
          New Design
        </Button>
      </div>

      {/* Usage stats */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-[10px] uppercase tracking-wider text-text-muted">
              Designs This Month
            </p>
            <p className="mt-1 text-2xl font-bold font-mono text-text-primary">
              {conversations.length} <span className="text-sm text-text-muted font-normal">/ 3</span>
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-[10px] uppercase tracking-wider text-text-muted">
              Subscription
            </p>
            <p className="mt-1 text-2xl font-bold text-text-primary">Free</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-[10px] uppercase tracking-wider text-text-muted">
              Total Projects
            </p>
            <p className="mt-1 text-2xl font-bold font-mono text-text-primary">
              {conversations.length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Projects list */}
      <div className="space-y-3">
        {loading && (
          <p className="text-sm text-text-muted py-4 text-center">Loading projects...</p>
        )}
        {!loading && conversations.length === 0 && (
          <p className="text-sm text-text-muted py-4 text-center">
            No projects yet. Click &quot;New Design&quot; to get started.
          </p>
        )}
        {conversations.map((conv) => {
          const badge = phaseBadge[conv.phase] ?? phaseBadge.gathering;
          return (
            <Card
              key={conv.id}
              className="group hover:border-accent/50 transition-colors cursor-pointer"
              onClick={() => router.push(`/design/${conv.id}`)}
            >
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-text-primary truncate">
                      {conv.name}
                    </h3>
                    <Badge variant={badge.variant}>{badge.label}</Badge>
                  </div>
                  <p className="mt-0.5 text-xs text-text-muted truncate">
                    {conv.project_type
                      ? conv.project_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
                      : "No type yet"}
                    {" — "}
                    {conv.message_count} message{conv.message_count !== 1 ? "s" : ""}
                  </p>
                  <div className="mt-1 flex items-center gap-1 text-[10px] text-text-muted">
                    <Clock className="h-3 w-3" />
                    Updated{" "}
                    {new Date(conv.updated_at).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    })}
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 text-text-muted opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-4" />
              </CardContent>
            </Card>
          );
        })}
      </div>
    </main>
  );
}
