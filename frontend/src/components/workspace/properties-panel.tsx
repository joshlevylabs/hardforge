"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Download, RefreshCw, FileImage } from "lucide-react";
import type { CircuitComponent } from "@/types";
import { formatComponentValue } from "@/lib/utils";

interface PropertiesPanelProps {
  selectedComponent?: CircuitComponent;
}

export function PropertiesPanel({ selectedComponent }: PropertiesPanelProps) {
  return (
    <div className="flex h-full flex-col border-l border-border bg-surface-raised">
      {/* Component properties */}
      <div className="border-b border-border p-4">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">
          Properties
        </p>
        {selectedComponent ? (
          <div className="space-y-3">
            <div>
              <label className="text-[10px] text-text-muted block mb-1">Reference</label>
              <Input value={selectedComponent.ref} readOnly className="h-8 text-xs font-mono" />
            </div>
            <div>
              <label className="text-[10px] text-text-muted block mb-1">Value</label>
              <Input
                value={formatComponentValue(selectedComponent.value, selectedComponent.unit)}
                readOnly
                className="h-8 text-xs font-mono"
              />
            </div>
            <div>
              <label className="text-[10px] text-text-muted block mb-1">Footprint</label>
              <Input value={selectedComponent.footprint} readOnly className="h-8 text-xs font-mono" />
            </div>
            {selectedComponent.tolerance && (
              <div>
                <label className="text-[10px] text-text-muted block mb-1">Tolerance</label>
                <Input value={selectedComponent.tolerance} readOnly className="h-8 text-xs font-mono" />
              </div>
            )}
            {selectedComponent.power_rating && (
              <div>
                <label className="text-[10px] text-text-muted block mb-1">Power Rating</label>
                <Input value={`${selectedComponent.power_rating}W`} readOnly className="h-8 text-xs font-mono" />
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-text-muted">
            Select a component to view its properties
          </p>
        )}
      </div>

      {/* Quick actions */}
      <div className="p-4">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">
          Actions
        </p>
        <div className="space-y-2">
          <Button variant="outline" size="sm" className="w-full justify-start gap-2">
            <RefreshCw className="h-3.5 w-3.5" />
            Recalculate
          </Button>
          <Button variant="outline" size="sm" className="w-full justify-start gap-2">
            <FileImage className="h-3.5 w-3.5" />
            Export Schematic
          </Button>
          <Button variant="outline" size="sm" className="w-full justify-start gap-2">
            <Download className="h-3.5 w-3.5" />
            Export Gerber
          </Button>
        </div>
      </div>
    </div>
  );
}
