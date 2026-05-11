import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Atom, FlaskConical, Database, Sparkles, BarChart3, RefreshCw,
  Send, Beaker, Activity, AlertTriangle, CheckCircle2, Layers,
  ChevronRight, Search, Settings, Home, BookOpen, Cpu, Zap, Bot, User,
  FileText, ArrowRight, Clock, Target, PlayCircle, ShieldCheck, Loader2,
  ScatterChart, Info
} from "lucide-react";
import { 
  createReaction, 
  listReactions, 
  retrieveCatalysts, 
  rankCatalysts,
  fetchExperimentSummary,
  fetchRetrainingHistory,
  triggerRetraining
} from "../lib/api";
import {
  ActivitySelectivityScatter,
  StabilityComparisonChart,
  ConfidenceScoreVisualization,
  CandidateRankingHeatmap,
} from "../components/ScientificCharts";
import { 
  StatSkeleton, 
  TableRowSkeleton, 
  ChartSkeleton, 
  EmptyState, 
  ErrorState, 
  PageTransition 
} from "../components/UXStates";
import { Menu, X } from "lucide-react";
import { cn } from "../lib/utils";

export const Route = createFileRoute("/workspace")({
  component: Workspace,
});

const navItems = [
  { icon: Home, label: "Overview" },
  { icon: Sparkles, label: "Discovery" },
  { icon: Atom, label: "Candidates" },
  { icon: BarChart3, label: "Predictions" },
  { icon: ScatterChart, label: "Visualizations" },
  { icon: FlaskConical, label: "Experiments" },
  { icon: RefreshCw, label: "Feedback Loop" },
  { icon: Database, label: "Knowledge Base" },
  { icon: BookOpen, label: "Protocols" },
];


function Stat({ label, value, suffix }: { label: string; value: number | string; suffix?: string }) {
  return (
    <div className="rounded border border-border/60 bg-background/40 py-1.5 px-3 text-center">
      <div className="font-display text-base">{value}{suffix ? <span className="text-[10px] text-muted-foreground ml-0.5">{suffix}</span> : ""}</div>
      <div className="font-mono text-[9px] text-muted-foreground">{label}</div>
    </div>
  );
}

function Molecule3D() {
  return (
    <svg viewBox="0 0 320 280" className="w-full h-full">
      <defs>
        <radialGradient id="atomP" cx="0.3" cy="0.3">
          <stop offset="0" stopColor="oklch(0.92 0.18 165)" />
          <stop offset="1" stopColor="oklch(0.45 0.18 165)" />
        </radialGradient>
        <radialGradient id="atomA" cx="0.3" cy="0.3">
          <stop offset="0" stopColor="oklch(0.92 0.13 200)" />
          <stop offset="1" stopColor="oklch(0.40 0.13 200)" />
        </radialGradient>
        <radialGradient id="atomW" cx="0.3" cy="0.3">
          <stop offset="0" stopColor="oklch(0.95 0.15 75)" />
          <stop offset="1" stopColor="oklch(0.50 0.15 75)" />
        </radialGradient>
      </defs>
      <g className="animate-orbit-slow" style={{ transformOrigin: "160px 140px" }}>
        <g stroke="oklch(0.78 0.18 165 / 0.5)" strokeWidth="2">
          <line x1="160" y1="140" x2="80" y2="80" />
          <line x1="160" y1="140" x2="240" y2="80" />
          <line x1="160" y1="140" x2="80" y2="200" />
          <line x1="160" y1="140" x2="240" y2="200" />
          <line x1="160" y1="140" x2="160" y2="40" />
          <line x1="160" y1="140" x2="160" y2="240" />
        </g>
        <circle cx="160" cy="140" r="22" fill="url(#atomP)" />
        <circle cx="80" cy="80" r="14" fill="url(#atomA)" />
        <circle cx="240" cy="80" r="14" fill="url(#atomA)" />
        <circle cx="80" cy="200" r="14" fill="url(#atomW)" />
        <circle cx="240" cy="200" r="14" fill="url(#atomW)" />
        <circle cx="160" cy="40" r="11" fill="url(#atomA)" />
        <circle cx="160" cy="240" r="11" fill="url(#atomW)" />
      </g>
      <ellipse cx="160" cy="140" rx="110" ry="40" fill="none" stroke="oklch(0.78 0.18 165 / 0.2)" strokeDasharray="3 6" />
      <ellipse cx="160" cy="140" rx="40" ry="110" fill="none" stroke="oklch(0.82 0.13 200 / 0.2)" strokeDasharray="3 6" />
    </svg>
  );
}

function Sparkline() {
  const pts = [82, 78, 74, 71, 68, 64, 60, 57, 54, 52, 49, 47, 45, 43];
  const max = Math.max(...pts), min = Math.min(...pts);
  const w = 280, h = 50;
  const path = pts.map((p, i) => {
    const x = (i / (pts.length - 1)) * w;
    const y = h - ((p - min) / (max - min)) * h;
    return `${i === 0 ? "M" : "L"}${x},${y}`;
  }).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h + 10}`} className="w-full h-14">
      <path d={`${path} L${w},${h} L0,${h} Z`} fill="oklch(0.78 0.18 165 / 0.15)" />
      <path d={path} fill="none" stroke="oklch(0.78 0.18 165)" strokeWidth="1.5" />
      {pts.map((p, i) => {
        const x = (i / (pts.length - 1)) * w;
        const y = h - ((p - min) / (max - min)) * h;
        return <circle key={i} cx={x} cy={y} r="1.5" fill="oklch(0.78 0.18 165)" />;
      })}
    </svg>
  );
}

function OverviewView({ stats, projects, isLoading }: { stats: any, projects: any[], isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="h-12 w-64 bg-secondary/40 rounded animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatSkeleton />
          <StatSkeleton />
          <StatSkeleton />
          <StatSkeleton />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-64 bg-card/40 rounded-xl animate-pulse" />
          <div className="h-64 bg-card/40 rounded-xl animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <PageTransition className="p-6 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h1 className="text-2xl font-display">Welcome back, Dr. Sharma</h1>
          <p className="text-muted-foreground text-sm mt-1">Here's the status of your catalyst discovery pipeline.</p>
        </div>
        <button className="w-full sm:w-auto bg-primary text-primary-foreground px-4 py-2 rounded-md font-mono text-xs uppercase flex items-center justify-center gap-2 hover:opacity-90 transition-opacity">
          <Zap className="h-4 w-4" /> New Project
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Active Projects", val: projects?.length ?? 0, icon: Target, col: "text-primary" },
          { label: "Experiments Logged", val: stats?.total_experiments ?? 0, icon: FlaskConical, col: "text-amber-500" },
          { label: "Model Retrainings", val: stats?.model_retrainings ?? 0, icon: RefreshCw, col: "text-accent" },
          { label: "Anomalies Detected", val: stats?.experiments_by_status?.anomaly ?? 0, icon: AlertTriangle, col: "text-red-500" },
        ].map(s => (
          <div key={s.label} className="bg-card/60 border border-border p-5 rounded-xl hover:border-primary/30 transition-colors">
            <div className={`mb-3 ${s.col}`}><s.icon className="h-6 w-6" /></div>
            <div className="font-display text-3xl mb-1">{s.val}</div>
            <div className="font-mono text-[10px] uppercase text-muted-foreground">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card/60 border border-border p-5 rounded-xl">
          <h2 className="font-mono text-xs uppercase tracking-widest text-primary mb-4">Recent Activity</h2>
          <div className="space-y-4">
            {[
              { text: "Model retraining history updated from DB.", time: "Live", icon: RefreshCw },
              { text: "Real-time discovery pipeline active.", time: "Now", icon: Sparkles },
              { text: "Experimental feedback loop initialized.", time: "Live", icon: Layers },
            ].map((a, i) => (
              <div key={i} className="flex gap-3 text-sm">
                <a.icon className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="text-foreground">{a.text}</div>
                  <div className="text-muted-foreground text-xs">{a.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-card/60 border border-border p-5 rounded-xl">
          <h2 className="font-mono text-xs uppercase tracking-widest text-primary mb-4">Active Projects Status</h2>
          <div className="space-y-4">
            {projects?.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-muted-foreground text-sm">No active projects.</p>
              </div>
            ) : (
              projects?.slice(0, 3).map((p: any) => (
                <div key={p.id} className="flex items-center justify-between p-3 rounded bg-background/40 border border-border/50 hover:border-primary/20 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className={`h-2 w-2 rounded-full bg-primary`} />
                    <span className="font-medium truncate max-w-[150px]">{p.name}</span>
                  </div>
                  <span className="font-mono text-[10px] text-muted-foreground">{p.solvent}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </PageTransition>
  );
}


function CandidatesView({ candidates, catalystSource, catalystCount, isLoading, error, onRetry }: { candidates: any[], catalystSource?: string, catalystCount?: number, isLoading: boolean, error?: any, onRetry?: () => void }) {
  if (error) return <ErrorState error={error} onRetry={onRetry} />;

  const handleExportCSV = () => {
    if (!candidates.length) return;
    const headers = ['catalyst_id', 'composition', 'activity', 'selectivity', 'stability', 'combined_score', 'uncertainty', 'source', 'rank'];
    const rows = candidates.map((c: any) =>
      headers.map(h => {
        const v = c[h];
        return typeof v === 'number' ? v.toFixed(3) : (v ?? '');
      }).join(',')
    );
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `catalyst_candidates_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <PageTransition className="p-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-display">Candidate Pool</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {catalystSource && catalystCount ? (
              <>Retrieved {catalystCount} catalysts from <span className="text-primary font-semibold">{catalystSource}</span></>
            ) : (
              <>Explore all generated and retrieved candidates for the current project.</>
            )}
          </p>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <button className="flex-1 sm:flex-none px-3 py-1.5 border border-border bg-card rounded text-sm flex items-center justify-center gap-2 hover:bg-secondary transition-colors">
            <Search className="h-4 w-4" /> Filter
          </button>
          <button
            onClick={handleExportCSV}
            disabled={!candidates.length}
            className="flex-1 sm:flex-none px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Export CSV
          </button>
        </div>
      </div>

      <div className="border border-border rounded-xl bg-card/60 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-background/80 font-mono text-[10px] uppercase text-muted-foreground border-b border-border">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Composition</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3">Selectivity</th>
                <th className="px-4 py-3">Activity</th>
                <th className="px-4 py-3">Source</th>
                <th className="px-4 py-3">AI Verdict</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {isLoading ? (
                Array(6).fill(0).map((_, i) => (
                  <TableRowSkeleton key={i} cols={7} />
                ))
              ) : candidates.length === 0 ? (
                <tr>
                  <td colSpan={7}>
                    <EmptyState 
                      icon={Sparkles}
                      title="No candidates surfaced"
                      description="Initialize a discovery cycle or adjust your search parameters to generate potential catalyst candidates."
                    />
                  </td>
                </tr>
              ) : candidates.map((c) => (
                <tr key={c.catalyst_id} className="hover:bg-secondary/40 transition-colors group">
                  <td className="px-4 py-3 font-mono text-xs">{c.catalyst_id.slice(0, 8)}</td>
                  <td className="px-4 py-3 font-medium group-hover:text-primary transition-colors">{c.composition}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 rounded bg-secondary overflow-hidden">
                        <div className="h-full bg-primary" style={{ width: `${c.combined_score * 100}%` }} />
                      </div>
                      <span className="font-mono text-xs">{c.combined_score.toFixed(2)}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{Math.round(c.selectivity)}%</td>
                  <td className="px-4 py-3 font-mono text-xs">{Math.round(c.activity)}%</td>
                  <td className="px-4 py-3">
                    {c.source === "generated" ? 
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-accent/20 text-accent border border-accent/40">NOVEL</span> :
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-muted text-muted-foreground border border-border">KNOWN</span>
                    }
                  </td>
                  <td className="px-4 py-3 text-[11px] italic text-primary/80 truncate max-w-[150px]">{c.explanation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </PageTransition>
  );
}

function PredictionsView({ rankingData, isLoading }: { rankingData: any[], isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="h-10 w-48 bg-secondary/40 rounded animate-pulse" />
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <ChartSkeleton />
          <ChartSkeleton />
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <ChartSkeleton />
          <ChartSkeleton />
        </div>
      </div>
    );
  }

  const avgUncertainty = rankingData.length
    ? rankingData.reduce((acc, c) => acc + c.uncertainty, 0) / rankingData.length
    : 0;
    
  return (
    <PageTransition className="p-6 space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display">Prediction Models</h1>
          <p className="text-muted-foreground text-sm mt-1">GNN &amp; MLIP prediction confidences, uncertainties, and candidate rankings.</p>
        </div>
        <div className="flex gap-3 font-mono text-[10px]">
          <div className="rounded border border-border/60 bg-card/60 px-3 py-2 text-center">
            <div className="text-foreground text-sm font-display">{rankingData.length}</div>
            <div className="text-muted-foreground">Candidates</div>
          </div>
          <div className="rounded border border-border/60 bg-card/60 px-3 py-2 text-center">
            <div className="text-foreground text-sm font-display">±{(avgUncertainty * 100).toFixed(1)}%</div>
            <div className="text-muted-foreground">Avg Uncertainty</div>
          </div>
        </div>
      </div>

      {rankingData.length === 0 ? (
        <EmptyState 
          icon={BarChart3}
          title="No prediction data"
          description="Candidates must be generated before the AI engine can run performance predictions and uncertainty quantification."
        />
      ) : (
        <>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <ActivitySelectivityScatter candidates={rankingData} />
            <StabilityComparisonChart candidates={rankingData} />
          </div>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <ConfidenceScoreVisualization candidates={rankingData} />
            <CandidateRankingHeatmap candidates={rankingData} />
          </div>
        </>
      )}
    </PageTransition>
  );
}

function VisualizationsView({ rankingData, isLoading }: { rankingData: any[], isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="h-10 w-48 bg-secondary/40 rounded animate-pulse" />
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <ChartSkeleton />
          <ChartSkeleton />
        </div>
      </div>
    );
  }

  return (
    <PageTransition className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display">Scientific Visualizations</h1>
          <p className="text-muted-foreground text-sm mt-1">Interactive multi-dimensional analysis of catalyst candidates.</p>
        </div>
        <span className="hidden sm:inline font-mono text-[10px] text-muted-foreground border border-border/50 px-2 py-1 rounded">
          {rankingData.length} candidates · Recharts
        </span>
      </div>

      {rankingData.length === 0 ? (
        <EmptyState 
          icon={Activity}
          title="Visualization data unavailable"
          description="Complete a discovery cycle to populate these interactive visualizations with real-time candidate data."
        />
      ) : (
        <div className="space-y-6">
          {/* Row 1 */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <ActivitySelectivityScatter candidates={rankingData} />
            <StabilityComparisonChart candidates={rankingData} />
          </div>
          {/* Row 2 */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <ConfidenceScoreVisualization candidates={rankingData} />
            <CandidateRankingHeatmap candidates={rankingData} />
          </div>
        </div>
      )}
    </PageTransition>
  );
}

function ExperimentsView({ stats, isLoading }: { stats: any, isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="h-10 w-48 bg-secondary/40 rounded animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-96 bg-card/40 rounded-xl animate-pulse" />
          <div className="h-96 bg-card/40 rounded-xl animate-pulse" />
          <div className="h-96 bg-card/40 rounded-xl animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <PageTransition className="p-6">
      <h1 className="text-2xl font-display mb-1">Experiment Logs</h1>
      <p className="text-muted-foreground text-sm mb-6">Track physical synthesis and testing of selected candidates.</p>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {['Queued', 'In Progress', 'Completed'].map((col, idx) => (
          <div key={col} className="bg-card/40 border border-border rounded-xl p-4 min-h-[400px] sm:min-h-[500px]">
            <h3 className="font-mono text-xs uppercase tracking-widest text-primary mb-4 flex justify-between items-center">
              {col} <span className="bg-secondary px-2 py-0.5 rounded text-foreground">
                {idx === 0 ? 0 : idx === 1 ? 0 : stats?.total_experiments ?? 0}
              </span>
            </h3>
            {idx === 2 && stats?.total_experiments > 0 && (
              <div className="bg-background border border-border rounded-lg p-3 shadow-sm mb-3 animate-fade-in-up">
                <div className="flex justify-between items-start mb-2">
                  <span className="font-mono text-xs text-muted-foreground">EXP-LAST</span>
                  <ShieldCheck className="h-3.5 w-3.5 text-accent" />
                </div>
                <div className="text-sm font-medium mb-1">Recent Experiment</div>
                <div className="text-xs text-muted-foreground">Anomalies: {stats.experiments_by_status.anomaly}</div>
              </div>
            )}
            {idx !== 2 && (
               <div className="flex flex-col items-center justify-center h-48 opacity-20 italic text-xs">
                 No items in {col.toLowerCase()}
               </div>
            )}
          </div>
        ))}
      </div>
    </PageTransition>
  );
}

function FeedbackLoopView({ history, stats, isLoading, onTriggerRetraining, retrainingToast }: {
  history: any[], stats: any, isLoading: boolean,
  onTriggerRetraining: () => void,
  retrainingToast: string | null
}) {
  if (isLoading) return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="h-32 w-full bg-secondary/40 rounded animate-pulse" />
      <div className="h-64 w-full bg-card/40 rounded animate-pulse" />
    </div>
  );

  return (
    <PageTransition className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="text-center mb-8">
        <RefreshCw className="h-12 w-12 text-primary mx-auto mb-4 animate-spin-slow" />
        <h1 className="text-3xl font-display">Closed-Loop Feedback</h1>
        <p className="text-muted-foreground mt-2">Aligning physical experiment outcomes with AI predictions to fine-tune models.</p>
      </div>

      {retrainingToast && (
        <div className="flex items-center gap-3 bg-primary/10 border border-primary/30 text-primary px-4 py-3 rounded-xl animate-fade-in-up">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span className="text-sm">{retrainingToast}</span>
        </div>
      )}

      {stats?.experiments_by_status?.anomaly > 0 && (
        <div className="bg-[oklch(0.82_0.15_75)]/5 border border-[oklch(0.82_0.15_75)]/40 p-6 rounded-xl animate-fade-in-up">
          <div className="flex items-center gap-3 mb-4 text-[oklch(0.82_0.15_75)]">
            <AlertTriangle className="h-5 w-5 animate-pulse" />
            <h2 className="text-lg font-medium">Discrepancy Detected</h2>
          </div>
          <p className="text-sm text-foreground/90 mb-6 leading-relaxed">
            System detected {stats.experiments_by_status.anomaly} anomaly(s) in recent experiments. 
            Automated retraining is recommended to align model with observed experimental data.
          </p>
          <button
            onClick={onTriggerRetraining}
            className="bg-[oklch(0.82_0.15_75)] text-white px-4 py-2 rounded font-mono text-xs uppercase flex items-center gap-2 hover:opacity-90 transition-opacity"
          >
            <Zap className="h-4 w-4" /> Initiate Retraining Cycle
          </button>
        </div>
      )}

      <div className="bg-card/60 border border-border p-6 rounded-xl shadow-sm">
        <h3 className="font-mono text-xs uppercase tracking-widest text-primary mb-4">Retraining History</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="text-muted-foreground border-b border-border font-mono text-[10px] uppercase">
                <th className="pb-3 px-2">Date</th>
                <th className="pb-3 px-2">Model Version</th>
                <th className="pb-3 px-2">Trigger</th>
                <th className="pb-3 px-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {history.length === 0 ? (
                 <tr><td colSpan={4} className="py-12 text-center text-muted-foreground italic">No retraining history yet.</td></tr>
              ) : history.map((h) => (
                <tr key={h.id} className="hover:bg-secondary/20 transition-colors">
                  <td className="py-4 px-2 text-muted-foreground">{new Date(h.created_at).toLocaleDateString()}</td>
                  <td className="py-4 px-2 font-mono text-xs">{h.version}</td>
                  <td className="py-4 px-2">{h.trigger_reason}</td>
                  <td className="py-4 px-2">
                    <span className="inline-flex items-center gap-1.5 text-primary">
                      <span className="h-1.5 w-1.5 rounded-full bg-primary animate-blink" />
                      {h.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </PageTransition>
  );
}



function KnowledgeBaseView() {
  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-display">Knowledge Base</h1>
          <p className="text-muted-foreground text-sm mt-1">Search through 1.2M+ materials, papers, and logged experiments.</p>
        </div>
        <div className="relative w-72">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input placeholder="Search materials or papers..." className="w-full bg-input border border-border rounded-md pl-9 pr-3 py-2 text-sm focus:outline-none focus:border-primary/60" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-card/40 border border-border p-4 rounded-xl flex gap-4">
            <div className="h-12 w-12 rounded bg-secondary/80 flex items-center justify-center shrink-0">
              <Database className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <h4 className="font-medium text-sm mb-1 hover:text-primary cursor-pointer transition-colors">High-throughput screening of Cu-based catalysts</h4>
              <p className="text-xs text-muted-foreground mb-2">ACS Catalysis · 2024 · 42 citations</p>
              <div className="flex gap-2">
                <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-primary/10 text-primary">CO2 Reduction</span>
                <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-secondary text-muted-foreground">Dataset</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProtocolsView() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-display mb-1">Synthesis Protocols</h1>
      <p className="text-muted-foreground text-sm mb-6">AI-generated and lab-verified instructions for catalyst synthesis.</p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[
          { title: "Standard Co-precipitation", target: "Cu/ZnO/Al2O3", verified: true },
          { title: "Sol-gel method", target: "TiO2 supported", verified: true },
          { title: "Incipient Wetness Impregnation", target: "Pd/C", verified: false },
        ].map((p, i) => (
          <div key={i} className="bg-card/60 border border-border rounded-xl p-5 hover:border-primary/40 transition-colors cursor-pointer group">
            <div className="flex justify-between items-start mb-3">
              <FileText className="h-6 w-6 text-muted-foreground group-hover:text-primary transition-colors" />
              {p.verified ? (
                <span className="flex items-center gap-1 text-[10px] font-mono text-primary bg-primary/10 px-2 py-1 rounded">
                  <CheckCircle2 className="h-3 w-3" /> VERIFIED
                </span>
              ) : (
                <span className="flex items-center gap-1 text-[10px] font-mono text-muted-foreground bg-secondary px-2 py-1 rounded">
                  AI DRAFT
                </span>
              )}
            </div>
            <h3 className="font-medium mb-1">{p.title}</h3>
            <p className="text-xs text-muted-foreground mb-4">Target: {p.target}</p>
            <div className="flex items-center text-xs text-primary font-mono group-hover:underline">
              View Protocol <ArrowRight className="h-3 w-3 ml-1" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Workspace() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("Overview");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [reactionInput, setReactionInput] = useState("CO2 + 3H2 -> CH3OH + H2O");
  const [selectedCandidate, setSelectedCandidate] = useState<any>(null);
  const [retrainingToast, setRetrainingToast] = useState<string | null>(null);
  const [chat, setChat] = useState<{ role: "assistant" | "user"; text: string }[]>([
    { role: "assistant", text: "Ready to start discovery cycle. Enter your target reaction to begin." }
  ]);
  const [input, setInput] = useState("");

  // Queries
  const { data: reactionsData, isLoading: loadingReactions, error: errorReactions } = useQuery({
    queryKey: ["reactions"],
    queryFn: () => listReactions(),
  });

  const activeReaction = reactionsData?.reactions?.[0];

  const { data: catalystsData, isLoading: loadingCatalysts, error: errorCatalysts } = useQuery({
    queryKey: ["catalysts", activeReaction?.id],
    queryFn: () => retrieveCatalysts({
      reaction_id: activeReaction!.id,
      reactants: activeReaction!.reactants,
      products: activeReaction!.products,
    }),
    enabled: !!activeReaction,
  });

  // FIX: Use stable primitive (count) in queryKey — avoids infinite re-fetch
  // caused by new array reference on every render
  const { data: rankingData, isLoading: loadingRanking, error: errorRanking } = useQuery({
    queryKey: ["ranking", activeReaction?.id, catalystsData?.count],
    queryFn: () => rankCatalysts({
      catalysts: catalystsData!.catalysts,
      reaction_conditions: {
        temperature: activeReaction!.temperature,
        pressure: activeReaction!.pressure,
        solvent: activeReaction!.solvent,
      },
      reaction_id: activeReaction!.id
    }),
    enabled: !!activeReaction && !!catalystsData?.catalysts?.length,
  });

  const { data: experimentSummary, isLoading: loadingExperiments } = useQuery({
    queryKey: ["experimentSummary", activeReaction?.id],
    queryFn: () => fetchExperimentSummary(activeReaction?.id),
    enabled: !!activeReaction,
  });

  const { data: retrainingHistory, isLoading: loadingHistory } = useQuery({
    queryKey: ["retrainingHistory"],
    queryFn: () => fetchRetrainingHistory(),
  });

  // Mutations
  const discoveryMutation = useMutation({
    mutationFn: async (inputStr: string) => {
      // Very basic parsing for demo
      const [reactantsPart, productsPart] = inputStr.split("->");
      const reactants = reactantsPart.split("+").map(s => s.trim());
      const products = productsPart.split("+").map(s => s.trim());
      
      const reaction = await createReaction({
        name: inputStr,
        reactants,
        products,
        temperature: 250,
        pressure: 50,
        solvent: "water"
      });
      
      return reaction;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reactions"] });
      setChat(prev => [...prev, 
        { role: "assistant", text: "New reaction created. Discovery pipeline initiated. Retrieving known catalysts and generating novel variants..." }
      ]);
    },
  });

  const retrainingMutation = useMutation({
    mutationFn: () => triggerRetraining([], "manual_trigger"),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["retrainingHistory"] });
      const version = data?.retraining_job?.version ?? "new";
      setRetrainingToast(`Retraining job queued successfully — model ${version} scheduled.`);
      setTimeout(() => setRetrainingToast(null), 6000);
    },
    onError: () => {
      setRetrainingToast("Failed to queue retraining. Check backend connection.");
      setTimeout(() => setRetrainingToast(null), 5000);
    }
  });

  useEffect(() => {
    if (rankingData && rankingData.length > 0 && !selectedCandidate) {
      setSelectedCandidate(rankingData[0]);
    }
  }, [rankingData]);

  const send = () => {
    if (!input.trim()) return;
    setChat([...chat, { role: "user", text: input }]);
    setInput("");
    // Simulate AI response
    setTimeout(() => {
      setChat(prev => [...prev, {
        role: "assistant",
        text: "Analyzing current candidate pool... CAT-0241 shows consistent high selectivity in recent simulations.",
      }]);
    }, 1000);
  };


  const renderContent = () => {
    const isMainLoading = loadingReactions || loadingCatalysts || loadingRanking;
    
    switch (activeTab) {
      case "Overview": return <OverviewView stats={experimentSummary} projects={reactionsData?.reactions ?? []} isLoading={loadingReactions || loadingExperiments} />;
      case "Discovery": return (
        <PageTransition>
          {/* Reaction input */}
          <div className="px-6 pt-6">
            <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-primary mb-2">
              <Beaker className="h-3.5 w-3.5" /> Reaction Input
            </div>
            <div className="rounded-xl border border-border bg-card/60 p-4 flex flex-col md:flex-row gap-3 items-stretch md:items-center shadow-sm">
              <input
                value={reactionInput}
                onChange={(e) => setReactionInput(e.target.value)}
                className="flex-1 bg-input border border-border rounded-md px-3 py-2.5 font-mono text-sm focus:outline-none focus:border-primary/60 transition-colors"
              />
              <div className="flex gap-2">
                <select className="bg-input border border-border rounded-md px-2 py-2 text-sm focus:border-primary/40 focus:outline-none">
                  <option>Heterogeneous</option>
                  <option>Homogeneous</option>
                  <option>Enzymatic</option>
                </select>
                <button 
                  onClick={() => discoveryMutation.mutate(reactionInput)}
                  disabled={discoveryMutation.isPending}
                  className="px-4 py-2 rounded-md bg-primary text-primary-foreground font-mono text-xs uppercase tracking-widest hover:opacity-90 flex items-center justify-center gap-2 disabled:opacity-50 transition-all"
                >
                  {discoveryMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />} 
                  Generate
                </button>
              </div>
            </div>
          </div>

          {/* Candidate cards */}
          <div className="px-6 pt-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-primary">
                <Sparkles className="h-3.5 w-3.5" /> {loadingRanking ? "Ranking Candidates..." : `AI-Generated Candidates · ${rankingData?.length ?? 0} ranked`}
              </div>
              <span className="hidden sm:inline font-mono text-[10px] text-muted-foreground">Sorted by composite score</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {loadingRanking ? (
                Array(4).fill(0).map((_, i) => (
                  <div key={i} className="h-40 rounded-xl border border-border bg-card/60 animate-pulse" />
                ))
              ) : (
                rankingData?.slice(0,4).map((c: any) => (
                  <button
                    key={c.catalyst_id}
                    onClick={() => setSelectedCandidate(c)}
                    className={`text-left rounded-xl border p-4 transition-all duration-300 ${
                      selectedCandidate?.catalyst_id === c.catalyst_id ? "border-primary/60 bg-primary/5 shadow-inner" : "border-border bg-card/60 hover:border-primary/40 hover:bg-primary/5"
                    }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <span className="font-mono text-[10px] text-muted-foreground">{c.catalyst_id.slice(0, 8)}</span>
                      {c.source === "generated" && <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-accent/20 text-accent border border-accent/40">NOVEL</span>}
                    </div>
                    <div className="font-display text-lg mb-1 truncate">{c.composition}</div>
                    <div className="font-mono text-[9px] text-primary/80 mb-3 truncate italic">{c.explanation}</div>
                    <div className="grid grid-cols-3 gap-2 text-center mb-3">
                      <Stat label="Sel%" value={Math.round(c.selectivity)} />
                      <Stat label="Act%" value={Math.round(c.activity)} />
                      <Stat label="Stab" value={Math.round(c.stability)} />
                    </div>
                    <div className="flex items-center justify-between font-mono text-[10px]">
                      <span className="text-muted-foreground">Score</span>
                      <div className="flex-1 mx-2 h-1 rounded bg-secondary overflow-hidden">
                        <div className="h-full bg-primary" style={{ width: `${c.combined_score * 100}%` }} />
                      </div>
                      <span className="text-primary">{c.combined_score.toFixed(2)}</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>


          {/* 3D viewer + Predictions */}
          <div className="px-6 pt-6 grid grid-cols-1 lg:grid-cols-5 gap-4">
            {/* 3D Visualization */}
            <div className="lg:col-span-3 rounded-xl border border-border bg-card/60 p-5 relative overflow-hidden shadow-sm">
              <div className="absolute inset-0 grid-bg opacity-20" />
              {!selectedCandidate ? (
                <div className="h-64 flex items-center justify-center text-muted-foreground font-mono text-xs italic">Select a candidate to view structure</div>
              ) : (
                <div className="animate-fade-in-up">
                  <div className="relative flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 gap-2">
                    <div>
                      <div className="font-mono text-[10px] uppercase tracking-widest text-primary mb-1">3D Structure</div>
                      <div className="font-display text-xl">{selectedCandidate.composition}</div>
                    </div>
                    <div className="flex gap-1.5 font-mono text-[10px] overflow-x-auto w-full sm:w-auto">
                      {["Ball+Stick", "Surface", "Orbital"].map((m, i) => (
                        <button key={m} className={`px-2 py-1 rounded border whitespace-nowrap transition-colors ${i === 0 ? "border-primary/50 text-primary bg-primary/10" : "border-border text-muted-foreground hover:bg-secondary/40"}`}>{m}</button>
                      ))}
                    </div>
                  </div>
                  <div className="relative h-64 sm:h-72 flex items-center justify-center">
                    <Molecule3D />
                  </div>
                  <div className="relative grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2 font-mono text-[10px]">
                    {[
                      ["Atoms", "47"],
                      ["Bonds", "82"],
                      ["Symmetry", "Pm-3m"],
                      ["a (Å)", "4.21"],
                    ].map(([k, v]) => (
                      <div key={k} className="rounded border border-border/60 bg-background/40 px-2 py-1.5 hover:border-primary/20 transition-colors">
                        <div className="text-muted-foreground">{k}</div>
                        <div className="text-foreground">{v}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Prediction analytics */}
            <div className="lg:col-span-2 rounded-xl border border-border bg-card/60 p-5 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="font-mono text-[10px] uppercase tracking-widest text-primary flex items-center gap-2">
                  <BarChart3 className="h-3.5 w-3.5" /> Prediction Analytics
                </div>
                <span className="font-mono text-[9px] text-muted-foreground">±2σ uncertainty</span>
              </div>

              {!selectedCandidate ? (
                <div className="h-64 flex items-center justify-center text-muted-foreground font-mono text-xs italic">No candidate selected</div>
              ) : (
                <div className="space-y-3 animate-fade-in-up">
                  {[
                    { label: "Selectivity", val: Math.round(selectedCandidate.selectivity), unc: Math.round(selectedCandidate.uncertainty * 100), col: "bg-primary", max: 100 },
                    { label: "Activity", val: Math.round(selectedCandidate.activity), unc: Math.round(selectedCandidate.uncertainty * 80), col: "bg-accent", max: 100 },
                    { label: "Stability", val: Math.round(selectedCandidate.stability), unc: Math.round(selectedCandidate.uncertainty * 120), col: "bg-amber-warn", max: 100 },
                    { label: "Combined Score", val: Math.round(selectedCandidate.combined_score * 100), unc: 5, col: "bg-violet-500", suffix: "", max: 100 },
                  ].map((m) => (
                    <div key={m.label}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-muted-foreground">{m.label}</span>
                        <span className="font-mono text-foreground">{m.val}{m.suffix ?? "%"} <span className="text-muted-foreground">±{m.unc}</span></span>
                      </div>
                      <div className="relative h-2 bg-secondary/60 rounded overflow-hidden">
                        <div className={`absolute inset-y-0 left-0 ${m.col} transition-all duration-700`} style={{ width: `${(m.val / m.max) * 100}%` }} />
                        <div className="absolute inset-y-0 bg-foreground/20" style={{ left: `${((m.val - m.unc) / m.max) * 100}%`, width: `${((2 * m.unc) / m.max) * 100}%` }} />
                      </div>
                    </div>
                  ))}

                  <div className="mt-4 p-3 rounded-lg bg-primary/5 border border-primary/20">
                    <div className="font-mono text-[9px] uppercase tracking-widest text-primary mb-2 flex items-center gap-1.5"><Info className="h-3 w-3" /> AI Insights</div>
                    <ul className="space-y-1.5">
                      {selectedCandidate.insights?.map((insight: string, idx: number) => (
                        <li key={idx} className="text-[11px] leading-relaxed flex gap-2">
                          <span className="text-primary">•</span>
                          <span>{insight}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {selectedCandidate.uncertainty_description && (
                    <div className="flex items-center gap-2 mt-2 px-1">
                      <AlertTriangle className="h-3 w-3 text-amber-warn" />
                      <span className="text-[10px] text-muted-foreground italic">{selectedCandidate.uncertainty_description}</span>
                    </div>
                  )}
                  <div className="mt-5 pt-4 border-t border-border/60">
                    <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Cycle convergence</div>
                    <Sparkline />
                  </div>
                </div>
              )}
            </div>
          </div>


          {/* Experiment log + Discrepancy */}
          <div className="px-6 py-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Experiment log */}
            <div className="rounded-xl border border-border bg-card/60 p-5 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="font-mono text-[10px] uppercase tracking-widest text-primary flex items-center gap-2 truncate">
                  <FlaskConical className="h-3.5 w-3.5" /> Exp Log · {selectedCandidate?.catalyst_id?.slice(0, 8) || "—"}
                </div>
                <button className="font-mono text-[10px] uppercase tracking-widest text-primary border border-primary/40 px-2.5 py-1 rounded hover:bg-primary/10 transition-colors">+ Entry</button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                {[
                  ["Pred Sel%", selectedCandidate?.selectivity, "Act Sel%", 79],
                  ["Pred Conv%", selectedCandidate?.activity, "Act Conv%", 54],
                ].map(([pl, pv, al, av]) => (
                  <div key={String(pl)} className="rounded-md border border-border/60 bg-background/40 p-3 hover:border-primary/20 transition-colors">
                    <div className="flex justify-between font-mono text-[10px] text-muted-foreground">
                      <span>{pl}</span><span>{al}</span>
                    </div>
                    <div className="flex justify-between items-baseline mt-1">
                      <span className="font-display text-2xl text-primary">{pv?.toFixed(1) || "—"}</span>
                      <span className="font-display text-2xl text-foreground">{av}</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="space-y-2">
                {[
                  { d: "2026-05-04", op: "Lab-A · Patel", note: "Synthesis complete · co-precipitation pH 7.2", ok: true },
                  { d: "2026-05-05", op: "Lab-A · Patel", note: "GC-MS run 01 · selectivity below pred. by 8%", ok: false },
                  { d: "2026-05-06", op: "Lab-A · Patel", note: "Repeat with reduced calcination T (350°C)", ok: true },
                ].map((l) => (
                  <div key={l.d + l.note} className="flex gap-3 text-sm py-2 border-b border-border/40 last:border-0 hover:bg-secondary/20 rounded px-2 -mx-2 transition-colors">
                    <span className="font-mono text-[10px] text-muted-foreground shrink-0 mt-1">{l.d}</span>
                    {l.ok ? <CheckCircle2 className="h-4 w-4 text-primary shrink-0 mt-0.5" /> : <AlertTriangle className="h-4 w-4 text-amber-warn shrink-0 mt-0.5 animate-pulse" />}
                    <div className="flex-1">
                      <div className="leading-snug">{l.note}</div>
                      <div className="font-mono text-[10px] text-muted-foreground mt-0.5">{l.op}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Discrepancy analysis */}
            <div className="rounded-xl border border-amber-warn/40 bg-amber-warn/5 p-5 shadow-sm">
              <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-amber-warn mb-3">
                <AlertTriangle className="h-3.5 w-3.5" /> AI Discrepancy Analysis
              </div>
              <div className="font-display text-lg mb-3 leading-tight">
                Predicted vs. observed selectivity diverges by <span className="text-amber-warn font-semibold">−8.4%</span>
              </div>
              <div className="space-y-2.5 text-sm text-muted-foreground">
                {[
                  { p: 0.72, h: "Steric hindrance at Cu-Zn interface underestimated by GNN" },
                  { p: 0.41, h: "Calcination temperature drives Cu particle migration" },
                  { p: 0.23, h: "Trace Fe contamination in support" },
                ].map((h) => (
                  <div key={h.h} className="flex items-start gap-3 rounded-md border border-border/60 bg-background/40 p-3 hover:border-amber-warn/20 transition-colors">
                    <span className="font-mono text-[10px] text-primary mt-0.5 shrink-0">P={h.p.toFixed(2)}</span>
                    <span className="text-foreground/90 leading-snug">{h.h}</span>
                  </div>
                ))}
              </div>
              <button onClick={() => setActiveTab('Feedback Loop')} className="mt-4 w-full font-mono text-[10px] uppercase tracking-widest border border-primary/40 text-primary py-2.5 rounded hover:bg-primary/10 flex items-center justify-center gap-2 transition-all">
                <RefreshCw className="h-3.5 w-3.5" /> Trigger retraining cycle
              </button>
            </div>
          </div>

          {/* Closed-loop workflow */}
          <div className="px-6 pb-10">
            <div className="font-mono text-[10px] uppercase tracking-widest text-primary mb-3 flex items-center gap-2">
              <RefreshCw className="h-3.5 w-3.5" /> Closed-Loop Learning
            </div>
            <div className="rounded-xl border border-border bg-card/60 p-5 shadow-sm">
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                {[
                  { i: Database, l: "Retrieve", s: "1,284 refs" },
                  { i: Sparkles, l: "Generate", s: "47 candidates" },
                  { i: Cpu, l: "Predict", s: "GNN + MLIP" },
                  { i: BarChart3, l: "Rank", s: "Top 4 surfaced", active: true },
                  { i: FlaskConical, l: "Test", s: "Lab-A logging" },
                  { i: RefreshCw, l: "Retrain", s: "Δ analysis ready" },
                ].map((s, idx) => {
                  const Icon = s.i;
                  return (
                    <div key={s.l} className={`relative rounded-lg border p-3 transition-all ${s.active ? "border-primary/60 bg-primary/10 shadow-sm" : "border-border bg-background/40 hover:border-primary/20"}`}>
                      <div className="flex items-center justify-between mb-2">
                        <Icon className={`h-4 w-4 ${s.active ? "text-primary" : "text-muted-foreground"}`} />
                        <span className="font-mono text-[9px] text-muted-foreground">0{idx + 1}</span>
                      </div>
                      <div className="text-sm font-medium">{s.l}</div>
                      <div className="font-mono text-[10px] text-muted-foreground">{s.s}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </PageTransition>
      );
      case "Candidates": return <CandidatesView candidates={rankingData ?? []} catalystSource={catalystsData?.source} catalystCount={catalystsData?.count} isLoading={loadingRanking} error={errorRanking} onRetry={() => queryClient.invalidateQueries({ queryKey: ["ranking"] })} />;
      case "Predictions": return <PredictionsView rankingData={rankingData ?? []} isLoading={loadingRanking} />;
      case "Visualizations": return <VisualizationsView rankingData={rankingData ?? []} isLoading={loadingRanking} />;
      case "Experiments": return <ExperimentsView stats={experimentSummary} isLoading={loadingExperiments} />;
      case "Feedback Loop": return <FeedbackLoopView
        history={retrainingHistory?.history ?? []}
        stats={experimentSummary}
        isLoading={loadingHistory}
        onTriggerRetraining={() => retrainingMutation.mutate()}
        retrainingToast={retrainingToast}
      />;
      case "Knowledge Base": return <KnowledgeBaseView />;
      case "Protocols": return <ProtocolsView />;
      default: return null;
    }
  };

  return (
    <div className="h-screen w-full bg-background text-foreground flex overflow-hidden font-sans">
      {/* LEFT SIDEBAR - Overlay on mobile */}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-50 w-64 shrink-0 border-r border-border/60 bg-card/90 backdrop-blur-xl flex flex-col transition-transform duration-300 md:relative md:translate-x-0 md:bg-card/40",
        isSidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="px-5 py-5 border-b border-border/60 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="relative h-7 w-7">
              <div className="absolute inset-0 rounded-full bg-primary/20 animate-pulse-glow" />
              <div className="absolute inset-1 rounded-full bg-primary glow-emerald" />
              <div className="absolute inset-[10px] rounded-full bg-background" />
            </div>

            <span className="font-display text-base font-semibold tracking-tight">
              CATALYST<span className="text-primary">.AI</span>
            </span>
          </Link>
          <button onClick={() => setIsSidebarOpen(false)} className="md:hidden text-muted-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-3 py-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <input
              placeholder="Search…"
              className="w-full bg-input border border-border rounded-md pl-8 pr-2 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:border-primary/60 transition-colors"
            />
          </div>
        </div>

        <nav className="px-2 flex-1 overflow-y-auto">
          <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground px-3 py-2">Workflow</div>
          {navItems.map((it) => {
            const Icon = it.icon;
            const isActive = activeTab === it.label;
            return (
              <button
                key={it.label}
                onClick={() => {
                  setActiveTab(it.label);
                  setIsSidebarOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all ${
                  isActive
                    ? "bg-primary/15 text-foreground border border-primary/30 shadow-sm"
                    : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground border border-transparent"
                }`}
              >
                <Icon className="h-4 w-4" />
                {it.label}
              </button>
            );
          })}

          <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground px-3 py-2 mt-4">Active Projects</div>
          {(reactionsData?.reactions ?? []).length === 0 && (
            <div className="px-3 py-2 text-[10px] text-muted-foreground italic">No projects active</div>
          )}
          {(reactionsData?.reactions ?? []).map((p: any) => (
            <button key={p.id} className="w-full flex items-center justify-between px-3 py-2 rounded-md text-sm text-muted-foreground hover:bg-secondary/60 hover:text-foreground transition-colors group">
              <span className="flex items-center gap-2 truncate">
                <span className="h-1.5 w-1.5 rounded-full bg-primary animate-blink" />
                <span className="truncate group-hover:text-foreground">{p.name}</span>
              </span>
              <span className="font-mono text-[9px] text-muted-foreground/70">{p.solvent}</span>
            </button>
          ))}
        </nav>

        <div className="border-t border-border/60 p-3 flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-primary-foreground text-xs font-semibold shadow-sm">DR</div>
          <div className="flex-1 min-w-0">
            <div className="text-sm truncate">Dr. R. Sharma</div>
            <div className="font-mono text-[10px] text-muted-foreground truncate">GPS Renewables · Lead</div>
          </div>
          <Settings className="h-4 w-4 text-muted-foreground hover:text-foreground cursor-pointer transition-colors" />
        </div>
      </aside>

      {/* MOBILE OVERLAY */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-background/60 backdrop-blur-sm md:hidden" 
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* CENTRAL WORKSPACE */}
      <section className="flex-1 flex flex-col overflow-hidden relative">
        {/* Top bar */}
        <div className="border-b border-border/60 bg-background/80 backdrop-blur px-4 sm:px-6 py-3 flex items-center justify-between z-30">
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <button onClick={() => setIsSidebarOpen(true)} className="md:hidden text-foreground mr-1">
              <Menu className="h-5 w-5" />
            </button>
            <span className="hidden sm:inline">Workspace</span>
            <ChevronRight className="hidden sm:inline h-3.5 w-3.5" />
            <span className="text-foreground font-medium">{activeTab}</span>
            {activeTab === "Discovery" && (
              <>
                <ChevronRight className="hidden md:inline h-3.5 w-3.5" />
                <span className="hidden md:inline text-foreground">CO₂ → Methanol</span>
              </>
            )}
          </div>
          <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-widest">
            <span className="hidden lg:flex items-center gap-1.5 text-primary">
              <span className="h-1.5 w-1.5 rounded-full bg-primary animate-blink" /> Models online
            </span>
            <div className="h-4 w-px bg-border/60 hidden lg:block" />
            <span className="text-muted-foreground">v3.4.1</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto bg-background/50">
          {renderContent()}
        </div>
      </section>

      {/* RIGHT AI ASSISTANT */}
      <aside className="flex w-80 2xl:w-96 shrink-0 border-l border-border/60 bg-card/40 flex-col">
        <div className="px-5 py-4 border-b border-border/60 flex items-center gap-3">
          <div className="relative h-9 w-9 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg">
            <Bot className="h-5 w-5 text-primary-foreground" />
            <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-primary border-2 border-card animate-blink" />
          </div>
          <div>
            <div className="font-display text-sm">Catalyst Copilot</div>
            <div className="font-mono text-[10px] text-muted-foreground">GNN-v3 · ESM-2 · MLIP grounded</div>
          </div>
        </div>

        <div className="px-4 py-3 border-b border-border/60 grid grid-cols-3 gap-2 font-mono text-[10px]">
          {[
            ["Cycles", "14"],
            ["ΔAcc", "+3.1%"],
            ["Drift", "0.8σ"],
          ].map(([k, v]) => (
            <div key={k} className="rounded border border-border/60 bg-background/40 px-2 py-1.5 text-center hover:border-primary/20 transition-colors">
              <div className="text-muted-foreground">{k}</div>
              <div className="text-foreground text-sm font-display">{v}</div>
            </div>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
          {chat.map((m, i) => {
            const isUser = m.role === "user";
            return (
              <div key={i} className={`flex gap-2.5 animate-fade-in-up ${isUser ? "flex-row-reverse" : ""}`}>
                <div className={`h-7 w-7 shrink-0 rounded-md flex items-center justify-center shadow-sm ${isUser ? "bg-secondary" : "bg-primary/15 border border-primary/30"}`}>
                  {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5 text-primary" />}
                </div>
                <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm shadow-sm ${isUser ? "bg-primary text-primary-foreground" : "bg-background/60 border border-border/60"}`}>
                  {m.text}
                </div>
              </div>
            );
          })}

          <div className="rounded-lg border border-primary/30 bg-primary/5 p-3 shadow-sm animate-pulse-glow">
            <div className="font-mono text-[10px] uppercase tracking-widest text-primary mb-2 flex items-center gap-1.5">
              <Layers className="h-3 w-3" /> Suggested next action
            </div>
            <div className="text-sm mb-2 leading-snug">Run DFT validation on CAT-0241 surface (111) before committing to wet lab.</div>
            <button className="font-mono text-[10px] uppercase tracking-widest text-primary border border-primary/40 px-2 py-1 rounded hover:bg-primary/10 transition-colors">Queue job</button>
          </div>
        </div>

        <div className="border-t border-border/60 p-3">
          <div className="flex flex-wrap gap-1.5 mb-2 overflow-x-auto pb-1 no-scrollbar">
            {["Compare to baseline", "Export protocol", "Find references"].map((q) => (
              <button key={q} onClick={() => setInput(q)} className="font-mono text-[10px] px-2 py-1 rounded border border-border bg-secondary/60 hover:border-primary/40 whitespace-nowrap transition-colors">{q}</button>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder="Ask the copilot…"
              className="flex-1 bg-input border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary/60 transition-colors"
            />
            <button onClick={send} className="h-9 w-9 rounded-md bg-primary text-primary-foreground flex items-center justify-center hover:opacity-90 transition-all">
              <Send className="h-4 w-4" />
            </button>
          </div>
          <div className="font-mono text-[9px] text-muted-foreground mt-2 flex items-center gap-1.5">
            <Activity className="h-3 w-3" /> Grounded in 1,284 retrieved refs
          </div>
        </div>
      </aside>
    </div>
  );
}
