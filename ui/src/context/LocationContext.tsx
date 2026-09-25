"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";

export interface LocationItem {
  name: string;
  latitude: number;
  longitude: number;
  region?: string;
}

export const PRESET_LOCATIONS: LocationItem[] = [
  { name: "Mumbai", latitude: 19.0760, longitude: 72.8777, region: "Maharashtra (Default)" },
  { name: "New Delhi", latitude: 28.6139, longitude: 77.2090, region: "Delhi NCR" },
  { name: "Bengaluru", latitude: 12.9716, longitude: 77.5946, region: "Karnataka" },
  { name: "Chennai", latitude: 13.0827, longitude: 80.2707, region: "Tamil Nadu" },
  { name: "Kolkata", latitude: 22.5726, longitude: 88.3639, region: "West Bengal" },
  { name: "Hyderabad", latitude: 17.3850, longitude: 78.4867, region: "Telangana" },
  { name: "Ahmedabad", latitude: 23.0225, longitude: 72.5714, region: "Gujarat" },
  { name: "Pune", latitude: 18.5204, longitude: 73.8567, region: "Maharashtra" },
  { name: "Jaipur", latitude: 26.9124, longitude: 75.7873, region: "Rajasthan" },
  { name: "Srinagar", latitude: 34.0837, longitude: 74.7973, region: "Jammu & Kashmir" },
  { name: "Guwahati", latitude: 26.1445, longitude: 91.7362, region: "Assam" },
  { name: "Kochi", latitude: 9.9312, longitude: 76.2673, region: "Kerala" },
];

export interface ActiveForecastContext {
  valid_time: string;
  lead_time_hours: number;
  variable: string;
  trace_id?: string;
}

interface LocationContextType {
  location: LocationItem;
  setLocation: (loc: LocationItem) => void;
  setCoordinates: (lat: number, lon: number, name?: string) => void;
  presets: LocationItem[];
  activeForecast: ActiveForecastContext | null;
  setActiveForecast: (ctx: ActiveForecastContext | null) => void;
}

const LocationContext = createContext<LocationContextType | undefined>(undefined);

export function LocationProvider({ children }: { children: ReactNode }) {
  // Initial development/default station is Mumbai as specified
  const [location, setLocation] = useState<LocationItem>(PRESET_LOCATIONS[0]);
  const [activeForecast, setActiveForecast] = useState<ActiveForecastContext | null>(null);

  const setCoordinates = (lat: number, lon: number, name?: string) => {
    // Check if close to a preset
    const match = PRESET_LOCATIONS.find(
      (p) => Math.abs(p.latitude - lat) < 0.05 && Math.abs(p.longitude - lon) < 0.05
    );

    setLocation({
      name: name || (match ? match.name : `Station (${lat.toFixed(2)}, ${lon.toFixed(2)})`),
      latitude: parseFloat(lat.toFixed(4)),
      longitude: parseFloat(lon.toFixed(4)),
      region: match ? match.region : "Custom Coordinates",
    });
  };

  return (
    <LocationContext.Provider value={{ location, setLocation, setCoordinates, presets: PRESET_LOCATIONS, activeForecast, setActiveForecast }}>
      {children}
    </LocationContext.Provider>
  );
}

export function useLocation() {
  const context = useContext(LocationContext);
  if (!context) {
    throw new Error("useLocation must be used within a LocationProvider");
  }
  return context;
}
