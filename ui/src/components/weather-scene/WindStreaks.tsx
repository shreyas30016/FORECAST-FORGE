"use client";

import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface WindStreaksProps {
  windSpeed: number; // km/h
}

// Deterministic PRNG to satisfy React 19 purity rules
function getPseudoRandom(seed: number): number {
  const x = Math.sin(seed * 12.9898 + 78.233) * 43758.5453;
  return x - Math.floor(x);
}

export function WindStreaks({ windSpeed }: WindStreaksProps) {
  const groupRef = useRef<THREE.Group>(null);

  // Only render streaks if wind is noticeable (>14 km/h)
  const streakCount = useMemo(() => {
    if (windSpeed < 14) return 0;
    if (windSpeed < 30) return 12;
    return 24;
  }, [windSpeed]);

  const streaks = useMemo(() => {
    const list = [];
    for (let i = 0; i < streakCount; i++) {
      const r1 = getPseudoRandom(i * 5 + 1);
      const r2 = getPseudoRandom(i * 5 + 2);
      const r3 = getPseudoRandom(i * 5 + 3);
      const r4 = getPseudoRandom(i * 5 + 4);
      const r5 = getPseudoRandom(i * 5 + 5);

      list.push({
        x: (r1 - 0.5) * 28,
        y: r2 * 10 - 2,
        z: -5 - r3 * 8,
        length: 2 + r4 * 3,
        speed: (windSpeed / 20) * (3 + r5 * 2),
      });
    }
    return list;
  }, [streakCount, windSpeed]);

  useFrame((_, delta) => {
    if (!groupRef.current || streakCount === 0) return;
    groupRef.current.children.forEach((child, i) => {
      const s = streaks[i];
      if (!s) return;
      child.position.x += s.speed * delta;
      if (child.position.x > 18) {
        child.position.x = -18;
      }
    });
  });

  if (streakCount === 0) return null;

  return (
    <group ref={groupRef}>
      {streaks.map((s, i) => (
        <mesh key={i} position={[s.x, s.y, s.z]} rotation={[0, 0, 0]}>
          <planeGeometry args={[s.length, 0.04]} />
          <meshBasicMaterial
            color="#67e8f9"
            transparent
            opacity={0.3}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  );
}
