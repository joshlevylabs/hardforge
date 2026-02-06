"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  MessageSquare,
  Search,
  Cpu,
  FileOutput,
  ArrowRight,
  Check,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const pipelineSteps = [
  {
    icon: MessageSquare,
    title: "Describe Intent",
    description: "Tell us what you're building in plain English",
  },
  {
    icon: Search,
    title: "Feasibility Check",
    description: "AI validates physics and component availability",
  },
  {
    icon: Cpu,
    title: "Circuit Design",
    description: "Deterministic engine calculates exact component values",
  },
  {
    icon: FileOutput,
    title: "Export",
    description: "Production-ready schematics, BOM, and Gerber files",
  },
];

const pricingPlans = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Impedance calculator and basic designs",
    features: [
      "Impedance calculator (unlimited)",
      "3 designs per month",
      "SVG schematic export",
      "Community driver library",
    ],
    cta: "Get Started",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$14.99",
    period: "/month",
    description: "Full design pipeline for serious builders",
    features: [
      "Everything in Free",
      "Unlimited designs",
      "KiCad project export",
      "Gerber file generation",
      "SPICE simulation",
      "Priority AI processing",
    ],
    cta: "Start Pro Trial",
    highlighted: true,
  },
  {
    name: "Team",
    price: "$49.99",
    period: "/month",
    description: "Collaborate on hardware designs",
    features: [
      "Everything in Pro",
      "5 team members",
      "Shared project library",
      "Custom driver database",
      "API access",
      "Priority support",
    ],
    cta: "Contact Sales",
    highlighted: false,
  },
];

export default function LandingPage() {
  const [prompt, setPrompt] = useState("");
  const router = useRouter();

  const handleTryExample = () => {
    setPrompt("Admittance shaper for Dayton RS180-8");
  };

  const handleSubmit = () => {
    if (prompt.trim()) {
      router.push(`/design/new?prompt=${encodeURIComponent(prompt)}`);
    }
  };

  return (
    <main className="flex flex-col">
      {/* Hero */}
      <section className="relative flex flex-col items-center px-4 pt-24 pb-20 sm:pt-32 sm:pb-28">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute left-1/2 top-0 -translate-x-1/2 h-[500px] w-[800px] rounded-full bg-accent/5 blur-3xl" />
        </div>
        <div className="relative z-10 flex max-w-3xl flex-col items-center text-center">
          <Badge variant="outline" className="mb-6">
            Now in public beta
          </Badge>
          <h1 className="text-4xl font-bold tracking-tight text-text-primary sm:text-5xl lg:text-6xl">
            Describe your hardware.
            <br />
            <span className="text-accent">We&apos;ll design it.</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg text-text-secondary">
            From natural language to production-ready schematics. HardForge
            combines AI reasoning with deterministic circuit simulation to
            design analog hardware you can trust.
          </p>

          {/* Input area */}
          <div className="mt-10 w-full max-w-2xl">
            <div className="rounded-lg border border-border bg-surface-raised p-1 focus-within:border-accent focus-within:ring-1 focus-within:ring-accent transition-all">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe what you want to build..."
                className="w-full resize-none rounded-md bg-transparent px-4 py-3 text-text-primary placeholder:text-text-muted focus:outline-none min-h-[80px]"
                rows={3}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && e.metaKey) handleSubmit();
                }}
              />
              <div className="flex items-center justify-between px-3 pb-2">
                <button
                  onClick={handleTryExample}
                  className="text-xs text-text-muted hover:text-accent transition-colors cursor-pointer"
                >
                  Try: &quot;Admittance shaper for Dayton RS180-8&quot;
                </button>
                <Button size="sm" onClick={handleSubmit} disabled={!prompt.trim()}>
                  Design
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <p className="mt-2 text-xs text-text-muted text-center">
              Press {"\u2318"}+Enter to submit
            </p>
          </div>
        </div>
      </section>

      {/* Pipeline visualization */}
      <section className="border-t border-border bg-surface px-4 py-20">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center text-2xl font-semibold text-text-primary mb-12">
            From idea to fabrication in minutes
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {pipelineSteps.map((step, i) => (
              <div key={step.title} className="relative flex flex-col items-center text-center">
                {i < pipelineSteps.length - 1 && (
                  <ArrowRight className="absolute -right-4 top-8 hidden h-5 w-5 text-text-muted lg:block" />
                )}
                <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-lg border border-border bg-surface-raised">
                  <step.icon className="h-7 w-7 text-accent" />
                </div>
                <h3 className="text-sm font-semibold text-text-primary">
                  {step.title}
                </h3>
                <p className="mt-1 text-xs text-text-muted max-w-[200px]">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Free tool callout */}
      <section className="border-t border-border px-4 py-20">
        <div className="mx-auto max-w-3xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full bg-accent/10 px-4 py-1.5 text-sm text-accent mb-6">
            <Zap className="h-4 w-4" />
            Free tool — no signup required
          </div>
          <h2 className="text-2xl font-semibold text-text-primary mb-4">
            Impedance Correction Calculator
          </h2>
          <p className="text-text-secondary mb-8">
            Enter your driver&apos;s Thiele-Small parameters and instantly see
            the impedance curve with calculated Zobel and notch filter
            correction networks.
          </p>
          <Button
            size="lg"
            onClick={() => router.push("/tools/impedance")}
          >
            Open Impedance Tool
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </section>

      {/* Pricing */}
      <section className="border-t border-border bg-surface px-4 py-20">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center text-2xl font-semibold text-text-primary mb-4">
            Simple pricing
          </h2>
          <p className="text-center text-text-secondary mb-12">
            Start free. Upgrade when you need production exports.
          </p>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {pricingPlans.map((plan) => (
              <Card
                key={plan.name}
                className={
                  plan.highlighted
                    ? "border-accent ring-1 ring-accent"
                    : ""
                }
              >
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>{plan.name}</CardTitle>
                    {plan.highlighted && (
                      <Badge>Popular</Badge>
                    )}
                  </div>
                  <div className="mt-2">
                    <span className="text-3xl font-bold text-text-primary">
                      {plan.price}
                    </span>
                    <span className="text-sm text-text-muted">
                      {plan.period}
                    </span>
                  </div>
                  <p className="text-sm text-text-secondary mt-1">
                    {plan.description}
                  </p>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {plan.features.map((feature) => (
                      <li
                        key={feature}
                        className="flex items-start gap-2 text-sm text-text-secondary"
                      >
                        <Check className="h-4 w-4 text-accent shrink-0 mt-0.5" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </CardContent>
                <CardFooter>
                  <Button
                    className="w-full"
                    variant={plan.highlighted ? "default" : "outline"}
                  >
                    {plan.cta}
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border px-4 py-8">
        <div className="mx-auto max-w-5xl flex flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-2 text-sm text-text-muted">
            <Zap className="h-4 w-4 text-accent" />
            HardForge
          </div>
          <p className="text-xs text-text-muted">
            Deterministic circuit design. AI-powered reasoning.
          </p>
        </div>
      </footer>
    </main>
  );
}
