"use client";

import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { GridCellAPI } from "@/types/api";

interface CloudCoverLayerProps {
  cells: GridCellAPI[];
  visible: boolean;
}

/**
 * Forecast cloud-cover visualization layer.
 * Renders cloud_cover (%) as white opacity fields on a Leaflet canvas overlay.
 * NOT satellite imagery. This is an animated visualization of forecast cloud-cover field.
 */
export function CloudCoverLayer({ cells, visible }: CloudCoverLayerProps) {
  const map = useMap();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayRef = useRef<L.ImageOverlay | null>(null);
  const animFrameRef = useRef<number>(0);
  const timeRef = useRef<number>(0);

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

    // Determine bounds from cells
    let minLat = Infinity, maxLat = -Infinity, minLon = Infinity, maxLon = -Infinity;
    for (const cell of cells) {
      const [[s, w], [n, e]] = cell.bounds;
      if (s < minLat) minLat = s;
      if (n > maxLat) maxLat = n;
      if (w < minLon) minLon = w;
      if (e > maxLon) maxLon = e;
    }

    const canvas = document.createElement("canvas");
    const cellsPerRow = Math.round((maxLon - minLon) / 0.25) || 1;
    const cellsPerCol = Math.round((maxLat - minLat) / 0.25) || 1;
    // Upscale for smoothness
    const scale = 16;
    canvas.width = cellsPerRow * scale;
    canvas.height = cellsPerCol * scale;
    canvasRef.current = canvas;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Check reduced motion
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function drawClouds(t: number) {
      if (!ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      for (const cell of cells) {
        // cloud_cover comes from the grid as cell.value when variable=cloud_cover
        // But we receive it alongside other data - use value field
        const cloudPct = cell.value;
        if (cloudPct === null || cloudPct === undefined || cloudPct <= 0) continue;

        const [[s, w], [n, e]] = cell.bounds;
        const x = ((w - minLon) / (maxLon - minLon)) * canvas.width;
        const y = ((maxLat - n) / (maxLat - minLat)) * canvas.height;
        const cw = ((e - w) / (maxLon - minLon)) * canvas.width;
        const ch = ((n - s) / (maxLat - minLat)) * canvas.height;

        // Cloud opacity proportional to cloud cover percentage
        const baseAlpha = Math.min(cloudPct / 100, 1.0) * 0.65;
        // Subtle breathing animation if motion allowed
        const breathe = prefersReduced ? 0 : Math.sin(t * 0.0008 + x * 0.01) * 0.05;
        const alpha = Math.max(0, Math.min(1, baseAlpha + breathe));

        // Draw soft cloud fill
        ctx.fillStyle = `rgba(220, 230, 240, ${alpha})`;
        ctx.beginPath();
        // Slightly rounded cloud blobs
        const rx = cw * 0.4;
        const ry = ch * 0.4;
        const cx = x + cw / 2;
        const cy = y + ch / 2;
        ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
        ctx.fill();

        // Secondary wisp
        if (cloudPct > 30) {
          const wispAlpha = alpha * 0.5;
          ctx.fillStyle = `rgba(200, 215, 230, ${wispAlpha})`;
          ctx.beginPath();
          ctx.ellipse(cx + rx * 0.3, cy - ry * 0.2, rx * 0.7, ry * 0.6, 0, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }

    // Initial draw
    drawClouds(0);

    const dataUrl = canvas.toDataURL();
    const bounds: L.LatLngBoundsExpression = [[minLat, minLon], [maxLat, maxLon]];

    if (overlayRef.current) {
      map.removeLayer(overlayRef.current);
    }
    overlayRef.current = L.imageOverlay(dataUrl, bounds, { opacity: 1, interactive: false });
    overlayRef.current.addTo(map);

    // Animation loop
    if (!prefersReduced) {
      function animate(ts: number) {
        timeRef.current = ts;
        drawClouds(ts);
        const newUrl = canvas.toDataURL();
        if (overlayRef.current) {
          (overlayRef.current as L.ImageOverlay & { setUrl: (url: string) => void }).setUrl(newUrl);
        }
        animFrameRef.current = requestAnimationFrame(animate);
      }
      animFrameRef.current = requestAnimationFrame(animate);
    }

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

export default CloudCoverLayer;
