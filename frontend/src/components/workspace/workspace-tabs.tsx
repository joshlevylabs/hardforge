"use client";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ChatPanel } from "./chat-panel";
import { SchematicViewer } from "./schematic-viewer";
import { ImpedancePlot } from "./impedance-plot";
import { Slider } from "@/components/ui/slider";
import type { ImpedanceDataPoint, ChatMessage, CorrectionNetwork, ConversationPhase, CircuitDesign } from "@/types";
import { formatComponentValue } from "@/lib/utils";

interface WorkspaceTabsProps {
  messages: ChatMessage[];
  impedanceData: ImpedanceDataPoint[];
  correctionNetwork: CorrectionNetwork | null;
  nominalImpedance: number;
  showCorrected: boolean;
  onSendMessage?: (content: string) => void;
  isLoading?: boolean;
  phase?: ConversationPhase;
  circuitDesign?: CircuitDesign | null;
}

export function WorkspaceTabs({
  messages,
  impedanceData,
  correctionNetwork,
  nominalImpedance,
  showCorrected,
  onSendMessage,
  isLoading,
  phase,
  circuitDesign,
}: WorkspaceTabsProps) {
  const hasDesign = !!circuitDesign || (phase && ["reviewing", "complete"].includes(phase));

  return (
    <Tabs defaultValue="chat" className="flex h-full flex-col">
      <div className="border-b border-border px-4">
        <TabsList className="bg-transparent">
          <TabsTrigger value="chat">Chat</TabsTrigger>
          <TabsTrigger value="schematic" disabled={!hasDesign}>
            Schematic
          </TabsTrigger>
          <TabsTrigger value="impedance" disabled={!hasDesign}>
            Impedance
          </TabsTrigger>
          <TabsTrigger value="simulation" disabled>
            Simulation
          </TabsTrigger>
          <TabsTrigger value="pcb" disabled>
            PCB
          </TabsTrigger>
        </TabsList>
      </div>

      <TabsContent value="chat" className="flex-1 mt-0">
        <ChatPanel
          messages={messages}
          onSendMessage={onSendMessage}
          isLoading={isLoading}
          phase={phase}
        />
      </TabsContent>

      <TabsContent value="schematic" className="flex-1 p-4 mt-0">
        <SchematicViewer />
      </TabsContent>

      <TabsContent value="impedance" className="flex-1 overflow-y-auto p-4 mt-0">
        <div className="space-y-6">
          <ImpedancePlot
            data={impedanceData}
            nominalImpedance={nominalImpedance}
            showCorrected={showCorrected}
            height={320}
          />

          {correctionNetwork && (
            <div className="rounded-lg border border-border bg-surface p-4">
              <h3 className="text-xs font-semibold text-text-primary mb-4">
                Correction Network Values
              </h3>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-[11px] text-text-muted">Zobel R (R<sub>z</sub>)</label>
                    <span className="text-xs font-mono text-text-primary">
                      {formatComponentValue(correctionNetwork.zobel.r, "\u03A9")}
                    </span>
                  </div>
                  <Slider
                    defaultValue={[correctionNetwork.zobel.r]}
                    min={1}
                    max={20}
                    step={0.1}
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-[11px] text-text-muted">Zobel C (C<sub>z</sub>)</label>
                    <span className="text-xs font-mono text-text-primary">
                      {formatComponentValue(correctionNetwork.zobel.c, "F")}
                    </span>
                  </div>
                  <Slider
                    defaultValue={[correctionNetwork.zobel.c * 1e6]}
                    min={0.1}
                    max={100}
                    step={0.1}
                  />
                </div>
                {correctionNetwork.notch && (
                  <>
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-[11px] text-text-muted">Notch R</label>
                        <span className="text-xs font-mono text-text-primary">
                          {formatComponentValue(correctionNetwork.notch.r, "\u03A9")}
                        </span>
                      </div>
                      <Slider
                        defaultValue={[correctionNetwork.notch.r]}
                        min={0.1}
                        max={10}
                        step={0.01}
                      />
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-[11px] text-text-muted">Notch C</label>
                        <span className="text-xs font-mono text-text-primary">
                          {formatComponentValue(correctionNetwork.notch.c, "F")}
                        </span>
                      </div>
                      <Slider
                        defaultValue={[correctionNetwork.notch.c * 1e6]}
                        min={1}
                        max={1000}
                        step={1}
                      />
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-[11px] text-text-muted">Notch L</label>
                        <span className="text-xs font-mono text-text-primary">
                          {formatComponentValue(correctionNetwork.notch.l, "H")}
                        </span>
                      </div>
                      <Slider
                        defaultValue={[correctionNetwork.notch.l * 1e3]}
                        min={0.1}
                        max={20}
                        step={0.1}
                      />
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </TabsContent>

      <TabsContent value="simulation" className="flex-1 flex items-center justify-center mt-0">
        <div className="text-center text-text-muted">
          <p className="text-sm">Simulation coming soon</p>
          <p className="text-xs mt-1">SPICE simulation requires Pro tier</p>
        </div>
      </TabsContent>

      <TabsContent value="pcb" className="flex-1 flex items-center justify-center mt-0">
        <div className="text-center text-text-muted">
          <p className="text-sm">PCB layout preview coming soon</p>
          <p className="text-xs mt-1">Gerber export requires Pro tier</p>
        </div>
      </TabsContent>
    </Tabs>
  );
}
