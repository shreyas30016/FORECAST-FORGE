"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { WeatherCondition } from "@/types/weather";

interface SunMoonProps {
  condition: WeatherCondition;
  isDay: boolean;
}

export function SunMoon({ condition, isDay }: SunMoonProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);

  // Subtle floating animation
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (meshRef.current) {
      meshRef.current.position.y = 4.2 + Math.sin(t * 0.5) * 0.15;
    }
    if (glowRef.current) {
      glowRef.current.position.y = 4.2 + Math.sin(t * 0.5) * 0.15;
      const s = 1.0 + Math.sin(t * 1.2) * 0.05;
      glowRef.current.scale.set(s, s, s);
    }
  });

  // Obscure in stormy or heavy rain conditions
  const isHidden = condition === "STORM" || condition === "HEAVY_RAIN";
  if (isHidden) return null;

  const isSun = isDay && condition !== "NIGHT";
  const mainColor = isSun ? "#FBBF24" : "#E2E8F0";
  const glowColor = isSun ? "#F59E0B" : "#94A3B8";

  return (
    <group position={[6.5, 4.2, -10]}>
      {/* Central Core Celestial Body */}
      <mesh ref={meshRef}>
        <sphereGeometry args={[1.2, 32, 32]} />
        <meshStandardMaterial
          color={mainColor}
          emissive={mainColor}
          emissiveIntensity={isSun ? 0.8 : 0.4}
          roughness={0.2}
        />
      </mesh>

      {/* Atmospheric Soft Glow Halo */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[1.8, 24, 24]} />
        <meshBasicMaterial
          color={glowColor}
          transparent
          opacity={isSun ? 0.25 : 0.15}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}
