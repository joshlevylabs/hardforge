"use client";

import { useEffect, useMemo, useRef } from "react";
import { useSearchParams, useParams } from "next/navigation";
import { ProjectNavigator } from "@/components/workspace/project-navigator";
import { WorkspaceTabs } from "@/components/workspace/workspace-tabs";
import { PropertiesPanel } from "@/components/workspace/properties-panel";
import { useConversation } from "@/lib/hooks/use-conversation";
import {
  generateImpedanceCurve,
  calculateCorrectionNetwork,
  generateCorrectedCurve,
  daytonRS180,
} from "@/lib/mock-data";
import type { CircuitComponent } from "@/types";

export default function DesignWorkspacePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const initialPrompt = searchParams.get("prompt");
  const hasStarted = useRef(false);
  const id = params.id as string;

  const {
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
  } = useConversation();

  // Start or resume conversation on mount (once)
  useEffect(() => {
    if (!hasStarted.current) {
      hasStarted.current = true;
      if (id !== "new") {
        resumeConversation(id);
      } else {
        startConversation(initialPrompt || undefined);
      }
    }
  }, [id, initialPrompt, startConversation, resumeConversation]);

  // Extract components from circuit design
  const components: CircuitComponent[] = useMemo(() => {
    if (!circuitDesign?.components) return [];
    return circuitDesign.components;
  }, [circuitDesign]);

  // Use mock impedance data when we have a design (for now — backend will provide real data later)
  const impedanceData = useMemo(() => {
    if (!circuitDesign) return [];
    const raw = generateImpedanceCurve(daytonRS180);
    const network = calculateCorrectionNetwork(daytonRS180);
    return generateCorrectedCurve(raw, network, daytonRS180.nominal_impedance);
  }, [circuitDesign]);

  const correctionNetwork = useMemo(() => {
    if (!circuitDesign) return null;
    return calculateCorrectionNetwork(daytonRS180);
  }, [circuitDesign]);

  // Derive project name from gathered spec or phase
  const projectName = gatheredSpec?.project_type
    ? gatheredSpec.project_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : "New Design";

  const description = gatheredSpec?.driver?.model
    ? `${gatheredSpec.driver.manufacturer || ""} ${gatheredSpec.driver.model}`.trim()
    : "Describe your project to get started";

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* Left panel — navigator */}
      <div className="w-64 shrink-0">
        <ProjectNavigator
          projectName={projectName}
          description={description}
          currentPhase={phase}
          components={components}
          gatheredSpec={gatheredSpec}
          lastSavedAt={lastSavedAt}
        />
      </div>

      {/* Center panel — workspace tabs */}
      <div className="flex-1 min-w-0 h-full overflow-hidden">
        <WorkspaceTabs
          designId={id}
          messages={messages}
          impedanceData={impedanceData}
          correctionNetwork={correctionNetwork}
          nominalImpedance={8}
          showCorrected={!!circuitDesign}
          onSendMessage={sendMessage}
          isLoading={isLoading}
          phase={phase}
          circuitDesign={circuitDesign}
        />
      </div>

      {/* Right panel — properties */}
      <div className="w-64 shrink-0">
        <PropertiesPanel
          selectedComponent={components.length > 0 ? components[0] : undefined}
        />
      </div>

      {/* Error toast */}
      {error && (
        <div className="fixed bottom-4 right-4 z-50 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}
    </div>
  );
}
