"use client";

import { Canvas } from "@react-three/fiber";
import { NormalizedWeatherState } from "@/types/weather";
import { SkyMesh } from "./SkyMesh";
import { SunMoon } from "./SunMoon";
import { CloudSystem } from "./CloudSystem";
import { RainSystem } from "./RainSystem";
import { WindStreaks } from "./WindStreaks";
import { LightingController } from "./LightingController";

interface WeatherSceneCanvasProps {
  weather: NormalizedWeatherState;
}

export default function WeatherSceneCanvas({ weather }: WeatherSceneCanvasProps) {
  return (
    <Canvas
      camera={{ position: [0, 1.5, 6], fov: 60 }}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      className="w-full h-full pointer-events-none"
    >
      {/* Dynamic Lighting */}
      <LightingController condition={weather.condition} isDay={weather.isDay} />

      {/* Atmospheric Sky Dome Backdrop */}
      <SkyMesh condition={weather.condition} />

      {/* 3D Sun / Moon */}
      <SunMoon condition={weather.condition} isDay={weather.isDay} />

      {/* Procedural Layered Clouds */}
      <CloudSystem
        condition={weather.condition}
        cloudCover={weather.cloudCover}
        windSpeed={weather.windSpeed}
      />

      {/* Dynamic Precipitation Drops */}
      <RainSystem
        precipitation={weather.precipitation}
        windSpeed={weather.windSpeed}
      />

      {/* Wind Aerodynamic Flow Streaks */}
      <WindStreaks windSpeed={weather.windSpeed} />
    </Canvas>
  );
}
