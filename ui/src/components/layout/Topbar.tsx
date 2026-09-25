"use client";

import { useState, useEffect, useSyncExternalStore } from "react";
import { format } from "date-fns";
import {
  MapPin,
  Globe,
  Activity,
  ChevronDown,
  Crosshair,
  Check,
  ArrowLeft,
  X,
  Search,
  Navigation,
  Loader2,
} from "lucide-react";
import { useLocation } from "@/context/LocationContext";

const emptySubscribe = () => () => {};

interface GeocodingResult {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  country?: string;
  country_code?: string;
  admin1?: string;
  timezone?: string;
}

export function Topbar() {
  const isMounted = useSyncExternalStore(emptySubscribe, () => true, () => false);
  const { location, setLocation, setCoordinates, presets } = useLocation();
  const [time, setTime] = useState<Date | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [customInputOpen, setCustomInputOpen] = useState(false);
  const [latInput, setLatInput] = useState(location.latitude.toString());
  const [lonInput, setLonInput] = useState(location.longitude.toString());

  // Search & Geocoding State
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<GeocodingResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Auto-detect GPS State
  const [isDetectingLocation, setIsDetectingLocation] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Debounced search for city / location names via Open-Meteo Geocoding
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!searchQuery || searchQuery.trim().length < 2) {
        setSearchResults([]);
        setIsSearching(false);
        return;
      }

      setIsSearching(true);
      try {
        const res = await fetch(
          `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(
            searchQuery.trim()
          )}&count=6&language=en&format=json`
        );
        if (res.ok) {
          const data = await res.json();
          setSearchResults(data.results || []);
        } else {
          setSearchResults([]);
        }
      } catch {
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 280);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleApplyCoordinates = (e: React.FormEvent) => {
    e.preventDefault();
    const lat = parseFloat(latInput);
    const lon = parseFloat(lonInput);
    if (!isNaN(lat) && !isNaN(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
      setCoordinates(lat, lon);
      setCustomInputOpen(false);
      setDropdownOpen(false);
    }
  };

  const handleSelectSearchResult = (item: GeocodingResult) => {
    const regionName = item.admin1
      ? `${item.admin1}${item.country ? `, ${item.country}` : ""}`
      : item.country || "Custom Location";

    setLocation({
      name: item.name,
      latitude: parseFloat(item.latitude.toFixed(4)),
      longitude: parseFloat(item.longitude.toFixed(4)),
      region: regionName,
    });
    setLatInput(item.latitude.toFixed(4));
    setLonInput(item.longitude.toFixed(4));
    setSearchQuery("");
    setSearchResults([]);
    setDropdownOpen(false);
  };

  const handleDetectCurrentLocation = () => {
    setGeoError(null);
    if (typeof window === "undefined" || !navigator.geolocation) {
      setGeoError("Geolocation is not supported by your browser.");
      return;
    }

    setIsDetectingLocation(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = parseFloat(pos.coords.latitude.toFixed(4));
        const lon = parseFloat(pos.coords.longitude.toFixed(4));
        setLatInput(lat.toString());
        setLonInput(lon.toString());

        try {
          const revRes = await fetch(
            `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}&localityLanguage=en`
          );
          if (revRes.ok) {
            const revData = await revRes.json();
            const cityName =
              revData.city ||
              revData.locality ||
              revData.principalSubdivision ||
              "Current Location";
            const stateName = revData.principalSubdivision || revData.countryName || "";
            setLocation({
              name: cityName,
              latitude: lat,
              longitude: lon,
              region: stateName ? `${stateName}, India` : "Auto-Detected Location",
            });
          } else {
            setCoordinates(lat, lon, `Location (${lat.toFixed(2)}, ${lon.toFixed(2)})`);
          }
        } catch {
          setCoordinates(lat, lon, `Location (${lat.toFixed(2)}, ${lon.toFixed(2)})`);
        } finally {
          setIsDetectingLocation(false);
          setDropdownOpen(false);
        }
      },
      (err) => {
        setIsDetectingLocation(false);
        if (err.code === 1) {
          setGeoError("Location access denied. Please grant browser location permission.");
        } else if (err.code === 2) {
          setGeoError("Location unavailable. Please verify GPS or network.");
        } else {
          setGeoError("Location detection timed out.");
        }
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  return (
    <header className="h-16 bg-panel/75 backdrop-blur-md border-b border-border-subtle flex items-center justify-between px-3 sm:px-5 lg:px-6 shrink-0 z-30">
      
      {/* Location Selector & Station Context */}
      <div className="flex items-center gap-3 relative">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              const next = !dropdownOpen;
              setDropdownOpen(next);
              if (next) {
                setLatInput(location.latitude.toString());
                setLonInput(location.longitude.toString());
                setSearchQuery("");
                setSearchResults([]);
                setGeoError(null);
              }
            }}
            className="flex items-center gap-2.5 bg-background/80 hover:bg-panel-hover border border-border-subtle hover:border-ensemble/40 px-3.5 py-1.5 rounded-lg text-sm text-text-primary transition-all duration-200 shadow-sm focus-visible:ring-2 focus-visible:ring-ensemble/50"
            aria-expanded={dropdownOpen}
            aria-label="Select meteorological station"
          >
            <div className="w-5 h-5 rounded-md bg-ensemble/15 flex items-center justify-center text-ensemble shrink-0">
              <MapPin className="h-3.5 w-3.5" />
            </div>
            <div className="flex items-center gap-2 text-left">
              <span className="font-bold text-white tracking-tight">{location.name}</span>
              <span className="hidden sm:inline text-[11px] font-mono text-text-muted">
                [{location.latitude.toFixed(4)}°N, {location.longitude.toFixed(4)}°E]
              </span>
            </div>
            <ChevronDown className={`h-3.5 w-3.5 text-text-secondary transition-transform duration-200 ${dropdownOpen ? "rotate-180" : ""}`} />
          </button>
        </div>

        {/* Backdrop for click-outside */}
        {dropdownOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-xs"
            onClick={() => setDropdownOpen(false)}
            aria-hidden="true"
          />
        )}

        {/* Dropdown Menu */}
        {dropdownOpen && (
          <div className="absolute top-12 left-0 w-88 sm:w-96 max-w-[calc(100vw-2rem)] bg-panel-elevated/95 backdrop-blur-2xl border border-border-subtle shadow-2xl rounded-2xl p-3 z-50 text-xs font-sans animate-in fade-in zoom-in-95 duration-150">
            
            {/* Header with Back and Close Buttons */}
            <div className="flex items-center justify-between px-1 pb-2 mb-2.5 border-b border-border-subtle">
              <button
                type="button"
                onClick={() => setDropdownOpen(false)}
                className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary hover:text-white px-2 py-1 rounded-md hover:bg-white/10 transition-colors"
                aria-label="Back"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back</span>
              </button>
              <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted font-bold">
                Select Station / Location
              </span>
              <button
                type="button"
                onClick={() => setDropdownOpen(false)}
                className="p-1.5 rounded-md text-text-muted hover:text-white hover:bg-white/10 transition-colors"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Direct Location Search Input */}
            <div className="relative mb-2.5">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
              <input
                type="text"
                placeholder="Type city or station (e.g. Pune, Shimla, Patna)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-background/90 border border-border-subtle pl-8.5 pr-8 py-2 rounded-xl text-xs text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-ensemble/60 focus:ring-1 focus:ring-ensemble/40 font-sans transition-all"
                autoFocus
              />
              {isSearching ? (
                <Loader2 className="w-3.5 h-3.5 absolute right-3 top-1/2 -translate-y-1/2 text-ensemble animate-spin" />
              ) : searchQuery ? (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-text-muted hover:text-white"
                >
                  <X className="w-3 h-3" />
                </button>
              ) : null}
            </div>

            {/* Geocoding Search Suggestions (if query present) */}
            {searchQuery.trim().length >= 2 && (
              <div className="mb-2.5 bg-background/80 rounded-xl p-1.5 border border-border-subtle max-h-48 overflow-y-auto space-y-1">
                <div className="px-2 py-1 text-[10px] font-mono uppercase text-text-muted tracking-wider flex items-center justify-between">
                  <span>Suggested Locations</span>
                  <span>Coordinates</span>
                </div>
                {searchResults.length === 0 && !isSearching && (
                  <div className="px-3 py-2 text-center text-text-muted text-xs">
                    No matching location found. Try custom coordinates below.
                  </div>
                )}
                {searchResults.map((item) => {
                  const isIndia = item.country_code === "IN" || item.country === "India";
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => handleSelectSearchResult(item)}
                      className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-left hover:bg-panel-hover transition-colors group"
                    >
                      <div className="flex flex-col min-w-0 pr-2">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-white truncate text-xs group-hover:text-ensemble transition-colors">
                            {item.name}
                          </span>
                          {isIndia && (
                            <span className="px-1.5 py-0.2 text-[9px] rounded bg-orange-500/20 text-orange-300 font-mono shrink-0">
                              India
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-text-muted truncate">
                          {item.admin1 ? `${item.admin1}, ` : ""}
                          {item.country || ""}
                        </span>
                      </div>
                      <span className="text-[11px] font-mono text-text-muted shrink-0">
                        {item.latitude.toFixed(2)}°, {item.longitude.toFixed(2)}°
                      </span>
                    </button>
                  );
                })}
              </div>
            )}

            {/* Auto-Detect Current Location (GPS) */}
            <div className="mb-2.5">
              <button
                type="button"
                onClick={handleDetectCurrentLocation}
                disabled={isDetectingLocation}
                className="w-full flex items-center justify-center gap-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-3 py-2 rounded-xl text-xs font-semibold transition-all shadow-xs disabled:opacity-50"
              >
                {isDetectingLocation ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Detecting GPS Location...</span>
                  </>
                ) : (
                  <>
                    <Navigation className="w-3.5 h-3.5" />
                    <span>Use Current Location (Auto-Detect GPS)</span>
                  </>
                )}
              </button>

              {geoError && (
                <div className="mt-1 px-2.5 py-1 bg-amber-500/15 border border-amber-500/30 text-amber-300 text-[10px] rounded-lg">
                  {geoError}
                </div>
              )}
            </div>

            {/* Station Presets Header */}
            <div className="px-2 py-1 text-text-muted uppercase text-[10px] font-mono tracking-wider border-b border-border-subtle mb-1.5 flex items-center justify-between">
              <span>Indian Station Presets</span>
              <span>Coordinates</span>
            </div>

            {/* Presets List (All Indian) */}
            <div className="max-h-44 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
              {presets.map((preset) => {
                const isSelected = preset.name === location.name;
                return (
                  <button
                    key={preset.name}
                    type="button"
                    onClick={() => {
                      setLocation(preset);
                      setLatInput(preset.latitude.toString());
                      setLonInput(preset.longitude.toString());
                      setDropdownOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg transition-all text-left ${
                      isSelected
                        ? "bg-ensemble/15 text-white font-bold border border-ensemble/40"
                        : "text-text-secondary hover:bg-panel-hover hover:text-white"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0 pr-2">
                      {isSelected ? (
                        <Check className="w-3.5 h-3.5 text-ensemble shrink-0" />
                      ) : (
                        <div className="w-3.5 h-3.5 shrink-0" />
                      )}
                      <div className="flex flex-col min-w-0">
                        <span className="font-medium text-white truncate text-xs">
                          {preset.name}
                        </span>
                        {preset.region && (
                          <span className="text-[10px] text-text-muted truncate">
                            {preset.region}
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="text-[11px] font-mono text-text-muted shrink-0">
                      {preset.latitude.toFixed(2)}°, {preset.longitude.toFixed(2)}°
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Custom Coordinate Sync */}
            <div className="border-t border-border-subtle mt-2 pt-2">
              <button
                type="button"
                onClick={() => {
                  const nextState = !customInputOpen;
                  setCustomInputOpen(nextState);
                  if (nextState) {
                    setLatInput(location.latitude.toString());
                    setLonInput(location.longitude.toString());
                  }
                }}
                className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-text-secondary hover:text-white hover:bg-panel-hover transition-colors"
              >
                <span className="flex items-center gap-2 font-medium text-xs">
                  <Crosshair className="w-3.5 h-3.5 text-ensemble" />
                  Custom Coordinate Sync
                </span>
                <span className="text-[10px] font-mono uppercase text-text-muted">
                  {customInputOpen ? "Hide" : "Enter"}
                </span>
              </button>

              {customInputOpen && (
                <form
                  onSubmit={handleApplyCoordinates}
                  className="p-2.5 space-y-2.5 bg-background/60 rounded-xl mt-1.5 border border-border-subtle"
                >
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] font-mono text-text-muted block mb-1">
                        Latitude (°N)
                      </label>
                      <input
                        type="number"
                        step="0.0001"
                        min="-90"
                        max="90"
                        value={latInput}
                        onChange={(e) => setLatInput(e.target.value)}
                        className="w-full bg-background border border-border-subtle px-2.5 py-1.5 rounded-md text-text-primary text-xs focus:outline-none focus:border-ensemble font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-mono text-text-muted block mb-1">
                        Longitude (°E)
                      </label>
                      <input
                        type="number"
                        step="0.0001"
                        min="-180"
                        max="180"
                        value={lonInput}
                        onChange={(e) => setLonInput(e.target.value)}
                        className="w-full bg-background border border-border-subtle px-2.5 py-1.5 rounded-md text-text-primary text-xs focus:outline-none focus:border-ensemble font-mono"
                      />
                    </div>
                  </div>
                  <button
                    type="submit"
                    className="w-full bg-ensemble text-slate-950 font-bold py-1.5 px-3 rounded-md text-xs hover:bg-ensemble/90 transition-all shadow-md uppercase font-mono tracking-wider cursor-pointer"
                  >
                    Sync Coordinates
                  </button>
                </form>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Global Telemetry & Clock */}
      <div className="flex items-center gap-3 sm:gap-5">
        <div className="hidden sm:flex items-center gap-2 text-xs font-mono text-text-secondary bg-background/60 px-3 py-1.5 rounded-lg border border-border-subtle">
          <Activity className="w-3.5 h-3.5 text-status-available animate-pulse" />
          <span>API: <strong className="text-status-available font-semibold">LIVE</strong></span>
        </div>
        
        <div className="flex items-center gap-2 bg-background/80 px-3 py-1.5 border border-border-subtle rounded-lg shadow-inner">
          <Globe className="w-3.5 h-3.5 text-text-muted" />
          <span className="text-xs sm:text-sm font-mono font-medium tracking-wider text-text-primary" suppressHydrationWarning>
            {isMounted && time ? format(time, "HH:mm:ss 'UTC'") : "--:--:-- UTC"}
          </span>
        </div>
      </div>
    </header>
  );
}
