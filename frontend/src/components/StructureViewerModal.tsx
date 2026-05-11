import React, { useEffect, useMemo, useRef, useState } from "react";
import { Atom, BadgeInfo, Layers3, Zap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { formula_to_xyz, parseFormula } from "@/lib/molecular-viewer";

type StructureCandidate = {
  catalyst_id: string;
  catalyst_name?: string;
  composition: string;
  source: string;
  activity?: number;
  selectivity?: number;
  stability?: number;
  combined_score?: number;
  uncertainty?: number;
  rank?: number;
  explanation?: string;
  insights?: string[];
  structure_data?: Record<string, unknown> | null;
};

type StructureViewerModalProps = {
  candidate: StructureCandidate | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

declare global {
  interface Window {
    $3Dmol?: {
      createViewer: (
        element: HTMLDivElement,
        options: { backgroundColor: string },
      ) => {
        addModel: (data: string, format: string) => void;
        setStyle: (selection: Record<string, unknown>, style: Record<string, unknown>) => void;
        zoomTo: () => void;
        render: () => void;
      };
    };
  }
}

function resolveProteinAccession(candidate: StructureCandidate | null): string | undefined {
  const structureData = candidate?.structure_data;
  const possibleKeys = [
    "uniprot_accession",
    "uniprot_id",
    "protein_accession",
    "alphafold_accession",
  ];

  for (const key of possibleKeys) {
    const value = structureData?.[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }

  return undefined;
}

export function StructureViewerModal({ candidate, open, onOpenChange }: StructureViewerModalProps) {
  const catalystViewerRef = useRef<HTMLDivElement | null>(null);
  const [activeTab, setActiveTab] = useState<"catalyst" | "protein">("catalyst");

  const proteinAccession = useMemo(() => resolveProteinAccession(candidate), [candidate]);

  useEffect(() => {
    if (open) {
      setActiveTab("catalyst");
    }
  }, [candidate?.catalyst_id, open]);

  useEffect(() => {
    if (!open || activeTab !== "catalyst" || !candidate) {
      return;
    }

    const element = catalystViewerRef.current;
    if (!element) {
      return;
    }

    const viewerApi = window.$3Dmol;
    const xyz = formula_to_xyz(candidate.composition, 24);

    element.innerHTML = "";

    if (!viewerApi) {
      element.innerHTML =
        "<div class='flex h-full items-center justify-center text-sm text-muted-foreground'>3Dmol.js is loading...</div>";
      return;
    }

    const viewer = viewerApi.createViewer(element, {
      backgroundColor: "white",
    });

    viewer.addModel(xyz, "xyz");
    viewer.setStyle(
      {},
      {
        stick: { radius: 0.16, colorscheme: "Jmol" },
        sphere: { scale: 0.28 },
      },
    );
    viewer.zoomTo();
    viewer.render();

    return () => {
      element.innerHTML = "";
    };
  }, [activeTab, candidate, open]);

  const atomBreakdown = useMemo(() => {
    const counts = parseFormula(candidate?.composition || "");
    return Object.entries(counts)
      .map(([element, count]) => `${element}${count}`)
      .join(" · ");
  }, [candidate?.composition]);

  const proteinViewer = proteinAccession
    ? React.createElement("pdbe-molstar", {
        key: proteinAccession,
        style: { display: "block", width: "100%", height: "100%", minHeight: "28rem" },
        "molecule-id": proteinAccession,
        "default-preset": "default",
        "alphafold-view": "true",
        "hide-controls": "false",
        "loading-overlay": "true",
        "sequence-panel": "true",
        expanded: "false",
        landscape: "false",
        "subscribe-events": "false",
        "bg-color-r": "255",
        "bg-color-g": "255",
        "bg-color-b": "255",
      })
    : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl p-0 overflow-hidden border-border/70 bg-background shadow-2xl sm:max-h-[92vh]">
        <div className="flex h-[92vh] flex-col">
          <div className="border-b border-border/70 bg-card/50 px-6 py-5">
            <DialogHeader className="text-left">
              <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono uppercase tracking-[0.28em] text-primary">
                <Layers3 className="h-3.5 w-3.5" /> Structure viewer
              </div>
              <DialogTitle className="font-display text-2xl">
                {candidate?.composition || "Unknown structure"}
              </DialogTitle>
              <DialogDescription className="max-w-3xl">
                {candidate?.catalyst_name || candidate?.catalyst_id || "Selected candidate"} is
                rendered as a rough catalyst geometry, with AlphaFold protein context available when
                a UniProt accession is attached.
              </DialogDescription>
            </DialogHeader>

            <div className="mt-4 flex flex-wrap gap-2">
              <Badge
                variant="secondary"
                className="gap-1.5 font-mono text-[10px] uppercase tracking-wider"
              >
                <Zap className="h-3 w-3" /> {candidate?.source || "unknown"}
              </Badge>
              <Badge
                variant="outline"
                className="gap-1.5 font-mono text-[10px] uppercase tracking-wider"
              >
                <Atom className="h-3 w-3" /> {atomBreakdown || "Stoichiometry unavailable"}
              </Badge>
              {proteinAccession && (
                <Badge
                  variant="outline"
                  className="gap-1.5 font-mono text-[10px] uppercase tracking-wider"
                >
                  <BadgeInfo className="h-3 w-3" /> UniProt {proteinAccession}
                </Badge>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-hidden px-6 py-5">
            <Tabs
              value={activeTab}
              onValueChange={(value) => setActiveTab(value as "catalyst" | "protein")}
              className="flex h-full flex-col"
            >
              <div className="mb-4 flex items-center justify-between gap-3">
                <TabsList>
                  <TabsTrigger value="catalyst">Catalyst</TabsTrigger>
                  <TabsTrigger value="protein" disabled={!proteinAccession}>
                    Protein
                  </TabsTrigger>
                </TabsList>
                <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  3Dmol.js · PDBe Mol*
                </div>
              </div>

              <TabsContent
                value="catalyst"
                className="mt-0 flex-1 data-[state=active]:flex data-[state=active]:flex-col"
              >
                <div className="grid flex-1 gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(320px,0.8fr)]">
                  <div className="flex min-h-[26rem] flex-col overflow-hidden rounded-2xl border border-border/70 bg-[linear-gradient(135deg,rgba(16,23,38,0.94),rgba(34,42,61,0.85))] shadow-inner">
                    <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
                      <div>
                        <div className="font-mono text-[10px] uppercase tracking-widest text-primary/90">
                          Catalyst geometry
                        </div>
                        <div className="text-sm text-white/80">
                          Rough XYZ reconstruction from composition
                        </div>
                      </div>
                      <div className="text-right text-[10px] font-mono uppercase tracking-wider text-white/55">
                        {candidate?.rank ? `Rank ${candidate.rank}` : "Discovery candidate"}
                      </div>
                    </div>
                    <div ref={catalystViewerRef} className="min-h-0 flex-1" />
                  </div>

                  <div className="space-y-4">
                    <div className={cn("rounded-2xl border border-border/70 bg-card/70 p-4")}>
                      <div className="font-mono text-[10px] uppercase tracking-widest text-primary">
                        Candidate metrics
                      </div>
                      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                        <Metric label="Selectivity" value={candidate?.selectivity} />
                        <Metric label="Activity" value={candidate?.activity} />
                        <Metric label="Stability" value={candidate?.stability} />
                        <Metric
                          label="Score"
                          value={
                            candidate?.combined_score ? candidate.combined_score * 100 : undefined
                          }
                        />
                      </div>
                    </div>

                    <div className="rounded-2xl border border-border/70 bg-card/70 p-4">
                      <div className="font-mono text-[10px] uppercase tracking-widest text-primary">
                        Mechanistic notes
                      </div>
                      <div className="mt-3 space-y-2 text-sm text-muted-foreground">
                        <p>
                          {candidate?.explanation ||
                            "The structure panel highlights the selected catalyst geometry and the prediction context used for ranking."}
                        </p>
                        {candidate?.insights?.length ? (
                          <ul className="space-y-2">
                            {candidate.insights.slice(0, 3).map((insight, index) => (
                              <li
                                key={index}
                                className="rounded-lg border border-border/60 bg-background/60 px-3 py-2 text-foreground/90"
                              >
                                {insight}
                              </li>
                            ))}
                          </ul>
                        ) : null}
                      </div>
                    </div>
                  </div>
                </div>
              </TabsContent>

              <TabsContent
                value="protein"
                className="mt-0 flex-1 data-[state=active]:flex data-[state=active]:flex-col"
              >
                <div className="flex-1 overflow-hidden rounded-2xl border border-border/70 bg-background">
                  {proteinAccession ? (
                    proteinViewer
                  ) : (
                    <div className="flex h-full min-h-[26rem] items-center justify-center rounded-2xl border border-dashed border-border/70 bg-card/50 px-6 text-center text-sm text-muted-foreground">
                      No UniProt accession is attached to this candidate yet. When the backend
                      provides a protein accession in structure metadata, the AlphaFold viewer will
                      load here.
                    </div>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Metric({ label, value }: { label: string; value?: number }) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/60 px-3 py-2">
      <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 font-display text-lg text-foreground">
        {typeof value === "number" && Number.isFinite(value) ? Math.round(value) : "—"}
        {typeof value === "number" && Number.isFinite(value) ? (
          <span className="ml-1 text-[10px] font-mono text-muted-foreground">%</span>
        ) : null}
      </div>
    </div>
  );
}
