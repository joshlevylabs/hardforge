"use client";

import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ImpedancePlot } from "@/components/workspace/impedance-plot";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Info, Upload, ArrowRight } from "lucide-react";
import type { TSParams, Driver } from "@/types";
import {
  daytonRS180,
  generateImpedanceCurve,
  calculateCorrectionNetwork,
  generateCorrectedCurve,
} from "@/lib/mock-data";
import { formatComponentValue } from "@/lib/utils";

const tsParamFields: {
  key: keyof TSParams;
  label: string;
  unit: string;
  description: string;
  min: number;
  max: number;
  step: number;
}[] = [
  { key: "re", label: "Re", unit: "\u03A9", description: "DC resistance of the voice coil", min: 0.1, max: 100, step: 0.1 },
  { key: "le", label: "Le", unit: "mH", description: "Voice coil inductance", min: 0.01, max: 10, step: 0.01 },
  { key: "fs", label: "fs", unit: "Hz", description: "Resonance frequency in free air", min: 1, max: 10000, step: 1 },
  { key: "qms", label: "Qms", unit: "", description: "Mechanical Q factor at fs", min: 0.1, max: 100, step: 0.01 },
  { key: "qes", label: "Qes", unit: "", description: "Electrical Q factor at fs", min: 0.1, max: 100, step: 0.01 },
  { key: "qts", label: "Qts", unit: "", description: "Total Q factor at fs (Qms*Qes/(Qms+Qes))", min: 0.1, max: 100, step: 0.01 },
  { key: "vas", label: "Vas", unit: "L", description: "Equivalent compliance volume", min: 0.01, max: 500, step: 0.1 },
  { key: "bl", label: "BL", unit: "T\u00B7m", description: "Motor force factor (flux density \u00D7 coil length)", min: 0.1, max: 50, step: 0.1 },
  { key: "mms", label: "Mms", unit: "g", description: "Total moving mass (cone + coil + air load)", min: 0.1, max: 200, step: 0.1 },
  { key: "cms", label: "Cms", unit: "mm/N", description: "Mechanical compliance of suspension", min: 0.01, max: 10, step: 0.01 },
  { key: "rms", label: "Rms", unit: "kg/s", description: "Mechanical resistance of suspension", min: 0.01, max: 10, step: 0.01 },
  { key: "sd", label: "Sd", unit: "cm\u00B2", description: "Effective piston area", min: 1, max: 1000, step: 1 },
  { key: "xmax", label: "Xmax", unit: "mm", description: "Maximum linear excursion (one-way)", min: 0.1, max: 50, step: 0.1 },
];

export default function ImpedanceToolPage() {
  const [params, setParams] = useState<TSParams>(daytonRS180.ts_params);
  const [nominalImpedance, setNominalImpedance] = useState(8);
  const [showCorrection, setShowCorrection] = useState(false);

  const driver: Driver = useMemo(
    () => ({
      ...daytonRS180,
      ts_params: params,
      nominal_impedance: nominalImpedance,
    }),
    [params, nominalImpedance]
  );

  const impedanceData = useMemo(() => {
    const raw = generateImpedanceCurve(driver);
    if (!showCorrection) return raw;
    const network = calculateCorrectionNetwork(driver);
    return generateCorrectedCurve(raw, network, nominalImpedance);
  }, [driver, showCorrection, nominalImpedance]);

  const correctionNetwork = useMemo(
    () => calculateCorrectionNetwork(driver),
    [driver]
  );

  const handleParamChange = (key: keyof TSParams, value: string) => {
    const num = parseFloat(value);
    if (!isNaN(num) && num > 0) {
      setParams((prev) => ({ ...prev, [key]: num }));
    }
  };

  const loadExample = () => {
    setParams(daytonRS180.ts_params);
    setNominalImpedance(8);
  };

  return (
    <TooltipProvider>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-bold text-text-primary">
              Impedance Calculator
            </h1>
            <Badge variant="success">Free</Badge>
          </div>
          <p className="text-text-secondary text-sm">
            Enter Thiele-Small parameters to see the impedance curve and
            design correction networks. No account required.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Input section */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm">TS Parameters</CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs"
                    onClick={loadExample}
                  >
                    Load RS180-8
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <label className="text-[10px] text-text-muted block mb-1">
                      Nominal Impedance
                    </label>
                    <Input
                      type="number"
                      value={nominalImpedance}
                      onChange={(e) => {
                        const v = parseFloat(e.target.value);
                        if (!isNaN(v) && v > 0) setNominalImpedance(v);
                      }}
                      className="h-8 text-xs font-mono"
                    />
                  </div>
                  {tsParamFields.map((field) => (
                    <div key={field.key}>
                      <div className="flex items-center gap-1 mb-1">
                        <label className="text-[10px] text-text-muted">
                          {field.label}
                          {field.unit && (
                            <span className="ml-1 text-text-muted/60">
                              ({field.unit})
                            </span>
                          )}
                        </label>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Info className="h-3 w-3 text-text-muted/50 cursor-help" />
                          </TooltipTrigger>
                          <TooltipContent side="right">
                            <p className="max-w-[200px] text-xs">
                              {field.description}
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <Input
                        type="number"
                        value={params[field.key]}
                        onChange={(e) =>
                          handleParamChange(field.key, e.target.value)
                        }
                        min={field.min}
                        max={field.max}
                        step={field.step}
                        className="h-8 text-xs font-mono"
                      />
                    </div>
                  ))}
                  <div className="pt-2">
                    <Button variant="outline" size="sm" className="w-full gap-2" disabled title="Coming soon">
                      <Upload className="h-3.5 w-3.5" />
                      Upload CSV (Coming soon)
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Chart and results */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Impedance Curve</CardTitle>
              </CardHeader>
              <CardContent>
                <ImpedancePlot
                  data={impedanceData}
                  nominalImpedance={nominalImpedance}
                  showCorrected={showCorrection}
                  height={380}
                />
              </CardContent>
            </Card>

            {/* Correction network */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm">
                    Correction Network
                  </CardTitle>
                  <Button
                    size="sm"
                    onClick={() => setShowCorrection(!showCorrection)}
                  >
                    {showCorrection ? "Hide Correction" : "Design Correction Network"}
                    {!showCorrection && <ArrowRight className="h-3.5 w-3.5 ml-1" />}
                  </Button>
                </div>
              </CardHeader>
              {showCorrection && (
                <CardContent>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div className="rounded-md border border-border bg-surface p-3">
                      <h4 className="text-xs font-semibold text-text-primary mb-2">
                        Zobel Network
                      </h4>
                      <p className="text-xs text-text-muted mb-1">
                        Flattens rising impedance from voice coil inductance
                      </p>
                      <div className="space-y-1 mt-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-text-secondary">R<sub>z</sub></span>
                          <span className="font-mono text-text-primary">
                            {formatComponentValue(correctionNetwork.zobel.r, "\u03A9")}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-text-secondary">C<sub>z</sub></span>
                          <span className="font-mono text-text-primary">
                            {formatComponentValue(correctionNetwork.zobel.c, "F")}
                          </span>
                        </div>
                      </div>
                    </div>
                    {correctionNetwork.notch && (
                      <div className="rounded-md border border-border bg-surface p-3">
                        <h4 className="text-xs font-semibold text-text-primary mb-2">
                          Resonance Notch Filter
                        </h4>
                        <p className="text-xs text-text-muted mb-1">
                          Tames the impedance peak at f<sub>s</sub> = {params.fs}Hz
                        </p>
                        <div className="space-y-1 mt-2">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-text-secondary">R<sub>notch</sub></span>
                            <span className="font-mono text-text-primary">
                              {formatComponentValue(correctionNetwork.notch.r, "\u03A9")}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-text-secondary">C<sub>notch</sub></span>
                            <span className="font-mono text-text-primary">
                              {formatComponentValue(correctionNetwork.notch.c, "F")}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-text-secondary">L<sub>notch</sub></span>
                            <span className="font-mono text-text-primary">
                              {formatComponentValue(correctionNetwork.notch.l, "H")}
                            </span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              )}
            </Card>
          </div>
        </div>
      </main>
    </TooltipProvider>
  );
}
