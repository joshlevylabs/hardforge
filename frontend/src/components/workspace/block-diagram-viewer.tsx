"use client";

import { useState, useRef, useCallback, useMemo } from "react";
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Block, BlockConnection } from "@/types";

interface BlockDiagramViewerProps {
  blocks: Block[];
  connections: BlockConnection[];
}

const SIGNAL_COLORS: Record<string, string> = {
  power: "#F59E0B",
  analog: "#3B82F6",
  digital: "#A855F7",
  data: "#22C55E",
  control: "#6B7280",
};

const HW_COLORS = [
  "#3B82F6",
  "#F59E0B",
  "#22C55E",
  "#A855F7",
  "#EF4444",
  "#06B6D4",
  "#F97316",
];

interface HardwareGroup {
  name: string;
  color: string;
  blocks: LayoutBlock[];
  x: number;
  y: number;
  width: number;
  height: number;
}

const BLOCK_WIDTH = 180;
const BLOCK_HEADER = 36;
const PORT_ROW = 20;
const PORT_RADIUS = 5;
const H_GAP = 200;
const V_GAP = 150;
const PADDING = 60;

interface LayoutBlock {
  block: Block;
  x: number;
  y: number;
  width: number;
  height: number;
}

function layoutBlocks(blocks: Block[], connections: BlockConnection[]): LayoutBlock[] {
  if (blocks.length === 0) return [];

  // Build adjacency: which blocks feed into which
  const incomingMap = new Map<string, Set<string>>();
  const outgoingMap = new Map<string, Set<string>>();
  for (const b of blocks) {
    incomingMap.set(b.id, new Set());
    outgoingMap.set(b.id, new Set());
  }
  for (const c of connections) {
    incomingMap.get(c.to_block)?.add(c.from_block);
    outgoingMap.get(c.from_block)?.add(c.to_block);
  }

  // Assign columns via topological layering
  const blockIds = new Set(blocks.map((b) => b.id));
  const column = new Map<string, number>();
  const assigned = new Set<string>();

  // Find roots (no internal incoming edges)
  const roots = blocks.filter((b) => {
    const incoming = incomingMap.get(b.id) ?? new Set();
    return [...incoming].every((src) => !blockIds.has(src));
  });

  // BFS layering
  let frontier = roots.map((b) => b.id);
  let col = 0;
  while (frontier.length > 0) {
    for (const id of frontier) {
      if (!assigned.has(id)) {
        column.set(id, col);
        assigned.add(id);
      }
    }
    const next = new Set<string>();
    for (const id of frontier) {
      for (const dest of outgoingMap.get(id) ?? []) {
        if (!assigned.has(dest)) {
          next.add(dest);
        }
      }
    }
    frontier = [...next];
    col++;
  }

  // Place any unassigned blocks (disconnected) in the last column
  for (const b of blocks) {
    if (!column.has(b.id)) {
      column.set(b.id, col);
    }
  }

  // Group by column
  const colGroups = new Map<number, Block[]>();
  for (const b of blocks) {
    const c = column.get(b.id) ?? 0;
    if (!colGroups.has(c)) colGroups.set(c, []);
    colGroups.get(c)!.push(b);
  }

  const result: LayoutBlock[] = [];
  for (const [c, group] of colGroups) {
    for (let row = 0; row < group.length; row++) {
      const b = group[row];
      const maxPorts = Math.max(b.inputs.length, b.outputs.length, 1);
      const h = BLOCK_HEADER + maxPorts * PORT_ROW + 12;
      result.push({
        block: b,
        x: PADDING + c * (BLOCK_WIDTH + H_GAP),
        y: PADDING + row * (V_GAP + h) - row * h + row * V_GAP,
        width: BLOCK_WIDTH,
        height: h,
      });
    }
  }

  // Recalculate y so items in same column are stacked without overlapping
  const colBlocks = new Map<number, LayoutBlock[]>();
  for (const lb of result) {
    const c = column.get(lb.block.id) ?? 0;
    if (!colBlocks.has(c)) colBlocks.set(c, []);
    colBlocks.get(c)!.push(lb);
  }
  for (const [, group] of colBlocks) {
    let yOffset = PADDING;
    for (const lb of group) {
      lb.y = yOffset;
      yOffset += lb.height + V_GAP;
    }
  }

  return result;
}

function getPortPosition(
  lb: LayoutBlock,
  portName: string,
  side: "input" | "output"
): { x: number; y: number } {
  const ports = side === "input" ? lb.block.inputs : lb.block.outputs;
  const idx = ports.indexOf(portName);
  const i = idx >= 0 ? idx : 0;
  const x = side === "input" ? lb.x : lb.x + lb.width;
  const y = lb.y + BLOCK_HEADER + 10 + i * PORT_ROW;
  return { x, y };
}

export function BlockDiagramViewer({ blocks, connections }: BlockDiagramViewerProps) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const lastPos = useRef({ x: 0, y: 0 });

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setDragging(true);
    lastPos.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!dragging) return;
      const dx = e.clientX - lastPos.current.x;
      const dy = e.clientY - lastPos.current.y;
      setPan((p) => ({ x: p.x + dx, y: p.y + dy }));
      lastPos.current = { x: e.clientX, y: e.clientY };
    },
    [dragging]
  );

  const handleMouseUp = useCallback(() => setDragging(false), []);

  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const layout = useMemo(() => layoutBlocks(blocks, connections), [blocks, connections]);

  const layoutMap = useMemo(() => {
    const map = new Map<string, LayoutBlock>();
    for (const lb of layout) map.set(lb.block.id, lb);
    return map;
  }, [layout]);

  // Group blocks by host_hardware
  const hardwareGroups = useMemo(() => {
    const groupMap = new Map<string, LayoutBlock[]>();
    for (const lb of layout) {
      const hw = lb.block.host_hardware;
      if (!hw) continue;
      if (!groupMap.has(hw)) groupMap.set(hw, []);
      groupMap.get(hw)!.push(lb);
    }

    const groups: HardwareGroup[] = [];
    let colorIdx = 0;
    for (const [name, groupBlocks] of groupMap) {
      const pad = 20;
      const labelHeight = 30;
      const minX = Math.min(...groupBlocks.map((lb) => lb.x));
      const minY = Math.min(...groupBlocks.map((lb) => lb.y));
      const maxX = Math.max(...groupBlocks.map((lb) => lb.x + lb.width));
      const maxY = Math.max(...groupBlocks.map((lb) => lb.y + lb.height));
      groups.push({
        name,
        color: HW_COLORS[colorIdx % HW_COLORS.length],
        blocks: groupBlocks,
        x: minX - pad,
        y: minY - labelHeight,
        width: maxX - minX + pad * 2,
        height: maxY - minY + labelHeight + pad,
      });
      colorIdx++;
    }
    return groups;
  }, [layout]);

  // Compute SVG canvas size (account for hardware group borders)
  const svgWidth = useMemo(() => {
    if (layout.length === 0) return 600;
    const blockMax = Math.max(...layout.map((lb) => lb.x + lb.width + PADDING));
    const groupMax = hardwareGroups.length > 0
      ? Math.max(...hardwareGroups.map((g) => g.x + g.width + PADDING))
      : 0;
    return Math.max(600, blockMax, groupMax);
  }, [layout, hardwareGroups]);

  const svgHeight = useMemo(() => {
    if (layout.length === 0) return 400;
    const blockMax = Math.max(...layout.map((lb) => lb.y + lb.height + PADDING));
    const groupMax = hardwareGroups.length > 0
      ? Math.max(...hardwareGroups.map((g) => g.y + g.height + PADDING))
      : 0;
    return Math.max(400, blockMax, groupMax);
  }, [layout, hardwareGroups]);

  if (blocks.length === 0) {
    return (
      <div className="flex h-full w-full items-center justify-center rounded-md border border-border bg-surface">
        <p className="text-sm text-text-muted">No architecture diagram available</p>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full overflow-hidden bg-surface rounded-md border border-border">
      {/* Toolbar */}
      <div className="absolute right-3 top-3 z-10 flex items-center gap-1 rounded-md border border-border bg-surface-raised p-1">
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setZoom((z) => Math.min(z * 1.25, 5))}>
          <ZoomIn className="h-3.5 w-3.5" />
        </Button>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setZoom((z) => Math.max(z / 1.25, 0.2))}>
          <ZoomOut className="h-3.5 w-3.5" />
        </Button>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleReset}>
          <Maximize2 className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Canvas */}
      <div
        className="h-full w-full cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <div
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: "center center",
            transition: dragging ? "none" : "transform 0.15s ease",
          }}
          className="flex h-full w-full items-center justify-center"
        >
          <svg width={svgWidth} height={svgHeight} viewBox={`0 0 ${svgWidth} ${svgHeight}`}>
            {/* Grid background */}
            <defs>
              <pattern id="block-grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#1e293b" strokeWidth="0.5" />
              </pattern>
              <marker
                id="arrowhead"
                markerWidth="8"
                markerHeight="6"
                refX="8"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill="#94a3b8" />
              </marker>
              {Object.entries(SIGNAL_COLORS).map(([type, color]) => (
                <marker
                  key={type}
                  id={`arrow-${type}`}
                  markerWidth="8"
                  markerHeight="6"
                  refX="8"
                  refY="3"
                  orient="auto"
                >
                  <polygon points="0 0, 8 3, 0 6" fill={color} />
                </marker>
              ))}
            </defs>
            <rect width={svgWidth} height={svgHeight} fill="#0f172a" />
            <rect width={svgWidth} height={svgHeight} fill="url(#block-grid)" />

            {/* Hardware group rectangles */}
            {hardwareGroups.map((group) => {
              const label = group.name.length > 24 ? group.name.slice(0, 22) + "..." : group.name;
              return (
                <g key={`hw-${group.name}`}>
                  <rect
                    x={group.x}
                    y={group.y}
                    width={group.width}
                    height={group.height}
                    rx={12}
                    fill={group.color + "0D"}
                    stroke={group.color}
                    strokeWidth="1.5"
                    strokeDasharray="8 4"
                  />
                  <text
                    x={group.x + 10}
                    y={group.y + 18}
                    fill={group.color}
                    fontSize="11"
                    fontFamily="JetBrains Mono, monospace"
                    fontWeight="bold"
                  >
                    {label}
                  </text>
                </g>
              );
            })}

            {/* Connections */}
            {connections.map((conn, i) => {
              const fromLb = layoutMap.get(conn.from_block);
              const toLb = layoutMap.get(conn.to_block);
              if (!fromLb || !toLb) return null;

              // Find matching output port on source block
              const fromPort = getPortPosition(fromLb, conn.signal_name, "output");
              // Find matching input port on dest block
              const toPort = getPortPosition(toLb, conn.signal_name, "input");

              const color = SIGNAL_COLORS[conn.signal_type] ?? "#6B7280";
              const midX = (fromPort.x + toPort.x) / 2;

              return (
                <g key={`conn-${i}`}>
                  <path
                    d={`M ${fromPort.x} ${fromPort.y} C ${midX} ${fromPort.y}, ${midX} ${toPort.y}, ${toPort.x} ${toPort.y}`}
                    fill="none"
                    stroke={color}
                    strokeWidth="1.5"
                    markerEnd={`url(#arrow-${conn.signal_type})`}
                    opacity={0.8}
                  />
                  <text
                    x={midX}
                    y={Math.min(fromPort.y, toPort.y) - 6}
                    textAnchor="middle"
                    fill={color}
                    fontSize="9"
                    fontFamily="JetBrains Mono, monospace"
                    opacity={0.9}
                  >
                    {conn.signal_name}
                  </text>
                </g>
              );
            })}

            {/* Blocks */}
            {layout.map((lb) => {
              const { block, x, y, width, height } = lb;
              return (
                <g key={block.id}>
                  {/* Block body */}
                  <rect
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    rx={8}
                    ry={8}
                    fill="#1e293b"
                    stroke="#334155"
                    strokeWidth="1.5"
                  />

                  {/* Block name */}
                  <text
                    x={x + width / 2}
                    y={y + 16}
                    textAnchor="middle"
                    fill="#e2e8f0"
                    fontSize="12"
                    fontWeight="bold"
                    fontFamily="Inter, sans-serif"
                  >
                    {block.name.length > 18 ? block.name.slice(0, 16) + "..." : block.name}
                  </text>

                  {/* Block type */}
                  <text
                    x={x + width / 2}
                    y={y + 30}
                    textAnchor="middle"
                    fill="#94a3b8"
                    fontSize="9"
                    fontFamily="JetBrains Mono, monospace"
                  >
                    {block.type}
                  </text>

                  {/* Input ports */}
                  {block.inputs.map((input, idx) => {
                    const py = y + BLOCK_HEADER + 10 + idx * PORT_ROW;
                    return (
                      <g key={`in-${idx}`}>
                        <circle cx={x} cy={py} r={PORT_RADIUS} fill="#3B82F6" stroke="#1e293b" strokeWidth="1" />
                        <text
                          x={x + 10}
                          y={py + 3}
                          fill="#94a3b8"
                          fontSize="9"
                          fontFamily="JetBrains Mono, monospace"
                        >
                          {input.length > 12 ? input.slice(0, 10) + ".." : input}
                        </text>
                      </g>
                    );
                  })}

                  {/* Output ports */}
                  {block.outputs.map((output, idx) => {
                    const py = y + BLOCK_HEADER + 10 + idx * PORT_ROW;
                    return (
                      <g key={`out-${idx}`}>
                        <circle
                          cx={x + width}
                          cy={py}
                          r={PORT_RADIUS}
                          fill="#3B82F6"
                          stroke="#1e293b"
                          strokeWidth="1"
                        />
                        <text
                          x={x + width - 10}
                          y={py + 3}
                          textAnchor="end"
                          fill="#94a3b8"
                          fontSize="9"
                          fontFamily="JetBrains Mono, monospace"
                        >
                          {output.length > 12 ? output.slice(0, 10) + ".." : output}
                        </text>
                      </g>
                    );
                  })}
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      {/* Zoom indicator */}
      <div className="absolute bottom-3 left-3 text-[10px] text-text-muted font-mono">
        {Math.round(zoom * 100)}%
      </div>

      {/* Legends */}
      <div className="absolute bottom-3 right-3 flex flex-col items-end gap-1.5 text-[10px] text-text-muted font-mono">
        {hardwareGroups.length >= 2 && (
          <div className="flex items-center gap-3">
            {hardwareGroups.map((group) => (
              <span key={group.name} className="flex items-center gap-1">
                <span
                  className="inline-block h-2 w-2 rounded border"
                  style={{ borderColor: group.color, backgroundColor: group.color + "33" }}
                />
                {group.name.length > 16 ? group.name.slice(0, 14) + ".." : group.name}
              </span>
            ))}
          </div>
        )}
        <div className="flex items-center gap-3">
          {Object.entries(SIGNAL_COLORS).map(([type, color]) => (
            <span key={type} className="flex items-center gap-1">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ backgroundColor: color }}
              />
              {type}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
