"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { WeatherCondition } from "@/types/weather";

interface LightingControllerProps {
  condition: WeatherCondition;
  isDay: boolean;
}

export function LightingController({ condition, isDay }: LightingControllerProps) {
  const lightningLightRef = useRef<THREE.PointLight>(null);
  const nextFlashTime = useRef<number>(8.0);

  // Subtle lightning flash for storms
  useFrame(({ clock }) => {
    if (condition !== "STORM" || !lightningLightRef.current) return;
    const t = clock.getElapsedTime();

    if (t > nextFlashTime.current) {
      // Trigger a brief 100ms flash
      lightningLightRef.current.intensity = 4.0;
      setTimeout(() => {
        if (lightningLightRef.current) {
          lightningLightRef.current.intensity = 0;
        }
      }, 120);

      // Schedule next flash (8 to 18 seconds later - restrained, non-jarring)
      nextFlashTime.current = t + 8 + Math.random() * 10;
    }
  });

  const ambientColor = isDay
    ? condition === "STORM" || condition === "HEAVY_RAIN"
      ? "#334155"
      : "#94a3b8"
    : "#1e293b";

  const dirColor = isDay && condition !== "STORM" ? "#fef3c7" : "#38bdf8";
  const dirIntensity = isDay ? (condition === "STORM" ? 0.4 : 1.2) : 0.3;

  return (
    <>
      <ambientLight color={ambientColor} intensity={0.65} />
      <directionalLight
        position={[8, 12, 5]}
        color={dirColor}
        intensity={dirIntensity}
      />
      {condition === "STORM" && (
        <pointLight
          ref={lightningLightRef}
          position={[0, 8, -5]}
          color="#e0e7ff"
          intensity={0}
          distance={35}
        />
      )}
    </>
  );
}
