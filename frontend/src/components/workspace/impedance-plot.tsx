"use client";

import { useMemo } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";
import type { ImpedanceDataPoint } from "@/types";
import { formatFrequency, formatImpedance } from "@/lib/utils";

interface ImpedancePlotProps {
  data: ImpedanceDataPoint[];
  nominalImpedance?: number;
  showCorrected?: boolean;
  height?: number;
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: number;
}) {
  if (!active || !payload || !label) return null;

  return (
    <div className="rounded-md border border-border bg-surface-raised px-3 py-2 shadow-lg">
      <p className="text-xs text-text-muted font-mono mb-1">
        {formatFrequency(label)}
      </p>
      {payload.map((entry) => (
        <p
          key={entry.name}
          className="text-xs font-mono"
          style={{ color: entry.color }}
        >
          {entry.name}: {entry.name.includes("Phase") ? `${entry.value.toFixed(1)}\u00B0` : formatImpedance(entry.value)}
        </p>
      ))}
    </div>
  );
}

const logTicks = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000];

export function ImpedancePlot({
  data,
  nominalImpedance = 8,
  showCorrected = false,
  height = 350,
}: ImpedancePlotProps) {
  const yDomain = useMemo(() => {
    const magnitudes = data.map((d) => d.magnitude);
    const max = Math.max(...magnitudes);
    return [0, Math.ceil(max / 5) * 5 + 5];
  }, [data]);

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 5, right: 60, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
          <XAxis
            dataKey="frequency"
            type="number"
            scale="log"
            domain={[20, 20000]}
            ticks={logTicks}
            tickFormatter={(v: number) => formatFrequency(v)}
            stroke="#737373"
            tick={{ fill: "#737373", fontSize: 11, fontFamily: "JetBrains Mono" }}
            label={{
              value: "Frequency",
              position: "insideBottom",
              offset: -2,
              fill: "#737373",
              fontSize: 11,
            }}
          />
          <YAxis
            yAxisId="magnitude"
            domain={yDomain}
            stroke="#737373"
            tick={{ fill: "#737373", fontSize: 11, fontFamily: "JetBrains Mono" }}
            tickFormatter={(v: number) => `${v}\u03A9`}
            label={{
              value: "|\u2124| (\u03A9)",
              angle: -90,
              position: "insideLeft",
              offset: 10,
              fill: "#737373",
              fontSize: 11,
            }}
          />
          <YAxis
            yAxisId="phase"
            orientation="right"
            domain={[-90, 90]}
            stroke="#737373"
            tick={{ fill: "#737373", fontSize: 11, fontFamily: "JetBrains Mono" }}
            tickFormatter={(v: number) => `${v}\u00B0`}
            label={{
              value: "Phase (\u00B0)",
              angle: 90,
              position: "insideRight",
              offset: 10,
              fill: "#737373",
              fontSize: 11,
            }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 11, fontFamily: "JetBrains Mono" }}
          />
          <ReferenceLine
            yAxisId="magnitude"
            y={nominalImpedance}
            stroke="#3B82F6"
            strokeDasharray="5 5"
            strokeOpacity={0.5}
            label={{
              value: `${nominalImpedance}\u03A9 nominal`,
              fill: "#3B82F6",
              fontSize: 10,
              position: "right",
            }}
          />
          <Line
            yAxisId="magnitude"
            type="monotone"
            dataKey="magnitude"
            name="Impedance"
            stroke="#F59E0B"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: "#F59E0B" }}
          />
          <Line
            yAxisId="phase"
            type="monotone"
            dataKey="phase"
            name="Phase"
            stroke="#737373"
            strokeWidth={1}
            strokeDasharray="4 4"
            dot={false}
          />
          {showCorrected && (
            <>
              <Line
                yAxisId="magnitude"
                type="monotone"
                dataKey="corrected_magnitude"
                name="Corrected"
                stroke="#22C55E"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: "#22C55E" }}
              />
              <Line
                yAxisId="phase"
                type="monotone"
                dataKey="corrected_phase"
                name="Corrected Phase"
                stroke="#22C55E"
                strokeWidth={1}
                strokeDasharray="4 4"
                dot={false}
                opacity={0.6}
              />
            </>
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
