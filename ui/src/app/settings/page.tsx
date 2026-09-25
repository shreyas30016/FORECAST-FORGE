"use client";

import { 
  Sliders, 
  Thermometer, 
  Wind, 
  Gauge
} from "lucide-react";
import { useSettings } from "@/context/SettingsContext";

export default function SettingsPage() {
  const { 
    tempUnit, 
    setTempUnit, 
    windUnit, 
    setWindUnit, 
    pressureUnit, 
    setPressureUnit,
    tempSymbol,
    windSymbol,
    pressureSymbol
  } = useSettings();

  return (
    <div className="flex flex-col gap-6 text-slate-100 max-w-4xl mx-auto pb-12">
      
      {/* Header Bar */}
      <div className="glass-panel p-5 sm:p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 border border-white/10 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-40 bg-ensemble/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex items-start sm:items-center gap-3.5 relative z-10">
          <div className="w-11 h-11 rounded-xl bg-ensemble/15 border border-ensemble/30 flex items-center justify-center text-ensemble shrink-0 shadow-inner">
            <Sliders className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                Measurement Units
              </h1>
              <span className="hidden sm:inline-block px-2.5 py-0.5 rounded-full text-[10px] font-mono tracking-wider bg-ensemble/20 text-ensemble border border-ensemble/40">
                ACTIVE CONFIGURATION
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
              Configure meteorological measurement scales applied globally across all forecast views, maps, and models
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 relative z-10 font-mono text-xs">
          <span className="px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-slate-300">
            Active: <strong className="text-ensemble">{tempSymbol}</strong> · <strong className="text-cyan-400">{windSymbol}</strong> · <strong className="text-amber-400">{pressureSymbol}</strong>
          </span>
        </div>
      </div>

      {/* Meteorological Unit Preferences */}
      <div className="glass-panel p-6 rounded-2xl border border-white/10 shadow-xl space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-ensemble" />
            <h2 className="text-base font-bold text-white tracking-tight">
              Unit Configuration
            </h2>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Persisted in Local Storage
          </span>
        </div>

        <div className="space-y-4">
          
          {/* Temperature Unit */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 shrink-0 mt-0.5">
                <Thermometer className="w-4 h-4" />
              </div>
              <div>
                <span className="text-sm font-semibold text-white block">Temperature Scale</span>
                <span className="text-xs text-slate-400">Applied to ensemble forecasts, model cards, timelines, and alert thresholds</span>
              </div>
            </div>
            <div className="flex items-center gap-1.5 p-1 rounded-xl bg-black/40 border border-white/10 shrink-0">
              <button
                type="button"
                onClick={() => setTempUnit("celsius")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  tempUnit === "celsius" ? "bg-ensemble text-slate-950 shadow-md font-black" : "text-slate-400 hover:text-white"
                }`}
              >
                Celsius (°C)
              </button>
              <button
                type="button"
                onClick={() => setTempUnit("fahrenheit")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  tempUnit === "fahrenheit" ? "bg-ensemble text-slate-950 shadow-md font-black" : "text-slate-400 hover:text-white"
                }`}
              >
                Fahrenheit (°F)
              </button>
            </div>
          </div>

          {/* Wind Speed Unit */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shrink-0 mt-0.5">
                <Wind className="w-4 h-4" />
              </div>
              <div>
                <span className="text-sm font-semibold text-white block">Surface Wind Velocity</span>
                <span className="text-xs text-slate-400">10m atmospheric boundary layer velocity unit across weather cards and extremes</span>
              </div>
            </div>
            <div className="flex items-center gap-1.5 p-1 rounded-xl bg-black/40 border border-white/10 shrink-0">
              <button
                type="button"
                onClick={() => setWindUnit("kmh")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  windUnit === "kmh" ? "bg-ensemble text-slate-950 shadow-md font-black" : "text-slate-400 hover:text-white"
                }`}
              >
                km/h
              </button>
              <button
                type="button"
                onClick={() => setWindUnit("ms")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  windUnit === "ms" ? "bg-ensemble text-slate-950 shadow-md font-black" : "text-slate-400 hover:text-white"
                }`}
              >
                m/s
              </button>
              <button
                type="button"
                onClick={() => setWindUnit("knots")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  windUnit === "knots" ? "bg-ensemble text-slate-950 shadow-md font-black" : "text-slate-400 hover:text-white"
                }`}
              >
                knots
              </button>
            </div>
          </div>

          {/* Pressure Unit */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 shrink-0 mt-0.5">
                <Gauge className="w-4 h-4" />
              </div>
              <div>
                <span className="text-sm font-semibold text-white block">Barometric Pressure</span>
                <span className="text-xs text-slate-400">Mean sea level atmospheric pressure unit</span>
              </div>
            </div>
            <div className="flex items-center gap-1.5 p-1 rounded-xl bg-black/40 border border-white/10 shrink-0">
              <button
                type="button"
                onClick={() => setPressureUnit("hpa")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  pressureUnit === "hpa" ? "bg-ensemble text-slate-950 shadow-md font-black" : "text-slate-400 hover:text-white"
                }`}
              >
                hPa (mbar)
              </button>
              <button
                type="button"
                onClick={() => setPressureUnit("inhg")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  pressureUnit === "inhg" ? "bg-ensemble text-slate-950 shadow-md font-black" : "text-slate-400 hover:text-white"
                }`}
              >
                inHg
              </button>
            </div>
          </div>

        </div>
      </div>

    </div>
  );
}
