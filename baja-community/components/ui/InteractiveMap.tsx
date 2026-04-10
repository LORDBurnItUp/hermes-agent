"use client";

import { useEffect, useState } from "react";
import { getAllCoordinates } from "@/lib/data";
import { MEXICO_CENTER, DEFAULT_ZOOM } from "@/lib/constants";

interface InteractiveMapProps {
  className?: string;
  filterType?: string;
}

export function InteractiveMap({
  className = "",
  filterType,
}: InteractiveMapProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div
        className={`rounded-2xl bg-[var(--color-bg-secondary)] flex items-center justify-center ${className}`}
      >
        <p className="text-[var(--color-text-muted)] text-sm">Loading map...</p>
      </div>
    );
  }

  return <MapInner className={className} filterType={filterType} />;
}

function MapInner({
  className,
  filterType,
}: {
  className: string;
  filterType?: string;
}) {
  const [MapComponents, setMapComponents] = useState<{
    MapContainer: typeof import("react-leaflet").MapContainer;
    TileLayer: typeof import("react-leaflet").TileLayer;
    Marker: typeof import("react-leaflet").Marker;
    Popup: typeof import("react-leaflet").Popup;
    L: typeof import("leaflet");
  } | null>(null);

  useEffect(() => {
    Promise.all([import("react-leaflet"), import("leaflet")]).then(
      ([reactLeaflet, leaflet]) => {
        setMapComponents({
          MapContainer: reactLeaflet.MapContainer,
          TileLayer: reactLeaflet.TileLayer,
          Marker: reactLeaflet.Marker,
          Popup: reactLeaflet.Popup,
          L: leaflet.default,
        });
      }
    );
  }, []);

  if (!MapComponents) {
    return (
      <div
        className={`rounded-2xl bg-[var(--color-bg-secondary)] flex items-center justify-center ${className}`}
      >
        <p className="text-[var(--color-text-muted)] text-sm">Loading map...</p>
      </div>
    );
  }

  const { MapContainer, TileLayer, Marker, Popup, L } = MapComponents;

  const allPoints = getAllCoordinates();
  const points = filterType
    ? allPoints.filter((p) => p.type === filterType)
    : allPoints;

  const markerColors: Record<string, string> = {
    charity: "#ef4444",
    professional: "#06b6d4",
    service: "#a855f7",
  };

  const createIcon = (type: string) => {
    const color = markerColors[type] || "#f97316";
    return L.divIcon({
      html: `<div style="background:${color};width:12px;height:12px;border-radius:50%;border:2px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);"></div>`,
      className: "",
      iconSize: [12, 12],
      iconAnchor: [6, 6],
    });
  };

  return (
    <>
      <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      />
      <MapContainer
        center={[MEXICO_CENTER.lat, MEXICO_CENTER.lng]}
        zoom={DEFAULT_ZOOM}
        className={`rounded-2xl ${className}`}
        style={{ minHeight: "400px" }}
        scrollWheelZoom={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        {points.map((point) => (
          <Marker
            key={`${point.type}-${point.id}`}
            position={[point.lat, point.lng]}
            icon={createIcon(point.type)}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-semibold">{point.label}</p>
                <p className="text-xs capitalize opacity-70">{point.type}</p>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </>
  );
}
