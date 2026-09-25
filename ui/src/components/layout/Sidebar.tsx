"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  CloudSun, 
  GitCompare, 
  Layers, 
  Map as MapIcon,
  LineChart, 
  Bell, 
  Database, 
  Settings,
  Sparkles,
  MoreHorizontal,
  History,
  X
} from "lucide-react";

export const primaryNavItems = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Forecast", href: "/forecast", icon: CloudSun },
  { name: "Weather Maps", href: "/maps", icon: MapIcon },
  { name: "Comparison", href: "/compare", icon: GitCompare },
  { name: "Ensemble", href: "/ensemble", icon: Layers },
];

export const secondaryNavItems = [
  { name: "Historical Lab", href: "/historical", icon: LineChart },
  { name: "Risk Center", href: "/alerts", icon: Bell },
  { name: "Provider Health", href: "/sources", icon: Database },
  { name: "Decision Replay", href: "/replay", icon: History },
  { name: "Settings", href: "/settings", icon: Settings },
];

export const allNavItems = [...primaryNavItems, ...secondaryNavItems];

export function Sidebar() {
  const pathname = usePathname();
  const [mobileMoreOpen, setMobileMoreOpen] = useState(false);

  // Top 4 quick-access routes for mobile bar
  const mobileQuickItems = primaryNavItems.slice(0, 4);

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="w-64 bg-panel/90 backdrop-blur-md border-r border-border-subtle flex-col hidden md:flex shrink-0 z-20">
        {/* Brand Header */}
        <div className="h-16 border-b border-border-subtle flex items-center px-4 justify-between bg-background/40">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-ensemble to-emerald-600 flex items-center justify-center text-slate-950 font-black shadow-lg shadow-ensemble/20 group-hover:scale-105 transition-transform duration-300">
              <Sparkles className="w-4 h-4 fill-slate-950" />
            </div>
            <div className="leading-tight">
              <span className="text-sm font-extrabold tracking-tight text-white block">
                FORECAST FORGE
              </span>
              <span className="text-[10px] font-mono tracking-wider text-ensemble block">
                ATMOSPHERIC AI
              </span>
            </div>
          </Link>
        </div>
        
        {/* Navigation Sections */}
        <div className="flex-1 py-4 overflow-y-auto px-3 space-y-5">
          {/* Core Operations */}
          <div>
            <div className="px-2 mb-1.5 text-[10px] font-mono uppercase tracking-wider text-text-muted">
              Core Operations
            </div>
            <nav className="space-y-1">
              {primaryNavItems.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-all duration-200 ${
                      isActive
                        ? "bg-ensemble/15 text-white font-bold border-l-2 border-ensemble shadow-sm"
                        : "text-text-secondary hover:bg-panel-hover hover:text-white"
                    }`}
                  >
                    <item.icon className={`h-4 w-4 shrink-0 transition-colors ${isActive ? "text-ensemble" : "text-text-secondary"}`} />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* System & Verification */}
          <div>
            <div className="px-2 mb-1.5 text-[10px] font-mono uppercase tracking-wider text-text-muted">
              System & Verification
            </div>
            <nav className="space-y-1">
              {secondaryNavItems.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-all duration-200 ${
                      isActive
                        ? "bg-ensemble/15 text-white font-bold border-l-2 border-ensemble shadow-sm"
                        : "text-text-secondary hover:bg-panel-hover hover:text-white"
                    }`}
                  >
                    <item.icon className={`h-4 w-4 shrink-0 transition-colors ${isActive ? "text-ensemble" : "text-text-secondary"}`} />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>

        {/* Live System Telemetry Status Footnote */}
        <div className="p-3 border-t border-border-subtle bg-background/50 font-mono text-[11px] space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">Synthesis:</span>
            <span className="text-ensemble font-semibold">Ridge Adaptive</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">NWP Feed:</span>
            <span className="text-status-available flex items-center gap-1.5 font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-status-available animate-pulse" />
              SYNCHRONIZED
            </span>
          </div>
        </div>
      </aside>

      {/* Mobile More Drawer Backdrop */}
      {mobileMoreOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity"
          onClick={() => setMobileMoreOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile Extended Navigation Drawer */}
      {mobileMoreOpen && (
        <div className="md:hidden fixed bottom-14 left-0 right-0 z-50 bg-panel border-t border-border-subtle p-3 shadow-2xl font-mono text-xs">
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-border-subtle">
            <span className="text-[10px] uppercase text-text-secondary tracking-wider">All Workstation Modules</span>
            <button
              type="button"
              onClick={() => setMobileMoreOpen(false)}
              className="p-1 text-text-secondary hover:text-white"
              aria-label="Close menu"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {allNavItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMoreOpen(false)}
                  className={`flex flex-col items-center justify-center p-2.5 rounded-md border text-center transition-colors ${
                    isActive
                      ? "bg-ensemble/15 border-ensemble text-white font-bold"
                      : "bg-background border-border-subtle text-text-secondary hover:text-white"
                  }`}
                >
                  <item.icon className={`w-5 h-5 mb-1.5 ${isActive ? "text-ensemble" : ""}`} />
                  <span className="text-[10px] truncate max-w-full font-sans">{item.name}</span>
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* Mobile Bottom Navigation Bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 h-14 bg-panel/95 backdrop-blur-lg border-t border-border-subtle z-40 flex items-center justify-around px-1 font-mono text-[10px]">
        {mobileQuickItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center justify-center py-1 px-2 rounded-md transition-colors ${
                isActive ? "text-ensemble font-bold" : "text-text-secondary hover:text-white"
              }`}
            >
              <item.icon className="w-4 h-4" />
              <span className="mt-0.5 tracking-tighter truncate max-w-[56px] font-sans">{item.name}</span>
            </Link>
          );
        })}

        {/* More Trigger */}
        <button
          type="button"
          onClick={() => setMobileMoreOpen(!mobileMoreOpen)}
          className={`flex flex-col items-center justify-center py-1 px-2 rounded-md transition-colors ${
            mobileMoreOpen ? "text-ensemble font-bold" : "text-text-secondary hover:text-white"
          }`}
          aria-expanded={mobileMoreOpen}
          aria-label="Open full workstation views navigation"
        >
          <MoreHorizontal className="w-4 h-4" />
          <span className="mt-0.5 tracking-tighter font-sans">More</span>
        </button>
      </nav>
    </>
  );
}
