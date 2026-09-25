"use client";

import { useMemo } from "react";
import * as THREE from "three";
import { WeatherCondition } from "@/types/weather";

interface SkyMeshProps {
  condition: WeatherCondition;
}

export function SkyMesh({ condition }: SkyMeshProps) {
  // Generate atmospheric gradient colors based on weather state
  const colors = useMemo(() => {
    switch (condition) {
      case "SUNNY":
        return {
          top: new THREE.Color("#0c2444"),
          bottom: new THREE.Color("#18426d"),
        };
      case "PARTLY_CLOUDY":
        return {
          top: new THREE.Color("#091b33"),
          bottom: new THREE.Color("#143557"),
        };
      case "CLOUDY":
        return {
          top: new THREE.Color("#071526"),
          bottom: new THREE.Color("#0e243d"),
        };
      case "RAIN":
      case "HEAVY_RAIN":
        return {
          top: new THREE.Color("#040d1a"),
          bottom: new THREE.Color("#091b2e"),
        };
      case "STORM":
        return {
          top: new THREE.Color("#030812"),
          bottom: new THREE.Color("#07111f"),
        };
      case "FOG":
        return {
          top: new THREE.Color("#0e1e30"),
          bottom: new THREE.Color("#162c44"),
        };
      case "NIGHT":
      default:
        return {
          top: new THREE.Color("#020712"),
          bottom: new THREE.Color("#061122"),
        };
    }
  }, [condition]);

  return (
    <mesh position={[0, 0, -25]}>
      <planeGeometry args={[100, 60]} />
      <meshBasicMaterial
        color={colors.bottom}
        depthWrite={false}
      />
    </mesh>
  );
}
