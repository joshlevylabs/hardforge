"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { mockDrivers } from "@/lib/mock-data";
import type { DriverType } from "@/types";

const driverTypeLabels: Record<DriverType, string> = {
  woofer: "Woofer",
  midrange: "Midrange",
  tweeter: "Tweeter",
  full_range: "Full Range",
  subwoofer: "Subwoofer",
};

const driverTypeBadgeVariant: Record<DriverType, "default" | "secondary" | "outline" | "success" | "warning"> = {
  woofer: "default",
  midrange: "secondary",
  tweeter: "warning",
  full_range: "success",
  subwoofer: "outline",
};

export default function DriversLibraryPage() {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const router = useRouter();

  const filtered = useMemo(() => {
    return mockDrivers.filter((d) => {
      const matchesSearch =
        !search ||
        d.manufacturer.toLowerCase().includes(search.toLowerCase()) ||
        d.model.toLowerCase().includes(search.toLowerCase());
      const matchesType = typeFilter === "all" || d.driver_type === typeFilter;
      return matchesSearch && matchesType;
    });
  }, [search, typeFilter]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-text-primary">
          Driver Library
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Browse loudspeaker drivers with Thiele-Small parameters
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <Input
            placeholder="Search by manufacturer or model..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-full sm:w-[180px]">
            <SelectValue placeholder="All types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            <SelectItem value="woofer">Woofer</SelectItem>
            <SelectItem value="midrange">Midrange</SelectItem>
            <SelectItem value="tweeter">Tweeter</SelectItem>
            <SelectItem value="full_range">Full Range</SelectItem>
            <SelectItem value="subwoofer">Subwoofer</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Driver grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((driver) => (
          <Card key={driver.id} className="group hover:border-accent/50 transition-colors">
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[10px] text-text-muted uppercase tracking-wider">
                    {driver.manufacturer}
                  </p>
                  <CardTitle className="text-base mt-0.5">
                    {driver.model}
                  </CardTitle>
                </div>
                <Badge variant={driverTypeBadgeVariant[driver.driver_type]}>
                  {driverTypeLabels[driver.driver_type]}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div>
                  <p className="text-[10px] text-text-muted">f<sub>s</sub></p>
                  <p className="text-sm font-mono text-text-primary">
                    {driver.ts_params.fs}Hz
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-text-muted">Q<sub>ts</sub></p>
                  <p className="text-sm font-mono text-text-primary">
                    {driver.ts_params.qts}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-text-muted">R<sub>e</sub></p>
                  <p className="text-sm font-mono text-text-primary">
                    {driver.ts_params.re}\u03A9
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-text-muted">Sensitivity</p>
                  <p className="text-sm font-mono text-text-primary">
                    {driver.sensitivity}dB
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-text-muted">Power</p>
                  <p className="text-sm font-mono text-text-primary">
                    {driver.power_rating}W
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-text-muted">Z<sub>nom</sub></p>
                  <p className="text-sm font-mono text-text-primary">
                    {driver.nominal_impedance}\u03A9
                  </p>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => router.push(`/design/new?driver=${driver.id}`)}
              >
                Use This Driver
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="flex items-center justify-center py-20 text-text-muted">
          <p className="text-sm">No drivers match your search.</p>
        </div>
      )}
    </main>
  );
}
