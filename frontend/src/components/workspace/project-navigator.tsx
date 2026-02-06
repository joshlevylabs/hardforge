"use client";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { formatComponentValue } from "@/lib/utils";
import type { CircuitComponent, PipelineStep } from "@/types";
import {
  MessageSquare,
  Search,
  Cpu,
  FileImage,
  Download,
  Check,
} from "lucide-react";

interface ProjectNavigatorProps {
  projectName: string;
  description: string;
  currentStep: PipelineStep;
  components: CircuitComponent[];
}

const steps: { id: PipelineStep; label: string; icon: React.ElementType }[] = [
  { id: "intent", label: "Intent", icon: MessageSquare },
  { id: "feasibility", label: "Feasibility", icon: Search },
  { id: "design", label: "Design", icon: Cpu },
  { id: "schematic", label: "Schematic", icon: FileImage },
  { id: "export", label: "Export", icon: Download },
];

function stepStatus(step: PipelineStep, current: PipelineStep) {
  const stepOrder: PipelineStep[] = ["intent", "feasibility", "design", "schematic", "export"];
  const si = stepOrder.indexOf(step);
  const ci = stepOrder.indexOf(current);
  if (si < ci) return "complete";
  if (si === ci) return "active";
  return "pending";
}

export function ProjectNavigator({
  projectName,
  description,
  currentStep,
  components,
}: ProjectNavigatorProps) {
  const totalCost = components.reduce((acc, c) => {
    // Mock pricing
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

      {/* Pipeline stepper */}
      <div className="border-b border-border p-4">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">
          Pipeline
        </p>
        <div className="space-y-1">
          {steps.map((step) => {
            const status = stepStatus(step.id, currentStep);
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

      {/* Component list */}
      <div className="flex-1 overflow-y-auto p-4">
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
      </div>

      {/* BOM summary */}
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
    </div>
  );
}
