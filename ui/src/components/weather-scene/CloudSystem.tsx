"use client";

import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { WeatherCondition } from "@/types/weather";

interface CloudSystemProps {
  condition: WeatherCondition;
  cloudCover: number; // 0-100%
  windSpeed: number; // km/h
}

interface CloudPuff {
  offset: [number, number, number];
  scale: [number, number, number];
}

interface CloudCluster {
  x: number;
  y: number;
  z: number;
  speedMultiplier: number;
  puffs: CloudPuff[];
}

export function CloudSystem({ condition, cloudCover, windSpeed }: CloudSystemProps) {
  const groupRef = useRef<THREE.Group>(null);

  // Cloud tint based on condition
  const cloudColor = useMemo(() => {
    switch (condition) {
      case "STORM":
        return new THREE.Color("#1e293b"); // Deep stormy dark slate
      case "RAIN":
      case "HEAVY_RAIN":
        return new THREE.Color("#334155"); // Dark rain cloud
      case "CLOUDY":
        return new THREE.Color("#64748b"); // Neutral overcast
      case "PARTLY_CLOUDY":
      default:
        return new THREE.Color("#cbd5e1"); // Soft daylight cloud
    }
  }, [condition]);

  // Determine number of cloud clusters based on real cloudCover
  const clusterCount = useMemo(() => {
    if (cloudCover < 15) return 2;
    if (cloudCover < 40) return 4;
    if (cloudCover < 75) return 6;
    return 9;
  }, [cloudCover]);

  // Pre-generate cluster configurations
  const clusters: CloudCluster[] = useMemo(() => {
    const list: CloudCluster[] = [];
    for (let i = 0; i < clusterCount; i++) {
      const puffs: CloudPuff[] = [
        { offset: [0, 0, 0], scale: [1.8, 1.1, 1.2] },
        { offset: [1.2, 0.2, 0.1], scale: [1.4, 0.9, 1.0] },
        { offset: [-1.1, -0.1, -0.1], scale: [1.3, 0.8, 1.0] },
        { offset: [0.5, 0.6, 0.2], scale: [1.1, 0.9, 0.9] },
        { offset: [-0.6, 0.5, -0.2], scale: [1.0, 0.8, 0.8] },
      ];

      list.push({
        x: (i - clusterCount / 2) * 5 + (Math.sin(i * 3) * 2),
        y: 1.5 + (i % 3) * 1.2 + Math.cos(i) * 0.5,
        z: -8 - (i % 4) * 2.5,
        speedMultiplier: 0.6 + (i % 3) * 0.3,
        puffs,
      });
    }
    return list;
  }, [clusterCount]);

  // Drift clouds across screen driven by real wind speed
  useFrame((_, delta) => {
    if (!groupRef.current) return;
    const baseSpeed = Math.max(0.1, windSpeed * 0.015);

    groupRef.current.children.forEach((child, i) => {
      const c = clusters[i];
      if (!c) return;
      child.position.x += baseSpeed * c.speedMultiplier * delta * 2;

      // Wrap around seamlessly
      if (child.position.x > 22) {
        child.position.x = -22;
      }
    });
  });

  if (cloudCover < 5) return null;

  return (
    <group ref={groupRef}>
      {clusters.map((c, i) => (
        <group key={i} position={[c.x, c.y, c.z]}>
          {c.puffs.map((p, pi) => (
            <mesh key={pi} position={p.offset} scale={p.scale}>
              <sphereGeometry args={[1, 16, 16]} />
              <meshStandardMaterial
                color={cloudColor}
                transparent
                opacity={condition === "STORM" ? 0.85 : 0.65}
                roughness={0.9}
                depthWrite={false}
              />
            </mesh>
          ))}
        </group>
      ))}
    </group>
  );
}
