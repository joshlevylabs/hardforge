"use client";

import { useMemo } from "react";
import { ProjectNavigator } from "@/components/workspace/project-navigator";
import { WorkspaceTabs } from "@/components/workspace/workspace-tabs";
import { PropertiesPanel } from "@/components/workspace/properties-panel";
import {
  daytonRS180,
  mockComponents,
  mockChatMessages,
  generateImpedanceCurve,
  calculateCorrectionNetwork,
  generateCorrectedCurve,
} from "@/lib/mock-data";

export default function DesignWorkspacePage() {
  const driver = daytonRS180;

  const impedanceData = useMemo(() => {
    const raw = generateImpedanceCurve(driver);
    const network = calculateCorrectionNetwork(driver);
    return generateCorrectedCurve(raw, network, driver.nominal_impedance);
  }, [driver]);

  const correctionNetwork = useMemo(
    () => calculateCorrectionNetwork(driver),
    [driver]
  );

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* Left panel — navigator */}
      <div className="w-64 shrink-0">
        <ProjectNavigator
          projectName="RS180-8 Impedance Correction"
          description="Zobel + notch filter for Dayton RS180-8 woofer"
          currentStep="design"
          components={mockComponents}
        />
      </div>

      {/* Center panel — workspace tabs */}
      <div className="flex-1 min-w-0">
        <WorkspaceTabs
          messages={mockChatMessages}
          impedanceData={impedanceData}
          correctionNetwork={correctionNetwork}
          nominalImpedance={driver.nominal_impedance}
          showCorrected={true}
        />
      </div>

      {/* Right panel — properties */}
      <div className="w-64 shrink-0">
        <PropertiesPanel selectedComponent={mockComponents[0]} />
      </div>
    </div>
  );
}
