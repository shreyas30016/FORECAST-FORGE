"use client";

import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { GridCellAPI } from "@/types/api";

interface PrecipitationLayerProps {
  cells: GridCellAPI[];
  visible: boolean;
}

interface RainDrop {
  x: number;
  y: number;
  speed: number;
  length: number;
  opacity: number;
}

/**
 * Animated precipitation visualization layer.
 * Rain drop density and speed proportional to actual forecast precipitation values.
 * Null/missing precipitation means no particles are rendered in that cell.
 * This is NOT radar imagery.
 */
export function PrecipitationLayer({ cells, visible }: PrecipitationLayerProps) {
  const map = useMap();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayRef = useRef<L.ImageOverlay | null>(null);
  const animFrameRef = useRef<number>(0);
  const dropsRef = useRef<RainDrop[]>([]);

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

    // Filter only cells with real precipitation > threshold
    const precipCells = cells.filter(
      (c) => c.value !== null && c.value !== undefined && c.value > 0.05
    );

    // Compute bounds from all cells (for the base overlay size)
    let minLat = Infinity, maxLat = -Infinity, minLon = Infinity, maxLon = -Infinity;
    for (const cell of cells) {
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

    // Create rain drops for cells with precipitation
    const drops: RainDrop[] = [];

    if (!prefersReduced) {
      for (const cell of precipCells) {
        const precip = cell.value!;
        // Number of drops proportional to intensity
        const dropCount = Math.min(Math.ceil(precip * 3), 20);
        const [[s, w], [n, e]] = cell.bounds;

        for (let i = 0; i < dropCount; i++) {
          const cx = ((w + Math.random() * (e - w) - minLon) / (maxLon - minLon)) * canvasW;
          const cy = ((maxLat - (s + Math.random() * (n - s))) / (maxLat - minLat)) * canvas.height;

          drops.push({
            x: cx,
            y: cy,
            speed: 1.5 + precip * 0.3,
            length: 3 + Math.min(precip, 10),
            opacity: Math.min(0.3 + precip * 0.04, 0.8),
          });
        }
      }
    }
    dropsRef.current = drops;

    const bounds: L.LatLngBoundsExpression = [[minLat, minLon], [maxLat, maxLon]];

    if (overlayRef.current) {
      map.removeLayer(overlayRef.current);
    }

    // Initial render
    ctx.clearRect(0, 0, canvasW, canvas.height);

    // Static precipitation intensity field (always shown)
    for (const cell of cells) {
      const precip = cell.value;
      if (precip === null || precip === undefined) continue;

      const [[s, w], [n, e]] = cell.bounds;
      const x = ((w - minLon) / (maxLon - minLon)) * canvasW;
      const y = ((maxLat - n) / (maxLat - minLat)) * canvas.height;
      const cw = ((e - w) / (maxLon - minLon)) * canvasW;
      const ch = ((n - s) / (maxLat - minLat)) * canvas.height;

      if (precip <= 0.05) {
        // Dry - skip
        continue;
      }

      // Color intensity based on precip amount
      let r = 56, g = 189, b = 248, alpha = 0.15;
      if (precip < 1.0) { r = 56; g = 189; b = 248; alpha = 0.2; }
      else if (precip < 5.0) { r = 2; g = 132; b = 199; alpha = 0.3; }
      else if (precip < 15.0) { r = 79; g = 70; b = 229; alpha = 0.4; }
      else { r = 147; g = 51; b = 234; alpha = 0.5; }

      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
      ctx.fillRect(x, y, cw, ch);
    }

    const dataUrl = canvas.toDataURL();
    overlayRef.current = L.imageOverlay(dataUrl, bounds, { opacity: 1, interactive: false });
    overlayRef.current.addTo(map);

    if (prefersReduced || drops.length === 0) {
      return;
    }

    // Animation loop for rain drops
    function animate() {
      if (!ctx) return;

      // Redraw base intensity
      ctx.clearRect(0, 0, canvasW, canvas.height);

      for (const cell of cells) {
        const precip = cell.value;
        if (precip === null || precip === undefined || precip <= 0.05) continue;

        const [[s, w], [n, e]] = cell.bounds;
        const x = ((w - minLon) / (maxLon - minLon)) * canvasW;
        const y = ((maxLat - n) / (maxLat - minLat)) * canvas.height;
        const cw = ((e - w) / (maxLon - minLon)) * canvasW;
        const ch = ((n - s) / (maxLat - minLat)) * canvas.height;

        let r = 56, g = 189, b = 248, alpha = 0.12;
        if (precip >= 15) { r = 147; g = 51; b = 234; alpha = 0.35; }
        else if (precip >= 5) { r = 79; g = 70; b = 229; alpha = 0.25; }
        else if (precip >= 1) { r = 2; g = 132; b = 199; alpha = 0.2; }

        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
        ctx.fillRect(x, y, cw, ch);
      }

      // Draw rain drops
      for (const drop of drops) {
        ctx.strokeStyle = `rgba(160, 200, 255, ${drop.opacity})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(drop.x, drop.y);
        ctx.lineTo(drop.x - 0.3, drop.y + drop.length);
        ctx.stroke();

        drop.y += drop.speed;

        // Reset drop when it falls off
        if (drop.y > canvas.height) {
          drop.y = -drop.length;
          // Randomize x within precip zones
          drop.x = Math.random() * canvasW;
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

export default PrecipitationLayer;
