"use client";

import { useState, useRef, useCallback } from "react";
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SchematicViewer() {
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
          {/* Placeholder schematic SVG */}
          <svg width="600" height="300" viewBox="0 0 600 300" className="text-text-muted">
            {/* Grid */}
            <defs>
              <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#1a1a1a" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect width="600" height="300" fill="url(#grid)" />

            {/* Driver symbol */}
            <g transform="translate(80, 100)">
              <circle cx="0" cy="0" r="25" fill="none" stroke="#3B82F6" strokeWidth="1.5" />
              <line x1="-15" y1="-10" x2="-15" y2="10" stroke="#3B82F6" strokeWidth="1.5" />
              <line x1="15" y1="-15" x2="15" y2="15" stroke="#3B82F6" strokeWidth="1.5" />
              <text x="0" y="40" textAnchor="middle" fill="#A3A3A3" fontSize="11" fontFamily="JetBrains Mono">Driver</text>
            </g>

            {/* Wire to Zobel */}
            <line x1="105" y1="100" x2="200" y2="100" stroke="#737373" strokeWidth="1" />

            {/* Zobel resistor */}
            <g transform="translate(220, 70)">
              <rect x="-15" y="-5" width="30" height="10" fill="none" stroke="#F59E0B" strokeWidth="1.5" />
              <line x1="-15" y1="0" x2="-30" y2="0" stroke="#737373" strokeWidth="1" />
              <line x1="15" y1="0" x2="30" y2="0" stroke="#737373" strokeWidth="1" />
              <text x="0" y="-12" textAnchor="middle" fill="#A3A3A3" fontSize="10" fontFamily="JetBrains Mono">R1 6.8\u03A9</text>
            </g>

            {/* Zobel capacitor */}
            <g transform="translate(220, 130)">
              <line x1="-5" y1="-8" x2="-5" y2="8" stroke="#22C55E" strokeWidth="1.5" />
              <line x1="5" y1="-8" x2="5" y2="8" stroke="#22C55E" strokeWidth="1.5" />
              <line x1="-5" y1="0" x2="-30" y2="0" stroke="#737373" strokeWidth="1" />
              <line x1="5" y1="0" x2="30" y2="0" stroke="#737373" strokeWidth="1" />
              <text x="0" y="20" textAnchor="middle" fill="#A3A3A3" fontSize="10" fontFamily="JetBrains Mono">C1 12.5\u00B5F</text>
            </g>

            {/* Vertical wires for Zobel */}
            <line x1="250" y1="70" x2="250" y2="130" stroke="#737373" strokeWidth="1" />
            <line x1="190" y1="70" x2="190" y2="130" stroke="#737373" strokeWidth="1" />
            <line x1="190" y1="100" x2="200" y2="100" stroke="#737373" strokeWidth="1" />

            {/* Wire to notch */}
            <line x1="250" y1="100" x2="350" y2="100" stroke="#737373" strokeWidth="1" />

            {/* Notch filter */}
            <g transform="translate(380, 100)">
              <rect x="-15" y="-5" width="30" height="10" fill="none" stroke="#F59E0B" strokeWidth="1.5" />
              <text x="0" y="-12" textAnchor="middle" fill="#A3A3A3" fontSize="10" fontFamily="JetBrains Mono">R2 0.61\u03A9</text>
            </g>

            {/* Output */}
            <line x1="395" y1="100" x2="500" y2="100" stroke="#737373" strokeWidth="1" />
            <g transform="translate(520, 100)">
              <circle cx="0" cy="0" r="4" fill="#3B82F6" />
              <text x="0" y="20" textAnchor="middle" fill="#A3A3A3" fontSize="10" fontFamily="JetBrains Mono">OUT</text>
            </g>

            {/* Ground */}
            <line x1="300" y1="200" x2="300" y2="230" stroke="#737373" strokeWidth="1" />
            <line x1="285" y1="230" x2="315" y2="230" stroke="#737373" strokeWidth="1.5" />
            <line x1="290" y1="235" x2="310" y2="235" stroke="#737373" strokeWidth="1.5" />
            <line x1="295" y1="240" x2="305" y2="240" stroke="#737373" strokeWidth="1.5" />
          </svg>
        </div>
      </div>

      {/* Zoom indicator */}
      <div className="absolute bottom-3 left-3 text-[10px] text-text-muted font-mono">
        {Math.round(zoom * 100)}%
      </div>
    </div>
  );
}
