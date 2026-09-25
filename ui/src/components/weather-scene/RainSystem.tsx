"use client";

import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface RainSystemProps {
  precipitation: number; // mm
  windSpeed: number; // km/h
}

// Deterministic PRNG to satisfy React 19 purity rules
function getPseudoRandom(seed: number): number {
  const x = Math.sin(seed * 12.9898 + 78.233) * 43758.5453;
  return x - Math.floor(x);
}

export function RainSystem({ precipitation, windSpeed }: RainSystemProps) {
  const pointsRef = useRef<THREE.Points>(null);

  // Scale drop count with real precipitation intensity
  const dropCount = useMemo(() => {
    if (precipitation <= 0.05) return 0;
    if (precipitation < 1.0) return 300; // Light rain
    if (precipitation < 5.0) return 750; // Moderate rain
    return 1500; // Heavy / storm rain
  }, [precipitation]);

  // Generate deterministic particle positions
  const [positions, speeds] = useMemo(() => {
    if (dropCount === 0) return [new Float32Array(0), new Float32Array(0)];

    const pos = new Float32Array(dropCount * 3);
    const spd = new Float32Array(dropCount);

    for (let i = 0; i < dropCount; i++) {
      const r1 = getPseudoRandom(i * 3 + 1);
      const r2 = getPseudoRandom(i * 3 + 2);
      const r3 = getPseudoRandom(i * 3 + 3);
      const r4 = getPseudoRandom(i * 3 + 4);

      pos[i * 3] = (r1 - 0.5) * 32; // X
      pos[i * 3 + 1] = r2 * 20 - 5; // Y
      pos[i * 3 + 2] = (r3 - 0.5) * 16 - 4; // Z
      spd[i] = 12 + r4 * 10;
    }

    return [pos, spd];
  }, [dropCount]);

  // Rain drop fall and slant loop
  useFrame((_, delta) => {
    if (!pointsRef.current || dropCount === 0) return;
    const posAttr = pointsRef.current.geometry.attributes.position as THREE.BufferAttribute;
    const array = posAttr.array as Float32Array;

    const windLean = (windSpeed / 50) * 4; // Slant with wind

    for (let i = 0; i < dropCount; i++) {
      // Move downward
      array[i * 3 + 1] -= speeds[i] * delta;
      // Slant with wind
      array[i * 3] += windLean * delta;

      // Reset to top if fallen past floor
      if (array[i * 3 + 1] < -6) {
        array[i * 3 + 1] = 14;
        const resetSeed = (i + Math.floor(delta * 1000)) % 10000;
        array[i * 3] = (getPseudoRandom(resetSeed) - 0.5) * 32;
      }
    }

    posAttr.needsUpdate = true;
  });

  if (dropCount === 0) return null;

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        color="#93c5fd"
        size={0.12}
        transparent
        opacity={0.65}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}
