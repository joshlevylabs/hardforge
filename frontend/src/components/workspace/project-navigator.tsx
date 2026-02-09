"use client";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { formatComponentValue } from "@/lib/utils";
import type { CircuitComponent, ConversationPhase, GatheredSpec } from "@/types";
import {
  MessageSquare,
  ClipboardCheck,
  Cpu,
  Eye,
  CheckCircle,
  Check,
  HelpCircle,
} from "lucide-react";

interface ProjectNavigatorProps {
  projectName: string;
  description: string;
  currentPhase: ConversationPhase;
  components: CircuitComponent[];
  gatheredSpec?: GatheredSpec | null;
}

const phases: { id: ConversationPhase; label: string; icon: React.ElementType }[] = [
  { id: "gathering", label: "Requirements", icon: MessageSquare },
  { id: "clarifying", label: "Clarifying", icon: HelpCircle },
  { id: "confirming", label: "Confirmation", icon: ClipboardCheck },
  { id: "designing", label: "Design", icon: Cpu },
  { id: "reviewing", label: "Review", icon: Eye },
  { id: "complete", label: "Complete", icon: CheckCircle },
];

const PHASE_ORDER: ConversationPhase[] = [
  "gathering", "clarifying", "confirming", "designing", "reviewing", "complete",
];

function phaseStatus(phase: ConversationPhase, current: ConversationPhase) {
  const pi = PHASE_ORDER.indexOf(phase);
  const ci = PHASE_ORDER.indexOf(current);
  if (pi < ci) return "complete";
  if (pi === ci) return "active";
  return "pending";
}

export function ProjectNavigator({
  projectName,
  description,
  currentPhase,
  components,
  gatheredSpec,
}: ProjectNavigatorProps) {
  const totalCost = components.reduce((acc, c) => {
    const prices: Record<string, number> = { resistor: 0.1, capacitor: 0.5, inductor: 2.5 };
    return acc + (prices[c.type] || 0.25);
  }, 0);

  return (
    <div className="flex h-full flex-col border-r border-border bg-surface-raised">
      {/* Project info */}
      <div className="border-b border-border p-4">
        <h2 className="text-sm font-semibold text-text-primary truncate">
          {projectName}
        </h2>
        <p className="mt-1 text-xs text-text-muted line-clamp-2">
          {description}
        </p>
      </div>

      {/* Phase stepper */}
      <div className="border-b border-border p-4">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">
          Progress
        </p>
        <div className="space-y-1">
          {phases.map((step) => {
            const status = phaseStatus(step.id, currentPhase);
            return (
              <div
                key={step.id}
                className={cn(
                  "flex items-center gap-2 rounded-md px-2 py-1.5 text-xs",
                  status === "active" && "bg-accent/10 text-accent",
                  status === "complete" && "text-text-secondary",
                  status === "pending" && "text-text-muted"
                )}
              >
                {status === "complete" ? (
                  <Check className="h-3.5 w-3.5 text-success" />
                ) : (
                  <step.icon
                    className={cn(
                      "h-3.5 w-3.5",
                      status === "active" ? "text-accent" : "text-text-muted"
                    )}
                  />
                )}
                <span className="font-medium">{step.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Gathered spec info (during early phases) or Component list (after design) */}
      <div className="flex-1 overflow-y-auto p-4">
        {components.length > 0 ? (
          <>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">
              Components ({components.length})
            </p>
            <div className="space-y-1.5">
              {components.map((comp) => (
                <div
                  key={comp.ref}
                  className="flex items-center justify-between rounded-md bg-surface px-2 py-1.5 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                      {comp.ref}
                    </Badge>
                    <span className="text-text-secondary font-mono">
                      {formatComponentValue(comp.value, comp.unit)}
                    </span>
                  </div>
                  <span className="text-text-muted text-[10px]">{comp.footprint}</span>
                </div>
              ))}
            </div>
          </>
        ) : gatheredSpec ? (
          <>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">
              Gathered Specs
            </p>
            <div className="space-y-2 text-xs">
              {gatheredSpec.project_type && (
                <div className="rounded-md bg-surface px-2 py-1.5">
                  <span className="text-text-muted">Type: </span>
                  <span className="text-text-primary">{gatheredSpec.project_type.replace(/_/g, " ")}</span>
                </div>
              )}
              {gatheredSpec.driver?.model && (
                <div className="rounded-md bg-surface px-2 py-1.5">
                  <span className="text-text-muted">Driver: </span>
                  <span className="text-text-primary">
                    {gatheredSpec.driver.manufacturer ? `${gatheredSpec.driver.manufacturer} ` : ""}
                    {gatheredSpec.driver.model}
                  </span>
                </div>
              )}
              {Object.entries(gatheredSpec.target_specs).map(([key, value]) => (
                <div key={key} className="rounded-md bg-surface px-2 py-1.5">
                  <span className="text-text-muted">{key.replace(/_/g, " ")}: </span>
                  <span className="text-text-primary">{String(value)}</span>
                </div>
              ))}
              {Object.entries(gatheredSpec.constraints).map(([key, value]) => (
                <div key={key} className="rounded-md bg-surface px-2 py-1.5">
                  <span className="text-text-muted">{key.replace(/_/g, " ")}: </span>
                  <span className="text-text-primary">{String(value)}</span>
                </div>
              ))}
            </div>
          </>
        ) : (
          <p className="text-xs text-text-muted italic">
            Start a conversation to begin gathering requirements.
          </p>
        )}
      </div>

      {/* BOM summary (only when components exist) */}
      {components.length > 0 && (
        <div className="border-t border-border p-4">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-2">
            BOM Summary
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-text-muted">Parts:</span>
              <span className="ml-1 text-text-primary font-mono">{components.length}</span>
            </div>
            <div>
              <span className="text-text-muted">Est. cost:</span>
              <span className="ml-1 text-text-primary font-mono">${totalCost.toFixed(2)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
