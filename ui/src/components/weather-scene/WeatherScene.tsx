"use client";

import dynamic from "next/dynamic";
import { useSyncExternalStore } from "react";
import { NormalizedWeatherState } from "@/types/weather";

interface WeatherSceneProps {
  weather: NormalizedWeatherState;
  className?: string;
  disable3D?: boolean;
}

// Dynamically import Canvas with SSR disabled to prevent Three.js window/WebGL errors during Next.js SSR
const WeatherSceneCanvasDynamic = dynamic(
  () => import("./WeatherSceneCanvas"),
  {
    ssr: false,
    loading: () => null,
  }
);

// External store for mounted state
function subscribeMounted() {
  return () => {};
}
function getMountedSnapshot() {
  return true;
}
function getMountedServerSnapshot() {
  return false;
}

// External store for reduced motion
function subscribeReducedMotion(callback: () => void) {
  if (typeof window === "undefined") return () => {};
  const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  mediaQuery.addEventListener("change", callback);
  return () => mediaQuery.removeEventListener("change", callback);
}
function getReducedMotionSnapshot() {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
function getReducedMotionServerSnapshot() {
  return false;
}

export function WeatherScene({ weather, className = "", disable3D = false }: WeatherSceneProps) {
  const isMounted = useSyncExternalStore(
    subscribeMounted,
    getMountedSnapshot,
    getMountedServerSnapshot
  );

  const reducedMotion = useSyncExternalStore(
    subscribeReducedMotion,
    getReducedMotionSnapshot,
    getReducedMotionServerSnapshot
  );

  // Compute CSS background tint based on real weather condition
  const getAtmosphericGradient = () => {
    switch (weather.condition) {
      case "SUNNY":
        return "radial-gradient(ellipse at 80% 20%, rgba(251, 191, 36, 0.18) 0%, rgba(12, 36, 68, 0.4) 45%, rgba(6, 17, 31, 0.95) 100%)";
      case "PARTLY_CLOUDY":
        return "radial-gradient(ellipse at 75% 25%, rgba(245, 158, 11, 0.12) 0%, rgba(14, 43, 76, 0.35) 45%, rgba(6, 17, 31, 0.95) 100%)";
      case "CLOUDY":
        return "radial-gradient(ellipse at 50% 10%, rgba(71, 85, 105, 0.25) 0%, rgba(15, 33, 56, 0.4) 50%, rgba(6, 17, 31, 0.98) 100%)";
      case "RAIN":
      case "HEAVY_RAIN":
        return "radial-gradient(ellipse at 50% 10%, rgba(56, 189, 248, 0.15) 0%, rgba(14, 30, 52, 0.45) 50%, rgba(6, 17, 31, 0.98) 100%)";
      case "STORM":
        return "radial-gradient(ellipse at 50% 0%, rgba(99, 102, 241, 0.18) 0%, rgba(10, 18, 32, 0.6) 50%, rgba(3, 8, 18, 0.98) 100%)";
      case "WIND":
        return "radial-gradient(ellipse at 80% 30%, rgba(103, 232, 249, 0.15) 0%, rgba(12, 36, 66, 0.35) 45%, rgba(6, 17, 31, 0.95) 100%)";
      case "FOG":
        return "radial-gradient(ellipse at 50% 50%, rgba(203, 213, 225, 0.1) 0%, rgba(14, 33, 56, 0.4) 60%, rgba(6, 17, 31, 0.98) 100%)";
      case "NIGHT":
      default:
        return "radial-gradient(ellipse at 80% 20%, rgba(148, 163, 184, 0.12) 0%, rgba(9, 23, 42, 0.4) 50%, rgba(4, 10, 20, 0.98) 100%)";
    }
  };

  return (
    <div
      className={`absolute inset-0 overflow-hidden pointer-events-none transition-all duration-700 ${className}`}
      style={{ background: getAtmosphericGradient() }}
    >
      {/* 3D WebGL Canvas (disabled if user prefers reduced motion or disable3D requested) */}
      {isMounted && !reducedMotion && !disable3D && (
        <div className="absolute inset-0 w-full h-full opacity-90 transition-opacity duration-1000">
          <WeatherSceneCanvasDynamic weather={weather} />
        </div>
      )}

      {/* Atmospheric vignette & soft horizon overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent pointer-events-none" />
    </div>
  );
}
export default WeatherScene;
