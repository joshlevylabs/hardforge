"use client";

import { ExternalLink, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { EnrichedBOMEntry, EnrichedBOMResponse } from "@/types";
import { cn } from "@/lib/utils";

interface BOMTableProps {
  bom: EnrichedBOMResponse | null;
}

function formatPrice(price: number | undefined | null): string {
  if (price == null) return "-";
  return `$${price.toFixed(2)}`;
}

function formatStock(stock: number): string {
  if (stock >= 10000) return `${Math.floor(stock / 1000)}k+`;
  return stock.toLocaleString();
}

function PriceBreakTooltip({ entry }: { entry: EnrichedBOMEntry }) {
  const bestOption = entry.distributor_options.reduce<
    (typeof entry.distributor_options)[0] | null
  >((best, opt) => {
    if (!best || opt.unit_price < best.unit_price) return opt;
    return best;
  }, null);

  if (!bestOption || bestOption.price_breaks.length <= 1) return null;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="cursor-help border-b border-dotted border-text-muted">
            {formatPrice(entry.best_price)}
          </span>
        </TooltipTrigger>
        <TooltipContent>
          <div className="text-xs space-y-1">
            <p className="font-semibold mb-1">
              {bestOption.distributor} price breaks
            </p>
            {bestOption.price_breaks.map((pb, i) => (
              <div key={i} className="flex justify-between gap-4">
                <span>{pb.quantity}+</span>
                <span className="font-mono">${pb.unit_price.toFixed(4)}</span>
              </div>
            ))}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export function BOMTable({ bom }: BOMTableProps) {
  if (!bom) {
    return (
      <div className="flex h-full items-center justify-center text-text-muted">
        <p className="text-sm">Generate a design to see the Bill of Materials.</p>
      </div>
    );
  }

  const isEnriched = bom.enrichment_status !== "unavailable";

  return (
    <div className="space-y-4">
      {/* Status banner */}
      {bom.enrichment_status === "unavailable" && (
        <div className="flex items-start gap-2 rounded-lg border border-border bg-surface p-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
          <p className="text-xs text-text-secondary">
            Prices are estimates. Connect Nexar API for real-time distributor
            pricing and availability.
          </p>
        </div>
      )}
      {bom.enrichment_status === "partial" && (
        <div className="flex items-start gap-2 rounded-lg border border-border bg-surface p-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-text-muted" />
          <p className="text-xs text-text-secondary">
            Some components could not be matched to distributor parts. Prices
            shown are estimates for unmatched items.
          </p>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border bg-surface">
              <th className="px-3 py-2 text-left font-semibold text-text-secondary">
                Ref
              </th>
              <th className="px-3 py-2 text-left font-semibold text-text-secondary">
                Value
              </th>
              {isEnriched && (
                <th className="px-3 py-2 text-left font-semibold text-text-secondary">
                  MPN
                </th>
              )}
              <th className="px-3 py-2 text-right font-semibold text-text-secondary">
                {isEnriched ? "Best Price" : "Est. Price"}
              </th>
              {isEnriched && (
                <>
                  <th className="px-3 py-2 text-right font-semibold text-text-secondary">
                    Stock
                  </th>
                  <th className="px-3 py-2 text-left font-semibold text-text-secondary">
                    Distributors
                  </th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {bom.entries.map((entry, i) => {
              const hasDistData = entry.distributor_options.length > 0;

              return (
                <tr
                  key={entry.ref}
                  className={cn(
                    "border-b border-border last:border-0",
                    i % 2 === 0 ? "bg-surface-overlay/50" : ""
                  )}
                >
                  <td className="px-3 py-2 font-mono text-text-primary">
                    {entry.ref}
                  </td>
                  <td className="px-3 py-2 text-text-primary">
                    <div>{entry.value}</div>
                    <div className="text-[10px] text-text-muted">
                      {entry.description}
                    </div>
                  </td>
                  {isEnriched && (
                    <td className="px-3 py-2 font-mono text-text-secondary">
                      {entry.mpn || (
                        <span className="text-text-muted italic">-</span>
                      )}
                    </td>
                  )}
                  <td className="px-3 py-2 text-right font-mono text-text-primary">
                    {hasDistData ? (
                      <PriceBreakTooltip entry={entry} />
                    ) : (
                      <span
                        className={cn(!isEnriched && "text-text-secondary")}
                      >
                        {formatPrice(entry.estimated_price)}
                      </span>
                    )}
                  </td>
                  {isEnriched && (
                    <>
                      <td className="px-3 py-2 text-right font-mono text-text-secondary">
                        {hasDistData
                          ? formatStock(
                              Math.max(
                                ...entry.distributor_options.map((o) => o.stock)
                              )
                            )
                          : "-"}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          {entry.distributor_options.slice(0, 3).map((opt) => (
                            <a
                              key={`${opt.distributor}-${opt.sku}`}
                              href={opt.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 rounded border border-border bg-surface px-1.5 py-0.5 text-[10px] text-accent hover:bg-surface-overlay transition-colors"
                            >
                              {opt.distributor}
                              <ExternalLink className="h-2.5 w-2.5" />
                            </a>
                          ))}
                          {entry.distributor_options.length === 0 && (
                            <span className="text-[10px] text-text-muted italic">
                              No matches
                            </span>
                          )}
                        </div>
                      </td>
                    </>
                  )}
                </tr>
              );
            })}
          </tbody>
          {/* Totals row */}
          <tfoot>
            <tr className="bg-surface border-t border-border font-semibold">
              <td
                className="px-3 py-2 text-text-primary"
                colSpan={isEnriched ? 3 : 2}
              >
                Total ({bom.entries.length} components)
              </td>
              <td className="px-3 py-2 text-right font-mono text-text-primary">
                {isEnriched && bom.total_best_price != null
                  ? formatPrice(bom.total_best_price)
                  : formatPrice(bom.total_cost)}
              </td>
              {isEnriched && (
                <>
                  <td />
                  <td className="px-3 py-2">
                    <Badge
                      variant={
                        bom.enrichment_status === "full"
                          ? "success"
                          : bom.enrichment_status === "partial"
                            ? "warning"
                            : "outline"
                      }
                      className="text-[10px]"
                    >
                      {bom.enrichment_status === "full"
                        ? "Live pricing"
                        : bom.enrichment_status === "partial"
                          ? "Partial pricing"
                          : "Estimated"}
                    </Badge>
                  </td>
                </>
              )}
            </tr>
            {isEnriched &&
              bom.total_best_price != null &&
              bom.total_cost != null && (
                <tr className="bg-surface">
                  <td
                    className="px-3 py-1.5 text-[10px] text-text-muted"
                    colSpan={isEnriched ? 6 : 3}
                  >
                    Estimated total: {formatPrice(bom.total_cost)} | Distributor
                    best: {formatPrice(bom.total_best_price)}
                  </td>
                </tr>
              )}
          </tfoot>
        </table>
      </div>
    </div>
  );
}
