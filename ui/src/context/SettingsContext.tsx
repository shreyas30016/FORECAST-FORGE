"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";

export type TempUnit = "celsius" | "fahrenheit";
export type WindUnit = "kmh" | "ms" | "knots";
export type PressureUnit = "hpa" | "inhg";

interface SettingsContextType {
  tempUnit: TempUnit;
  setTempUnit: (unit: TempUnit) => void;
  windUnit: WindUnit;
  setWindUnit: (unit: WindUnit) => void;
  pressureUnit: PressureUnit;
  setPressureUnit: (unit: PressureUnit) => void;
  
  // Helpers
  tempSymbol: string;
  windSymbol: string;
  pressureSymbol: string;
  convertTemp: (celsius: number) => number;
  formatTemp: (celsius: number | null | undefined, precision?: number) => string;
  convertTempDelta: (celsiusDelta: number) => number;
  convertWind: (kmh: number) => number;
  formatWind: (kmh: number | null | undefined, precision?: number) => string;
  convertPressure: (hpa: number) => number;
  formatPressure: (hpa: number | null | undefined, precision?: number) => string;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

const STORAGE_KEYS = {
  TEMP: "forecast_forge_temp_unit",
  WIND: "forecast_forge_wind_unit",
  PRESSURE: "forecast_forge_pressure_unit",
};

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [tempUnit, setTempUnitState] = useState<TempUnit>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem(STORAGE_KEYS.TEMP) as TempUnit | null;
        if (saved === "celsius" || saved === "fahrenheit") return saved;
      } catch {
        // ignore
      }
    }
    return "celsius";
  });

  const [windUnit, setWindUnitState] = useState<WindUnit>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem(STORAGE_KEYS.WIND) as WindUnit | null;
        if (saved === "kmh" || saved === "ms" || saved === "knots") return saved;
      } catch {
        // ignore
      }
    }
    return "kmh";
  });

  const [pressureUnit, setPressureUnitState] = useState<PressureUnit>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem(STORAGE_KEYS.PRESSURE) as PressureUnit | null;
        if (saved === "hpa" || saved === "inhg") return saved;
      } catch {
        // ignore
      }
    }
    return "hpa";
  });

  const setTempUnit = (unit: TempUnit) => {
    setTempUnitState(unit);
    try {
      localStorage.setItem(STORAGE_KEYS.TEMP, unit);
    } catch {
      // ignore
    }
  };

  const setWindUnit = (unit: WindUnit) => {
    setWindUnitState(unit);
    try {
      localStorage.setItem(STORAGE_KEYS.WIND, unit);
    } catch {
      // ignore
    }
  };

  const setPressureUnit = (unit: PressureUnit) => {
    setPressureUnitState(unit);
    try {
      localStorage.setItem(STORAGE_KEYS.PRESSURE, unit);
    } catch {
      // ignore
    }
  };

  const tempSymbol = tempUnit === "celsius" ? "°C" : "°F";
  const windSymbol = windUnit === "kmh" ? "km/h" : windUnit === "ms" ? "m/s" : "kt";
  const pressureSymbol = pressureUnit === "hpa" ? "hPa" : "inHg";

  const convertTemp = (celsius: number): number => {
    if (tempUnit === "fahrenheit") {
      return (celsius * 9) / 5 + 32;
    }
    return celsius;
  };

  const convertTempDelta = (celsiusDelta: number): number => {
    if (tempUnit === "fahrenheit") {
      return (celsiusDelta * 9) / 5;
    }
    return celsiusDelta;
  };

  const formatTemp = (celsius: number | null | undefined, precision = 1): string => {
    if (celsius === null || celsius === undefined || isNaN(celsius)) {
      return "—";
    }
    const val = convertTemp(celsius);
    return `${val.toFixed(precision)}${tempSymbol}`;
  };

  const convertWind = (kmh: number): number => {
    if (windUnit === "ms") {
      return kmh / 3.6;
    }
    if (windUnit === "knots") {
      return kmh / 1.852;
    }
    return kmh;
  };

  const formatWind = (kmh: number | null | undefined, precision = 1): string => {
    if (kmh === null || kmh === undefined || isNaN(kmh)) {
      return "—";
    }
    const val = convertWind(kmh);
    return `${val.toFixed(precision)} ${windSymbol}`;
  };

  const convertPressure = (hpa: number): number => {
    if (pressureUnit === "inhg") {
      return hpa * 0.02953;
    }
    return hpa;
  };

  const formatPressure = (hpa: number | null | undefined, precision = 1): string => {
    if (hpa === null || hpa === undefined || isNaN(hpa)) {
      return "—";
    }
    const val = convertPressure(hpa);
    return `${val.toFixed(precision)} ${pressureSymbol}`;
  };

  return (
    <SettingsContext.Provider
      value={{
        tempUnit,
        setTempUnit,
        windUnit,
        setWindUnit,
        pressureUnit,
        setPressureUnit,
        tempSymbol,
        windSymbol,
        pressureSymbol,
        convertTemp,
        formatTemp,
        convertTempDelta,
        convertWind,
        formatWind,
        convertPressure,
        formatPressure,
      }}
    >
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error("useSettings must be used within a SettingsProvider");
  }
  return context;
}
