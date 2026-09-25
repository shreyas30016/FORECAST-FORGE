"use client";

import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { GridCellAPI } from "@/types/api";

interface WindFlowLayerProps {
  cells: GridCellAPI[];
  visible: boolean;
}

interface Particle {
  x: number;
  y: number;
  age: number;
  maxAge: number;
}

/**
 * Animated wind flow visualization using Canvas particles.
 * Every particle trajectory derives from actual forecast wind_speed + wind_direction.
 * No random wind directions are generated. If wind data is missing, no particles are drawn.
 */
export function WindFlowLayer({ cells, visible }: WindFlowLayerProps) {
  const map = useMap();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayRef = useRef<L.ImageOverlay | null>(null);
  const animFrameRef = useRef<number>(0);
  const particlesRef = useRef<Particle[]>([]);

  useEffect(() => {
    if (!visible || cells.length === 0) {
      if (overlayRef.current) {
        map.removeLayer(overlayRef.current);
        overlayRef.current = null;
      }
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
        animFrameRef.current = 0;
      }
      return;
    }

    // Filter only cells with valid wind data
    const windCells = cells.filter(
      (c) => typeof c.wind_speed === "number" && typeof c.wind_direction === "number" && c.wind_speed > 0
    );

    if (windCells.length === 0) {
      return;
    }

    // Compute bounds
    let minLat = Infinity, maxLat = -Infinity, minLon = Infinity, maxLon = -Infinity;
    for (const cell of windCells) {
      const [[s, w], [n, e]] = cell.bounds;
      if (s < minLat) minLat = s;
      if (n > maxLat) maxLat = n;
      if (w < minLon) minLon = w;
      if (e > maxLon) maxLon = e;
    }

    const canvasW = 400;
    const canvasH = Math.round(canvasW * ((maxLat - minLat) / Math.max(maxLon - minLon, 0.01)));
    const canvas = document.createElement("canvas");
    canvas.width = canvasW;
    canvas.height = canvasH || 400;
    canvasRef.current = canvas;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Build wind field lookup - normalized to canvas space
    function getWindAt(cx: number, cy: number): { u: number; v: number; speed: number } | null {
      // Convert canvas coords to lat/lon
      const lon = minLon + (cx / canvasW) * (maxLon - minLon);
      const lat = maxLat - (cy / canvas.height) * (maxLat - minLat);

      // Find nearest cell
      let nearest: GridCellAPI | null = null;
      let bestDist = Infinity;
      for (const cell of windCells) {
        const d = Math.abs(cell.latitude - lat) + Math.abs(cell.longitude - lon);
        if (d < bestDist) {
          bestDist = d;
          nearest = cell;
        }
      }

      if (!nearest || bestDist > 0.5 || nearest.wind_speed === null || nearest.wind_speed === undefined || nearest.wind_direction === null || nearest.wind_direction === undefined) {
        return null;
      }

      // Convert meteorological direction to u,v
      const speed = nearest.wind_speed;
      const dirRad = ((nearest.wind_direction + 180) % 360) * (Math.PI / 180);
      const u = speed * Math.sin(dirRad);
      const v = speed * Math.cos(dirRad);

      return { u, v, speed };
    }

    // Initialize particles
    const particleCount = prefersReduced ? 0 : Math.min(windCells.length * 8, 200);
    const particles: Particle[] = [];
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * canvasW,
        y: Math.random() * canvas.height,
        age: Math.floor(Math.random() * 60),
        maxAge: 40 + Math.floor(Math.random() * 40),
      });
    }
    particlesRef.current = particles;

    // Color by speed
    function speedColor(speed: number): string {
      if (speed < 15) return "rgba(56, 189, 248, 0.7)";
      if (speed < 30) return "rgba(16, 185, 129, 0.7)";
      if (speed < 50) return "rgba(245, 158, 11, 0.7)";
      return "rgba(239, 68, 68, 0.7)";
    }

    const bounds: L.LatLngBoundsExpression = [[minLat, minLon], [maxLat, maxLon]];

    if (overlayRef.current) {
      map.removeLayer(overlayRef.current);
    }

    // Draw initial static
    ctx.clearRect(0, 0, canvasW, canvas.height);
    const dataUrl = canvas.toDataURL();
    overlayRef.current = L.imageOverlay(dataUrl, bounds, { opacity: 1, interactive: false });
    overlayRef.current.addTo(map);

    if (prefersReduced) {
      // Static arrows only
      ctx.clearRect(0, 0, canvasW, canvas.height);
      for (const cell of windCells) {
        const cx = ((cell.longitude - minLon) / (maxLon - minLon)) * canvasW;
        const cy = ((maxLat - cell.latitude) / (maxLat - minLat)) * canvas.height;
        const wind = getWindAt(cx, cy);
        if (!wind) continue;

        const len = Math.min(wind.speed * 0.5, 15);
        const angle = Math.atan2(wind.v, wind.u);

        ctx.strokeStyle = speedColor(wind.speed);
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(angle) * len, cy - Math.sin(angle) * len);
        ctx.stroke();
      }
      const staticUrl = canvas.toDataURL();
      (overlayRef.current as L.ImageOverlay & { setUrl: (url: string) => void }).setUrl(staticUrl);
      return;
    }

    // Animation loop
    function animate() {
      if (!ctx) return;

      // Fade trail
      ctx.fillStyle = "rgba(0, 0, 0, 0.08)";
      ctx.fillRect(0, 0, canvasW, canvas.height);

      for (const p of particles) {
        const wind = getWindAt(p.x, p.y);

        if (wind) {
          // Scale movement: convert km/h wind to pixel displacement
          const scale = 0.15;
          const dx = wind.u * scale;
          const dy = -wind.v * scale; // canvas y is inverted

          const oldX = p.x;
          const oldY = p.y;
          p.x += dx;
          p.y += dy;

          // Draw trail
          const alpha = Math.max(0, 1 - p.age / p.maxAge) * 0.8;
          ctx.strokeStyle = speedColor(wind.speed).replace(/[\d.]+\)$/, `${alpha})`);
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.moveTo(oldX, oldY);
          ctx.lineTo(p.x, p.y);
          ctx.stroke();
        }

        p.age++;
        if (p.age > p.maxAge || p.x < 0 || p.x > canvasW || p.y < 0 || p.y > canvas.height) {
          p.x = Math.random() * canvasW;
          p.y = Math.random() * canvas.height;
          p.age = 0;
          p.maxAge = 40 + Math.floor(Math.random() * 40);
        }
      }

      const frameUrl = canvas.toDataURL();
      if (overlayRef.current) {
        (overlayRef.current as L.ImageOverlay & { setUrl: (url: string) => void }).setUrl(frameUrl);
      }
      animFrameRef.current = requestAnimationFrame(animate);
    }

    animFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
        animFrameRef.current = 0;
      }
      if (overlayRef.current) {
        map.removeLayer(overlayRef.current);
        overlayRef.current = null;
      }
    };
  }, [cells, visible, map]);

  return null;
}

export default WindFlowLayer;
