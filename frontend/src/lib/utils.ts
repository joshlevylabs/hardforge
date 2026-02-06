import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatFrequency(hz: number): string {
  if (hz >= 1000) return `${(hz / 1000).toFixed(1)}kHz`;
  return `${hz.toFixed(0)}Hz`;
}

export function formatImpedance(ohms: number): string {
  return `${ohms.toFixed(1)}\u03A9`;
}

export function formatComponentValue(value: number, unit: string): string {
  if (unit === "F" || unit === "H") {
    if (value >= 1) return `${value.toFixed(2)}${unit}`;
    if (value >= 1e-3) return `${(value * 1e3).toFixed(2)}m${unit}`;
    if (value >= 1e-6) return `${(value * 1e6).toFixed(2)}\u00B5${unit}`;
    if (value >= 1e-9) return `${(value * 1e9).toFixed(2)}n${unit}`;
    return `${(value * 1e12).toFixed(2)}p${unit}`;
  }
  if (unit === "\u03A9" || unit === "ohm") {
    if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M\u03A9`;
    if (value >= 1e3) return `${(value / 1e3).toFixed(2)}k\u03A9`;
    return `${value.toFixed(2)}\u03A9`;
  }
  return `${value}${unit}`;
}
