"use client";

import { useState, useRef, useCallback, useMemo, useEffect } from "react";
import { ZoomIn, ZoomOut, Maximize2, CheckCircle, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Block, BlockConnection, ConversationPhase } from "@/types";

interface BlockDiagramViewerProps {
  designId?: string;
  blocks: Block[];
  connections: BlockConnection[];
  phase?: ConversationPhase;
  isLoading?: boolean;
  onApprove?: () => void;
}

interface LayoutData {
  blockPositions: [string, { x: number; y: number }][];
  pointOverrides: [number, { dx: number; dy: number }[]][];
  waypoints: [number, { x: number; y: number }[]][];
}

function getLayoutKey(designId: string): string {
  return `hardforge-layout-${designId}`;
}

function loadLayout(designId: string): LayoutData | null {
  try {
    const raw = localStorage.getItem(getLayoutKey(designId));
    if (!raw) return null;
    return JSON.parse(raw) as LayoutData;
  } catch { return null; }
}

function saveLayout(designId: string, data: LayoutData): void {
  try {
    localStorage.setItem(getLayoutKey(designId), JSON.stringify(data));
  } catch { /* localStorage full or unavailable */ }
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
const CONNECTION_SPREAD = 15;

interface LayoutBlock {
  block: Block;
  x: number;
  y: number;
  width: number;
  height: number;
}

function layoutBlocks(blocks: Block[], connections: BlockConnection[]): LayoutBlock[] {
  if (blocks.length === 0) return [];

  // Constants for hardware-aware layout
  const GROUP_PAD_X = 20;
  const GROUP_PAD_TOP = 30;
  const GROUP_PAD_BOTTOM = 20;
  const GROUP_GAP = 40;
  const INTRA_GROUP_H_GAP = 40;
  const INTRA_GROUP_V_GAP = 20;

  // Build block adjacency
  const blockIncoming = new Map<string, Set<string>>();
  const blockOutgoing = new Map<string, Set<string>>();
  for (const b of blocks) {
    blockIncoming.set(b.id, new Set());
    blockOutgoing.set(b.id, new Set());
  }
  for (const c of connections) {
    blockIncoming.get(c.to_block)?.add(c.from_block);
    blockOutgoing.get(c.from_block)?.add(c.to_block);
  }

  // LEVEL 1: Partition blocks by hardware and build hardware groups
  const hwGroupMap = new Map<string, Block[]>();
  let soloGroupId = 0;
  for (const b of blocks) {
    const hw = b.host_hardware;
    if (hw) {
      if (!hwGroupMap.has(hw)) hwGroupMap.set(hw, []);
      hwGroupMap.get(hw)!.push(b);
    } else {
      // Solo block gets its own unique group
      hwGroupMap.set(`__solo_${soloGroupId++}`, [b]);
    }
  }

  const hwGroups = Array.from(hwGroupMap.entries()).map(([name, groupBlocks]) => ({
    name,
    blocks: groupBlocks,
    column: -1,
    layoutBlocks: [] as LayoutBlock[],
    width: 0,
    height: 0,
  }));

  // Build group adjacency graph
  const groupIncoming = new Map<number, Set<number>>();
  const groupOutgoing = new Map<number, Set<number>>();
  const blockToGroupIdx = new Map<string, number>();
  for (let i = 0; i < hwGroups.length; i++) {
    groupIncoming.set(i, new Set());
    groupOutgoing.set(i, new Set());
    for (const b of hwGroups[i].blocks) {
      blockToGroupIdx.set(b.id, i);
    }
  }

  for (const c of connections) {
    const fromGroup = blockToGroupIdx.get(c.from_block);
    const toGroup = blockToGroupIdx.get(c.to_block);
    if (fromGroup !== undefined && toGroup !== undefined && fromGroup !== toGroup) {
      groupOutgoing.get(fromGroup)!.add(toGroup);
      groupIncoming.get(toGroup)!.add(fromGroup);
    }
  }

  // BFS layering for group columns
  const assignedGroups = new Set<number>();
  const rootGroups: number[] = [];
  for (let i = 0; i < hwGroups.length; i++) {
    if (groupIncoming.get(i)!.size === 0) {
      rootGroups.push(i);
    }
  }

  let groupFrontier = rootGroups;
  let groupCol = 0;
  while (groupFrontier.length > 0) {
    for (const gIdx of groupFrontier) {
      if (!assignedGroups.has(gIdx)) {
        hwGroups[gIdx].column = groupCol;
        assignedGroups.add(gIdx);
      }
    }
    const nextGroups = new Set<number>();
    for (const gIdx of groupFrontier) {
      for (const dest of groupOutgoing.get(gIdx) ?? []) {
        if (!assignedGroups.has(dest)) {
          nextGroups.add(dest);
        }
      }
    }
    groupFrontier = [...nextGroups];
    groupCol++;
  }

  // Assign disconnected groups to last column
  for (let i = 0; i < hwGroups.length; i++) {
    if (!assignedGroups.has(i)) {
      hwGroups[i].column = groupCol;
    }
  }

  // LEVEL 2: Layout blocks within each hardware group
  for (const group of hwGroups) {
    const groupBlockIds = new Set(group.blocks.map((b) => b.id));

    // Build intra-group adjacency
    const intraIncoming = new Map<string, Set<string>>();
    const intraOutgoing = new Map<string, Set<string>>();
    for (const b of group.blocks) {
      intraIncoming.set(b.id, new Set());
      intraOutgoing.set(b.id, new Set());
    }
    for (const c of connections) {
      if (groupBlockIds.has(c.from_block) && groupBlockIds.has(c.to_block)) {
        intraIncoming.get(c.to_block)!.add(c.from_block);
        intraOutgoing.get(c.from_block)!.add(c.to_block);
      }
    }

    // Topological sort within group
    const blockColumn = new Map<string, number>();
    const assignedBlocks = new Set<string>();
    const roots = group.blocks.filter((b) => intraIncoming.get(b.id)!.size === 0);

    let blockFrontier = roots.map((b) => b.id);
    let col = 0;
    while (blockFrontier.length > 0) {
      for (const id of blockFrontier) {
        if (!assignedBlocks.has(id)) {
          blockColumn.set(id, col);
          assignedBlocks.add(id);
        }
      }
      const next = new Set<string>();
      for (const id of blockFrontier) {
        for (const dest of intraOutgoing.get(id) ?? []) {
          if (!assignedBlocks.has(dest)) {
            next.add(dest);
          }
        }
      }
      blockFrontier = [...next];
      col++;
    }

    // Assign disconnected blocks within group
    for (const b of group.blocks) {
      if (!blockColumn.has(b.id)) {
        blockColumn.set(b.id, col);
      }
    }

    // Group blocks by sub-column
    const subColGroups = new Map<number, Block[]>();
    for (const b of group.blocks) {
      const c = blockColumn.get(b.id) ?? 0;
      if (!subColGroups.has(c)) subColGroups.set(c, []);
      subColGroups.get(c)!.push(b);
    }

    // Layout blocks within group (relative positions)
    const tempLayout: LayoutBlock[] = [];
    for (const [subCol, blockList] of subColGroups) {
      let yOffset = 0;
      for (const b of blockList) {
        const maxPorts = Math.max(b.inputs.length, b.outputs.length, 1);
        const h = BLOCK_HEADER + maxPorts * PORT_ROW + 12;
        tempLayout.push({
          block: b,
          x: subCol * (BLOCK_WIDTH + INTRA_GROUP_H_GAP),
          y: yOffset,
          width: BLOCK_WIDTH,
          height: h,
        });
        yOffset += h + INTRA_GROUP_V_GAP;
      }
    }

    // Compute group bounding box
    if (tempLayout.length > 0) {
      const minX = Math.min(...tempLayout.map((lb) => lb.x));
      const minY = Math.min(...tempLayout.map((lb) => lb.y));
      const maxX = Math.max(...tempLayout.map((lb) => lb.x + lb.width));
      const maxY = Math.max(...tempLayout.map((lb) => lb.y + lb.height));
      group.width = maxX - minX + GROUP_PAD_X * 2;
      group.height = maxY - minY + GROUP_PAD_TOP + GROUP_PAD_BOTTOM;
    }

    group.layoutBlocks = tempLayout;
  }

  // LEVEL 3: Position groups on canvas
  const groupColumns = new Map<number, typeof hwGroups>();
  for (const group of hwGroups) {
    const c = group.column;
    if (!groupColumns.has(c)) groupColumns.set(c, []);
    groupColumns.get(c)!.push(group);
  }

  let canvasX = PADDING;
  for (const col of Array.from(groupColumns.keys()).sort((a, b) => a - b)) {
    const colGroups = groupColumns.get(col)!;
    const maxWidth = Math.max(...colGroups.map((g) => g.width));

    let canvasY = PADDING;
    for (const group of colGroups) {
      // Compute group top-left position
      const groupX = canvasX;
      const groupY = canvasY;

      // Translate all group blocks to absolute canvas positions
      for (const lb of group.layoutBlocks) {
        lb.x += groupX + GROUP_PAD_X;
        lb.y += groupY + GROUP_PAD_TOP;
      }

      canvasY += group.height + GROUP_GAP;
    }

    canvasX += maxWidth + H_GAP;
  }

  // Flatten all layout blocks
  const result: LayoutBlock[] = [];
  for (const group of hwGroups) {
    result.push(...group.layoutBlocks);
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

function areBlocksInSameGroup(fromBlockId: string, toBlockId: string, layoutMap: Map<string, LayoutBlock>): boolean {
  const fromLb = layoutMap.get(fromBlockId);
  const toLb = layoutMap.get(toBlockId);
  if (!fromLb || !toLb) return false;
  const fromHw = fromLb.block.host_hardware;
  const toHw = toLb.block.host_hardware;
  if (!fromHw || !toHw) return false;
  return fromHw === toHw;
}

function lineIntersectsBlock(
  x: number,
  startY: number,
  endY: number,
  block: LayoutBlock,
  margin: number
): boolean {
  const minY = Math.min(startY, endY);
  const maxY = Math.max(startY, endY);
  const blockLeft = block.x - margin;
  const blockRight = block.x + block.width + margin;
  const blockTop = block.y - margin;
  const blockBottom = block.y + block.height + margin;
  return x >= blockLeft && x <= blockRight && maxY >= blockTop && minY <= blockBottom;
}

function findClearVerticalChannel(
  preferredX: number,
  startY: number,
  endY: number,
  blocks: LayoutBlock[]
): number {
  const margin = 10;
  if (!blocks.some((b) => lineIntersectsBlock(preferredX, startY, endY, b, margin))) {
    return preferredX;
  }
  for (let offset = 20; offset <= 300; offset += 20) {
    const leftX = preferredX - offset;
    if (!blocks.some((b) => lineIntersectsBlock(leftX, startY, endY, b, margin))) {
      return leftX;
    }
    const rightX = preferredX + offset;
    if (!blocks.some((b) => lineIntersectsBlock(rightX, startY, endY, b, margin))) {
      return rightX;
    }
  }
  return preferredX;
}

function computeOrthogonalPath(
  fromPort: { x: number; y: number },
  toPort: { x: number; y: number },
  allBlocks: LayoutBlock[],
  sameGroup: boolean,
  verticalOffset: number
): string {
  const exitDistance = sameGroup ? 20 : 40;
  const exitX = fromPort.x + exitDistance;
  const entryX = toPort.x - exitDistance;
  const fromY = fromPort.y + verticalOffset;
  const toY = toPort.y + verticalOffset;

  // SAME-COLUMN connection: blocks are vertically aligned
  if (Math.abs(toPort.x - fromPort.x) < BLOCK_WIDTH * 0.5) {
    const jogX = fromPort.x + 30 + Math.abs(verticalOffset);
    return [
      `M ${fromPort.x} ${fromPort.y}`,
      `L ${jogX} ${fromY}`,
      `L ${jogX} ${toY}`,
      `L ${toPort.x} ${toPort.y}`,
    ].join(" ");
  }

  if (toPort.x > fromPort.x + exitDistance * 2) {
    // FORWARD connection: source is left of destination
    const midX = (exitX + entryX) / 2;
    const baseChannelX = findClearVerticalChannel(midX, fromY, toY, allBlocks);
    const channelX = baseChannelX + verticalOffset * 0.7;
    if (Math.abs(fromY - toY) < 1) {
      // Straight horizontal — no vertical jog needed
      return `M ${fromPort.x} ${fromPort.y} L ${toPort.x} ${toPort.y}`;
    }
    return [
      `M ${fromPort.x} ${fromPort.y}`,
      `L ${channelX} ${fromY}`,
      `L ${channelX} ${toY}`,
      `L ${toPort.x} ${toPort.y}`,
    ].join(" ");
  } else {
    // BACKWARD connection: destination is left of or at same x as source
    const nearSourceBlocks = allBlocks.filter((b) => Math.abs(b.y - fromPort.y) < b.height + 40);
    const sourceRight = nearSourceBlocks.length > 0
      ? Math.max(...nearSourceBlocks.map((b) => b.x + b.width), fromPort.x)
      : fromPort.x;
    const nearDestBlocks = allBlocks.filter((b) => Math.abs(b.y - toPort.y) < b.height + 40);
    const destLeft = nearDestBlocks.length > 0
      ? Math.min(...nearDestBlocks.map((b) => b.x), toPort.x)
      : toPort.x;
    const loopRightX = sourceRight + 30;
    const loopLeftX = destLeft - 30;
    if (allBlocks.length === 0) {
      return `M ${fromPort.x} ${fromPort.y} L ${toPort.x} ${toPort.y}`;
    }
    const allBlockTops = allBlocks.map((b) => b.y);
    const allBlockBottoms = allBlocks.map((b) => b.y + b.height);
    const minTop = Math.min(...allBlockTops) - 40;
    const maxBottom = Math.max(...allBlockBottoms) + 40;
    const goUp = Math.abs(fromY - minTop) + Math.abs(toY - minTop) <
                 Math.abs(fromY - maxBottom) + Math.abs(toY - maxBottom);
    const loopY = goUp ? minTop + verticalOffset : maxBottom + verticalOffset;
    return [
      `M ${fromPort.x} ${fromPort.y}`,
      `L ${loopRightX} ${fromY}`,
      `L ${loopRightX} ${loopY}`,
      `L ${loopLeftX} ${loopY}`,
      `L ${loopLeftX} ${toY}`,
      `L ${toPort.x} ${toPort.y}`,
    ].join(" ");
  }
}

// ---- Path helpers for per-segment editing ----

function parsePathPoints(pathStr: string): { x: number; y: number }[] {
  const parts = pathStr.split(/\s+/);
  const points: { x: number; y: number }[] = [];
  for (let i = 0; i < parts.length; i++) {
    if (parts[i] === "M" || parts[i] === "L") {
      points.push({ x: parseFloat(parts[i + 1]), y: parseFloat(parts[i + 2]) });
    }
  }
  return points;
}

function pointsToPath(points: { x: number; y: number }[]): string {
  return points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
}

function pointToSegmentDist(
  px: number, py: number,
  ax: number, ay: number,
  bx: number, by: number
): number {
  const dx = bx - ax;
  const dy = by - ay;
  const lenSq = dx * dx + dy * dy;
  if (lenSq === 0) return Math.hypot(px - ax, py - ay);
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / lenSq));
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

/** Move interior path points (indices 1..n-2) by their {dx,dy} overrides.
 *  First and last points are port anchors and never move. */
function applyPointOverrides(pathStr: string, overrides: { dx: number; dy: number }[]): string {
  const points = parsePathPoints(pathStr);
  if (points.length < 3) return pathStr; // No interior points
  for (let i = 1; i < points.length - 1; i++) {
    const ov = overrides[i - 1];
    if (ov && (Math.abs(ov.dx) > 0.1 || Math.abs(ov.dy) > 0.1)) {
      points[i].x += ov.dx;
      points[i].y += ov.dy;
    }
  }
  return pointsToPath(points);
}

/** Insert waypoints into a path, splitting segments with a zero-length jog.
 *  Each waypoint creates 2 extra points (and 2 extra segments).
 *  Returns the expanded path and an array mapping old segment indices to new ones.
 */
function insertWaypointsIntoPath(
  pathStr: string,
  waypoints: { x: number; y: number }[]
): { path: string; segmentMap: number[] } {
  if (waypoints.length === 0) return { path: pathStr, segmentMap: [] };

  let points = parsePathPoints(pathStr);
  // Sort waypoints in reverse order of their position along the path
  // to avoid index shifting when inserting
  const wpWithSeg = waypoints.map((wp) => {
    let bestDist = Infinity;
    let bestIdx = 0;
    let bestT = 0;
    for (let s = 0; s < points.length - 1; s++) {
      const p1 = points[s];
      const p2 = points[s + 1];
      const dx = p2.x - p1.x;
      const dy = p2.y - p1.y;
      const lenSq = dx * dx + dy * dy;
      const t = lenSq === 0 ? 0 : Math.max(0, Math.min(1, ((wp.x - p1.x) * dx + (wp.y - p1.y) * dy) / lenSq));
      const dist = Math.hypot(wp.x - (p1.x + t * dx), wp.y - (p1.y + t * dy));
      if (dist < bestDist) {
        bestDist = dist;
        bestIdx = s;
        bestT = t;
      }
    }
    return { wp, segIdx: bestIdx, t: bestT };
  });

  // Sort by segment index descending, then t descending (insert from end to preserve indices)
  wpWithSeg.sort((a, b) => b.segIdx - a.segIdx || b.t - a.t);

  // Build segment index map (original segment index → new start index after insertions)
  const segmentMap: number[] = [];
  let insertedCount = 0;

  for (const { segIdx } of wpWithSeg) {
    const p1 = points[segIdx];
    const p2 = points[segIdx + 1];
    const isHoriz = Math.abs(p1.y - p2.y) < 1;

    if (isHoriz) {
      // Split horizontal segment: insert two points at (wp.x, y) creating a vertical jog
      const splitY = p1.y;
      const splitX = wpWithSeg.find((w) => w.segIdx === segIdx)!.wp.x;
      // Clamp X between segment endpoints
      const minX = Math.min(p1.x, p2.x) + 5;
      const maxX = Math.max(p1.x, p2.x) - 5;
      const clampedX = Math.max(minX, Math.min(maxX, splitX));
      points.splice(segIdx + 1, 0, { x: clampedX, y: splitY }, { x: clampedX, y: splitY });
    } else {
      // Split vertical segment: insert two points at (x, wp.y) creating a horizontal jog
      const splitX = p1.x;
      const splitY = wpWithSeg.find((w) => w.segIdx === segIdx)!.wp.y;
      const minY = Math.min(p1.y, p2.y) + 5;
      const maxY = Math.max(p1.y, p2.y) - 5;
      const clampedY = Math.max(minY, Math.min(maxY, splitY));
      points.splice(segIdx + 1, 0, { x: splitX, y: clampedY }, { x: splitX, y: clampedY });
    }
  }

  return { path: pointsToPath(points), segmentMap };
}

function getPathMidpoint(pathStr: string): { x: number; y: number } {
  const points = parsePathPoints(pathStr);
  if (points.length < 2) return { x: 0, y: 0 };

  // Prefer horizontal segments for label placement (text reads naturally)
  let bestHorizIdx = -1;
  let bestHorizLen = 0;
  let longestIdx = 0;
  let longestLen = 0;

  for (let i = 0; i < points.length - 1; i++) {
    const dx = Math.abs(points[i + 1].x - points[i].x);
    const dy = Math.abs(points[i + 1].y - points[i].y);
    const len = dx + dy;
    if (len > longestLen) {
      longestLen = len;
      longestIdx = i;
    }
    if (dy < 1 && dx > bestHorizLen && dx >= 30) {
      bestHorizLen = dx;
      bestHorizIdx = i;
    }
  }

  const idx = bestHorizIdx >= 0 ? bestHorizIdx : longestIdx;
  return {
    x: (points[idx].x + points[idx + 1].x) / 2,
    y: (points[idx].y + points[idx + 1].y) / 2,
  };
}

export function BlockDiagramViewer({ designId, blocks, connections, phase, isLoading, onApprove }: BlockDiagramViewerProps) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [hoveredConn, setHoveredConn] = useState<number | null>(null);
  const [hoveredBlock, setHoveredBlock] = useState<string | null>(null);
  const lastPos = useRef({ x: 0, y: 0 });
  const [draggedBlockId, setDraggedBlockId] = useState<string | null>(null);
  const draggedBlockRef = useRef<string | null>(null);
  const [blockPositionOverrides, setBlockPositionOverrides] = useState<Map<string, { x: number; y: number }>>(new Map());
  const [connPointOverrides, setConnPointOverrides] = useState<Map<number, { dx: number; dy: number }[]>>(new Map());
  const [connWaypoints, setConnWaypoints] = useState<Map<number, { x: number; y: number }[]>>(new Map());
  const [selectedConn, setSelectedConn] = useState<number | null>(null);
  const [hoveredNode, setHoveredNode] = useState<{ connIdx: number; pointIdx: number } | null>(null);
  const draggedNodeRef = useRef<{ connIdx: number; pointIdx: number } | null>(null);
  const dragStartPos = useRef({ blockX: 0, blockY: 0, mouseX: 0, mouseY: 0 });
  const connDragStart = useRef({ mouseX: 0, mouseY: 0 });
  const connDragBaseOverrides = useRef<{ dx: number; dy: number }[]>([]);
  const zoomRef = useRef(zoom);
  zoomRef.current = zoom;
  const panRef = useRef(pan);
  panRef.current = pan;
  const svgRef = useRef<SVGSVGElement>(null);
  const computedPathsRef = useRef<({ path: string; wpPath: string; points: { x: number; y: number }[] } | null)[]>([]);
  const hoveredConnRef = useRef<number | null>(null);

  // Pinch/scroll zoom + two-finger pan via native event listener (passive: false to allow preventDefault)
  const canvasRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = canvasRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (e.ctrlKey) {
        // Pinch-to-zoom gesture (ctrlKey is set by macOS for trackpad pinch)
        const delta = -e.deltaY * 0.01;
        const oldZoom = zoomRef.current;
        const newZoom = Math.min(Math.max(oldZoom * (1 + delta), 0.2), 5);
        const rect = el.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        const contentX = (mouseX - panRef.current.x) / oldZoom;
        const contentY = (mouseY - panRef.current.y) / oldZoom;
        const newPanX = mouseX - contentX * newZoom;
        const newPanY = mouseY - contentY * newZoom;
        setZoom(newZoom);
        setPan({ x: newPanX, y: newPanY });
      } else {
        // Two-finger scroll → pan the canvas
        setPan((prev) => ({
          x: prev.x - e.deltaX,
          y: prev.y - e.deltaY,
        }));
      }
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  // Load saved layout from localStorage on mount (or when designId changes)
  useEffect(() => {
    if (!designId) return;
    const saved = loadLayout(designId);
    if (!saved) return;
    if (saved.blockPositions.length > 0) {
      setBlockPositionOverrides(new Map(saved.blockPositions));
    }
    if (saved.pointOverrides.length > 0) {
      setConnPointOverrides(new Map(saved.pointOverrides));
    }
    if (saved.waypoints.length > 0) {
      setConnWaypoints(new Map(saved.waypoints));
    }
  }, [designId]);

  // Debounced save to localStorage when layout state changes
  const layoutSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [layoutSaved, setLayoutSaved] = useState(false);
  useEffect(() => {
    if (!designId) return;
    // Skip saving if all state is empty (initial mount before load)
    if (blockPositionOverrides.size === 0 && connPointOverrides.size === 0 && connWaypoints.size === 0) return;
    if (layoutSaveTimer.current) clearTimeout(layoutSaveTimer.current);
    layoutSaveTimer.current = setTimeout(() => {
      saveLayout(designId, {
        blockPositions: [...blockPositionOverrides.entries()],
        pointOverrides: [...connPointOverrides.entries()],
        waypoints: [...connWaypoints.entries()],
      });
      setLayoutSaved(true);
      setTimeout(() => setLayoutSaved(false), 2000);
    }, 500);
    return () => {
      if (layoutSaveTimer.current) clearTimeout(layoutSaveTimer.current);
    };
  }, [designId, blockPositionOverrides, connPointOverrides, connWaypoints]);

  const layout = useMemo(() => {
    const baseLayout = layoutBlocks(blocks, connections);
    return baseLayout.map((lb) => {
      const override = blockPositionOverrides.get(lb.block.id);
      return override ? { ...lb, x: override.x, y: override.y } : lb;
    });
  }, [blocks, connections, blockPositionOverrides]);

  const layoutMap = useMemo(() => {
    const map = new Map<string, LayoutBlock>();
    for (const lb of layout) map.set(lb.block.id, lb);
    return map;
  }, [layout]);

  // Precompute connection grouping and spread offsets
  const connectionOffsets = useMemo(() => {
    const pairGroups = new Map<string, number[]>();
    connections.forEach((conn, i) => {
      const key = [conn.from_block, conn.to_block].sort().join('<->');
      if (!pairGroups.has(key)) pairGroups.set(key, []);
      pairGroups.get(key)!.push(i);
    });
    const offsets = new Map<number, number>();
    for (const indices of pairGroups.values()) {
      const groupSize = indices.length;
      indices.forEach((idx, positionInGroup) => {
        const spreadFactor = groupSize === 1 ? 0 : (positionInGroup - (groupSize - 1) / 2);
        offsets.set(idx, spreadFactor * CONNECTION_SPREAD);
      });
    }
    return offsets;
  }, [connections]);

  // Precompute all rendered connection paths (shared by rendering and hit testing)
  const computedPaths = useMemo(() => {
    return connections.map((conn, i) => {
      const fromLb = layoutMap.get(conn.from_block);
      const toLb = layoutMap.get(conn.to_block);
      if (!fromLb || !toLb) return null;
      const fromPort = getPortPosition(fromLb, conn.signal_name, "output");
      const toPort = getPortPosition(toLb, conn.signal_name, "input");
      const sameGroup = areBlocksInSameGroup(conn.from_block, conn.to_block, layoutMap);
      const vertOffset = connectionOffsets.get(i) ?? 0;
      const basePath = computeOrthogonalPath(fromPort, toPort, layout, sameGroup, vertOffset);
      const wps = connWaypoints.get(i) ?? [];
      const { path: wpPath } = insertWaypointsIntoPath(basePath, wps);
      const pointOvs = connPointOverrides.get(i);
      const path = pointOvs && pointOvs.length > 0 ? applyPointOverrides(wpPath, pointOvs) : wpPath;
      const points = parsePathPoints(path);
      return { path, wpPath, points };
    });
  }, [connections, layoutMap, connectionOffsets, layout, connWaypoints, connPointOverrides]);
  computedPathsRef.current = computedPaths;

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault(); // Prevent browser text selection during drag
    // Click on background deselects any selected connection
    setSelectedConn(null);
    setDragging(true);
    lastPos.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handleBlockMouseDown = useCallback((blockId: string, blockX: number, blockY: number, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    draggedBlockRef.current = blockId;
    setDraggedBlockId(blockId);
    dragStartPos.current = { blockX, blockY, mouseX: e.clientX, mouseY: e.clientY };
  }, []);

  const handleConnMouseDown = useCallback((_eventConnIdx: number, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    // Use geometric nearest-path detection instead of trusting SVG event
    // dispatch. Overlapping hit areas can select the wrong connection.
    const svgEl = svgRef.current;
    if (!svgEl) return;
    const svgRect = svgEl.getBoundingClientRect();
    const vb = svgEl.viewBox.baseVal;
    if (vb.width === 0 || vb.height === 0) return;
    const svgX = (e.clientX - svgRect.left) * vb.width / svgRect.width;
    const svgY = (e.clientY - svgRect.top) * vb.height / svgRect.height;

    const paths = computedPathsRef.current;
    let bestConnIdx = _eventConnIdx;
    let bestDist = Infinity;
    for (let ci = 0; ci < paths.length; ci++) {
      const cp = paths[ci];
      if (!cp) continue;
      for (let s = 0; s < cp.points.length - 1; s++) {
        const d = pointToSegmentDist(svgX, svgY,
          cp.points[s].x, cp.points[s].y,
          cp.points[s + 1].x, cp.points[s + 1].y);
        if (d < bestDist) { bestDist = d; bestConnIdx = ci; }
      }
    }

    const targetIdx = bestConnIdx;
    const cp = paths[targetIdx];

    // Find nearest interior node — if close enough, start dragging it
    if (cp && cp.points.length >= 3) {
      let nearestNodeIdx = -1;
      let nearestNodeDist = Infinity;
      for (let pi = 1; pi < cp.points.length - 1; pi++) {
        const d = Math.hypot(cp.points[pi].x - svgX, cp.points[pi].y - svgY);
        if (d < nearestNodeDist) { nearestNodeDist = d; nearestNodeIdx = pi; }
      }

      if (nearestNodeIdx >= 0 && nearestNodeDist < 25) {
        // Start dragging this node
        draggedNodeRef.current = { connIdx: targetIdx, pointIdx: nearestNodeIdx };
        connDragStart.current = { mouseX: e.clientX, mouseY: e.clientY };
        const existing = connPointOverrides.get(targetIdx) ?? [];
        connDragBaseOverrides.current = [...existing];
      }
    }

    setSelectedConn(targetIdx);
    setHoveredConn(targetIdx);
    hoveredConnRef.current = targetIdx;
  }, [connPointOverrides]);

  const handleNodeMouseDown = useCallback((connIdx: number, pointIdx: number, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    draggedNodeRef.current = { connIdx, pointIdx };
    connDragStart.current = { mouseX: e.clientX, mouseY: e.clientY };
    const existing = connPointOverrides.get(connIdx) ?? [];
    connDragBaseOverrides.current = [...existing];
    setSelectedConn(connIdx);
  }, [connPointOverrides]);

  const handleConnDoubleClick = useCallback((connIdx: number, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    const svgEl = svgRef.current;
    if (!svgEl) return;
    const svgRect = svgEl.getBoundingClientRect();
    const vb = svgEl.viewBox.baseVal;
    const svgX = (e.clientX - svgRect.left) * vb.width / svgRect.width;
    const svgY = (e.clientY - svgRect.top) * vb.height / svgRect.height;

    // Check if clicking near an existing waypoint → remove it
    const existingWps = connWaypoints.get(connIdx) ?? [];
    const removeIdx = existingWps.findIndex((wp) => Math.hypot(wp.x - svgX, wp.y - svgY) < 15);
    if (removeIdx >= 0) {
      removeWaypoint(connIdx, removeIdx);
      return;
    }

    // Add new waypoint at click position
    setConnWaypoints((prev) => {
      const updated = new Map(prev);
      const wps = [...(prev.get(connIdx) ?? []), { x: svgX, y: svgY }];
      updated.set(connIdx, wps);
      return updated;
    });

    // Insert 2 zero-overrides into the point overrides array for the 2 new interior points
    setConnPointOverrides((prev) => {
      const updated = new Map(prev);
      const overrides = [...(prev.get(connIdx) ?? [])];
      const conn = connections[connIdx];
      const fromLb = layoutMap.get(conn.from_block);
      const toLb = layoutMap.get(conn.to_block);
      if (fromLb && toLb) {
        const fromPort = getPortPosition(fromLb, conn.signal_name, "output");
        const toPort = getPortPosition(toLb, conn.signal_name, "input");
        const sameGroup = areBlocksInSameGroup(conn.from_block, conn.to_block, layoutMap);
        const vertOffset = connectionOffsets.get(connIdx) ?? 0;
        const basePath = computeOrthogonalPath(fromPort, toPort, layout, sameGroup, vertOffset);
        const { path: expandedPath } = insertWaypointsIntoPath(basePath, existingWps);
        const expandedPts = parsePathPoints(expandedPath);

        // Pad overrides to match current interior point count
        while (overrides.length < expandedPts.length - 2) overrides.push({ dx: 0, dy: 0 });

        // Find nearest segment for insertion
        let bestSeg = 0;
        let bestDist = Infinity;
        for (let s = 0; s < expandedPts.length - 1; s++) {
          const dist = pointToSegmentDist(svgX, svgY,
            expandedPts[s].x, expandedPts[s].y, expandedPts[s + 1].x, expandedPts[s + 1].y);
          if (dist < bestDist) { bestDist = dist; bestSeg = s; }
        }
        // Insert 2 zero-overrides at the split point
        overrides.splice(bestSeg, 0, { dx: 0, dy: 0 }, { dx: 0, dy: 0 });
      }
      updated.set(connIdx, overrides);
      return updated;
    });
  }, [connWaypoints, connections, layoutMap, connectionOffsets, layout]);

  const removeWaypoint = useCallback((connIdx: number, wpIdx: number) => {
    const existingWps = connWaypoints.get(connIdx) ?? [];

    setConnWaypoints((prev) => {
      const updated = new Map(prev);
      const wps = [...(prev.get(connIdx) ?? [])];
      wps.splice(wpIdx, 1);
      if (wps.length === 0) updated.delete(connIdx);
      else updated.set(connIdx, wps);
      return updated;
    });

    // Remove the 2 point override entries for this waypoint's interior points
    setConnPointOverrides((prev) => {
      const updated = new Map(prev);
      const overrides = [...(prev.get(connIdx) ?? [])];
      const conn = connections[connIdx];
      const fromLb = layoutMap.get(conn.from_block);
      const toLb = layoutMap.get(conn.to_block);
      if (fromLb && toLb) {
        const fromPort = getPortPosition(fromLb, conn.signal_name, "output");
        const toPort = getPortPosition(toLb, conn.signal_name, "input");
        const sameGroup = areBlocksInSameGroup(conn.from_block, conn.to_block, layoutMap);
        const vertOffset = connectionOffsets.get(connIdx) ?? 0;
        const basePath = computeOrthogonalPath(fromPort, toPort, layout, sameGroup, vertOffset);
        const basePoints = parsePathPoints(basePath);

        let bestSeg = 0;
        let bestDist = Infinity;
        for (let s = 0; s < basePoints.length - 1; s++) {
          const dist = pointToSegmentDist(existingWps[wpIdx].x, existingWps[wpIdx].y,
            basePoints[s].x, basePoints[s].y, basePoints[s + 1].x, basePoints[s + 1].y);
          if (dist < bestDist) { bestDist = dist; bestSeg = s; }
        }
        const removeAt = bestSeg + wpIdx * 2;
        if (removeAt < overrides.length) overrides.splice(removeAt, Math.min(2, overrides.length - removeAt));
      }
      if (overrides.length === 0) updated.delete(connIdx);
      else updated.set(connIdx, overrides);
      return updated;
    });
  }, [connWaypoints, connections, layoutMap, connectionOffsets, layout]);

  const handleCanvasMouseMove = useCallback(
    (e: React.MouseEvent) => {
      // Node drag — move the grabbed node freely in both X and Y
      const activeNode = draggedNodeRef.current;
      if (activeNode) {
        const rawDx = e.clientX - connDragStart.current.mouseX;
        const rawDy = e.clientY - connDragStart.current.mouseY;
        if (Math.abs(rawDx) < 2 && Math.abs(rawDy) < 2) return;
        const dx = rawDx / zoomRef.current;
        const dy = rawDy / zoomRef.current;
        const { connIdx, pointIdx } = activeNode;
        setConnPointOverrides((prev) => {
          const updated = new Map(prev);
          const overrides = [...connDragBaseOverrides.current];
          // Ensure array covers this point (pointIdx is 1-based for interior, override index = pointIdx - 1)
          const ovIdx = pointIdx - 1;
          while (overrides.length <= ovIdx) overrides.push({ dx: 0, dy: 0 });
          const base = connDragBaseOverrides.current[ovIdx] ?? { dx: 0, dy: 0 };
          overrides[ovIdx] = { dx: base.dx + dx, dy: base.dy + dy };
          updated.set(connIdx, overrides);
          return updated;
        });
        return;
      }

      // Block drag — use ref for immediate access
      const activeBlock = draggedBlockRef.current;
      if (activeBlock) {
        const rawDx = e.clientX - dragStartPos.current.mouseX;
        const rawDy = e.clientY - dragStartPos.current.mouseY;
        // Require minimum drag distance to avoid accidental drags on click
        if (Math.abs(rawDx) < 5 && Math.abs(rawDy) < 5) return;
        const dx = rawDx / zoomRef.current;
        const dy = rawDy / zoomRef.current;
        setBlockPositionOverrides((prev) => {
          const updated = new Map(prev);
          updated.set(activeBlock, {
            x: Math.max(0, dragStartPos.current.blockX + dx),
            y: Math.max(0, dragStartPos.current.blockY + dy),
          });
          return updated;
        });
        return;
      }
      // Not dragging anything — use geometric nearest-path for hover detection
      if (!dragging) {
        const svgEl = svgRef.current;
        if (svgEl) {
          const svgRect = svgEl.getBoundingClientRect();
          const vb = svgEl.viewBox.baseVal;
          if (vb.width > 0 && vb.height > 0) {
            const svgX = (e.clientX - svgRect.left) * vb.width / svgRect.width;
            const svgY = (e.clientY - svgRect.top) * vb.height / svgRect.height;

            let bestIdx: number | null = null;
            let bestDist = Infinity;
            const paths = computedPathsRef.current;
            for (let ci = 0; ci < paths.length; ci++) {
              const cp = paths[ci];
              if (!cp) continue;
              for (let s = 0; s < cp.points.length - 1; s++) {
                const d = pointToSegmentDist(svgX, svgY,
                  cp.points[s].x, cp.points[s].y,
                  cp.points[s + 1].x, cp.points[s + 1].y);
                if (d < bestDist) { bestDist = d; bestIdx = ci; }
              }
            }

            const newHovered = bestDist < 12 ? bestIdx : null;
            if (newHovered !== hoveredConnRef.current) {
              hoveredConnRef.current = newHovered;
              setHoveredConn(newHovered);
            }
          }
        }
        return;
      }

      // Canvas pan
      const dx = e.clientX - lastPos.current.x;
      const dy = e.clientY - lastPos.current.y;
      setPan((p) => ({ x: p.x + dx, y: p.y + dy }));
      lastPos.current = { x: e.clientX, y: e.clientY };
    },
    [dragging]
  );

  const handleCanvasMouseUp = useCallback(() => {
    draggedBlockRef.current = null;
    draggedNodeRef.current = null;
    setDraggedBlockId(null);
    setDragging(false);
  }, []);

  const handleReset = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

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
    <div className="relative h-full w-full overflow-hidden rounded-md border border-border" style={{ backgroundColor: '#0f172a' }}>
      {/* Toolbar */}
      <div className="absolute right-3 top-3 z-10 flex items-center gap-2">
        {layoutSaved && (
          <div className="flex items-center gap-1 rounded-md border border-green-500/30 bg-green-500/10 px-2 py-1 text-[11px] text-green-400 transition-opacity">
            <Check className="h-3 w-3" />
            Layout saved
          </div>
        )}
        {phase === "reviewing" && (
          <Button
            onClick={onApprove}
            disabled={isLoading}
            className="h-8 px-3 bg-green-600 hover:bg-green-500 text-white text-xs font-semibold"
          >
            <CheckCircle className="h-3.5 w-3.5 mr-1.5" />
            Approve Architecture
          </Button>
        )}
        <div className="flex items-center gap-1 rounded-md border border-border bg-surface-raised p-1">
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
      </div>

      {/* Canvas */}
      <div
        ref={canvasRef}
        className="h-full w-full cursor-move active:cursor-grabbing"
        style={{ userSelect: 'none', WebkitUserSelect: 'none' } as React.CSSProperties}
        onMouseDown={handleMouseDown}
        onMouseMove={handleCanvasMouseMove}
        onMouseUp={handleCanvasMouseUp}
        onMouseLeave={handleCanvasMouseUp}
      >
        <div
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: "0 0",
            transition: dragging ? "none" : "transform 0.15s ease",
          }}
        >
          {/* Infinite grid background — extends far beyond content in all directions */}
          <div
            style={{
              position: "absolute",
              left: -5000,
              top: -5000,
              width: svgWidth + 10000,
              height: svgHeight + 10000,
              backgroundImage:
                "linear-gradient(to right, #1e293b 1px, transparent 1px), linear-gradient(to bottom, #1e293b 1px, transparent 1px)",
              backgroundSize: "20px 20px",
              backgroundPosition: "5000px 5000px",
              pointerEvents: "none",
            }}
          />
          <svg ref={svgRef} width={svgWidth} height={svgHeight} viewBox={`0 0 ${svgWidth} ${svgHeight}`} overflow="visible" style={{ position: "relative" }}>
            <defs>
              {/* Arrow markers for connection lines */}
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

            {/* Blocks */}
            {layout.map((lb) => {
              const { block, x, y, width, height } = lb;
              return (
                <g
                  key={block.id}
                  onMouseDown={(e) => handleBlockMouseDown(block.id, x, y, e)}
                  onMouseEnter={() => setHoveredBlock(block.id)}
                  onMouseLeave={() => setHoveredBlock(null)}
                  style={{ cursor: draggedBlockId === block.id ? 'grabbing' : 'grab' }}
                >
                  {/* Block body */}
                  <rect
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    rx={8}
                    ry={8}
                    fill={hoveredBlock === block.id || draggedBlockId === block.id ? "#253347" : "#1e293b"}
                    stroke={hoveredBlock === block.id || draggedBlockId === block.id ? "#3B82F6" : "#334155"}
                    strokeWidth={hoveredBlock === block.id || draggedBlockId === block.id ? 2 : 1.5}
                    style={{ transition: 'fill 0.1s ease, stroke 0.1s ease' }}
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

            {/* Connections */}
            {connections.map((conn, i) => {
              const computed = computedPaths[i];
              if (!computed) return null;
              const { path } = computed;
              const wps = connWaypoints.get(i) ?? [];

              const color = SIGNAL_COLORS[conn.signal_type] ?? "#6B7280";

              // Label positioning — midpoint of longest horizontal segment
              const midPt = getPathMidpoint(path);
              const labelX = isNaN(midPt.x) ? 0 : midPt.x;
              const labelY = isNaN(midPt.y) ? 0 : midPt.y;

              // Label background pill sizing
              const displayName = conn.signal_name.length > 16 ? conn.signal_name.slice(0, 14) + '..' : conn.signal_name;
              const textWidth = displayName.length * 5.5;
              const labelPadding = 4;
              const rectWidth = textWidth + labelPadding * 2;
              const rectHeight = 14;
              const rectX = labelX - rectWidth / 2;
              const rectY = labelY - rectHeight / 2 - 2;

              // Hover + selection opacity
              const isHovered = hoveredConn === i;
              const isSelected = selectedConn === i;
              const anyHovered = hoveredConn !== null;
              const connOpacity = isSelected ? 1 : anyHovered ? (isHovered ? 0.8 : 0.2) : 0.8;
              const labelOpacity = isSelected ? 1 : anyHovered ? (isHovered ? 0.9 : 0.3) : 0.9;
              const strokeWidth = isSelected ? 3 : isHovered ? 2.5 : 1.5;

              return (
                <g
                  key={`conn-${i}`}
                  onMouseDown={(e) => handleConnMouseDown(i, e)}
                  onDoubleClick={(e) => handleConnDoubleClick(i, e)}
                  style={{
                    cursor: (isHovered || isSelected) ? 'move' : 'default',
                    transition: 'opacity 0.15s ease, stroke-width 0.15s ease',
                  }}
                >
                  {/* Invisible wider hit area for easier hover */}
                  <path
                    d={path}
                    fill="none"
                    stroke="transparent"
                    strokeWidth="14"
                    pointerEvents="stroke"
                  />
                  {/* Selection glow */}
                  {isSelected && (
                    <path
                      d={path}
                      fill="none"
                      stroke={color}
                      strokeWidth={8}
                      opacity={0.2}
                      pointerEvents="none"
                    />
                  )}
                  {/* Visible connection line */}
                  <path
                    d={path}
                    fill="none"
                    stroke={color}
                    strokeWidth={strokeWidth}
                    markerEnd={`url(#arrow-${conn.signal_type})`}
                    opacity={connOpacity}
                    style={{ transition: 'opacity 0.15s ease, stroke-width 0.15s ease' }}
                  />
                  {/* Label background pill */}
                  <rect
                    x={rectX}
                    y={rectY}
                    width={rectWidth}
                    height={rectHeight}
                    rx={7}
                    fill="#0f172a"
                    fillOpacity={0.95}
                    stroke={color}
                    strokeWidth={0.5}
                    strokeOpacity={0.5}
                    opacity={labelOpacity}
                    style={{ transition: 'opacity 0.15s ease' }}
                  />
                  {/* Label text */}
                  <text
                    x={labelX}
                    y={labelY}
                    textAnchor="middle"
                    fill={color}
                    fontSize="9"
                    fontFamily="JetBrains Mono, monospace"
                    opacity={labelOpacity}
                    style={{ transition: 'opacity 0.15s ease' }}
                  >
                    {displayName}
                  </text>
                  {/* Interior nodes — visible when connection is hovered or selected */}
                  {(isSelected || isHovered) && computed.points.length >= 3 && (() => {
                    const pts = computed.points;
                    // Check which interior points are waypoint-added (for delete affordance)
                    const wpPositions = wps;
                    return pts.slice(1, -1).map((pt, idx) => {
                      const pointIdx = idx + 1; // 1-based index in the points array
                      const isNodeHov = hoveredNode?.connIdx === i && hoveredNode?.pointIdx === pointIdx;
                      const isDragging = draggedNodeRef.current?.connIdx === i && draggedNodeRef.current?.pointIdx === pointIdx;
                      // Check if this node is near a waypoint (for right-click delete)
                      const nearWpIdx = wpPositions.findIndex((wp) => Math.hypot(wp.x - pt.x, wp.y - pt.y) < 30);
                      return (
                        <g
                          key={`node-${idx}`}
                          onMouseDown={(ev) => handleNodeMouseDown(i, pointIdx, ev)}
                          onMouseEnter={() => setHoveredNode({ connIdx: i, pointIdx })}
                          onMouseLeave={() => setHoveredNode(null)}
                          onContextMenu={(ev) => {
                            if (nearWpIdx >= 0) {
                              ev.stopPropagation();
                              ev.preventDefault();
                              removeWaypoint(i, nearWpIdx);
                            }
                          }}
                          style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
                        >
                          {/* Larger invisible hit area */}
                          <circle cx={pt.x} cy={pt.y} r={12} fill="transparent" />
                          {/* Node circle */}
                          <circle
                            cx={pt.x} cy={pt.y}
                            r={isNodeHov || isDragging ? 5.5 : 4}
                            fill={nearWpIdx >= 0 && isNodeHov ? "#7f1d1d" : isNodeHov || isDragging ? "#1e3a5f" : "#0f172a"}
                            stroke={nearWpIdx >= 0 && isNodeHov ? "#ef4444" : color}
                            strokeWidth={isNodeHov || isDragging ? 2 : 1.5}
                            opacity={isSelected ? 0.9 : 0.7}
                          />
                          {/* Inner dot */}
                          {!(nearWpIdx >= 0 && isNodeHov) && (
                            <circle
                              cx={pt.x} cy={pt.y} r={2}
                              fill={color}
                              opacity={isSelected ? 1 : 0.7}
                              pointerEvents="none"
                            />
                          )}
                          {/* Delete hint for waypoint nodes */}
                          {nearWpIdx >= 0 && isNodeHov && (
                            <text
                              x={pt.x} y={pt.y + 3.5}
                              textAnchor="middle" fill="#ef4444"
                              fontSize="10" fontWeight="bold"
                              pointerEvents="none"
                            >
                              ×
                            </text>
                          )}
                        </g>
                      );
                    });
                  })()}
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
