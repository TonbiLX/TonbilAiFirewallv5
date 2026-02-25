// --- Ajan: MUHAFIZ (THE GUARDIAN) ---
// SVG Dünya haritası: Saldırı çizgileri + Zoom in/out

import { memo, useMemo, useState, useCallback } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  Line,
  Marker,
  ZoomableGroup,
} from "react-simple-maps";

const GEO_URL = "/world-110m.json";

const PROT_COLORS: Record<string, string> = {
  syn_flood: "#ff4444",
  udp_flood: "#ff8c00",
  icmp_flood: "#ffd700",
  conn_limit: "#cc66ff",
  invalid_packet: "#999999",
};

const PROT_GLOW: Record<string, string> = {
  syn_flood: "rgba(255,68,68,0.4)",
  udp_flood: "rgba(255,140,0,0.4)",
  icmp_flood: "rgba(255,215,0,0.4)",
  conn_limit: "rgba(204,102,255,0.4)",
  invalid_packet: "rgba(153,153,153,0.3)",
};

interface Attack {
  ip: string;
  lat: number;
  lon: number;
  country: string;
  countryCode: string;
  city: string;
  type: string;
  packets: number;
  bytes: number;
}

interface Props {
  attacks: Attack[];
  target: { lat: number; lon: number; label: string };
}

function DdosWorldMapInner({ attacks, target }: Props) {
  const [zoom, setZoom] = useState(1);
  const [center, setCenter] = useState<[number, number]>([32, 39]);

  const handleZoomIn = useCallback(() => {
    setZoom((z) => Math.min(z * 1.5, 8));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((z) => Math.max(z / 1.5, 1));
  }, []);

  const handleReset = useCallback(() => {
    setZoom(1);
    setCenter([32, 39]);
  }, []);

  const uniqueAttacks = useMemo(() => {
    const seen = new Set<string>();
    return attacks
      .filter((a) => {
        const key = `${a.lat.toFixed(1)}_${a.lon.toFixed(1)}_${a.type}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .slice(0, 50);
  }, [attacks]);

  return (
    <div className="relative w-full h-full">
      {/* Zoom kontrolleri */}
      <div className="absolute top-3 right-3 z-10 flex flex-col gap-1">
        <button
          onClick={handleZoomIn}
          className="w-8 h-8 rounded bg-surface-700/80 border border-glass-border text-white hover:bg-surface-600 flex items-center justify-center text-lg font-bold backdrop-blur-sm transition-colors"
          title="Yakinlastir"
        >
          +
        </button>
        <button
          onClick={handleZoomOut}
          className="w-8 h-8 rounded bg-surface-700/80 border border-glass-border text-white hover:bg-surface-600 flex items-center justify-center text-lg font-bold backdrop-blur-sm transition-colors"
          title="Uzaklastir"
        >
          &#x2212;
        </button>
        <button
          onClick={handleReset}
          className="w-8 h-8 rounded bg-surface-700/80 border border-glass-border text-white hover:bg-surface-600 flex items-center justify-center text-xs backdrop-blur-sm transition-colors"
          title="Sifirla"
        >
          &#x21BA;
        </button>
      </div>

      <ComposableMap
        projection="geoMercator"
        projectionConfig={{ scale: 150, center: [0, 20] }}
        style={{ width: "100%", height: "100%", background: "transparent" }}
      >
        {/* SVG glow filter */}
        <defs>
          <filter id="glow-red" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-target" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <ZoomableGroup
          zoom={zoom}
          center={center}
          onMoveEnd={({ coordinates, zoom: z }) => {
            setCenter(coordinates as [number, number]);
            setZoom(z);
          }}
          minZoom={1}
          maxZoom={8}
        >
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  fill="#1a1a2e"
                  stroke="#2a2a4a"
                  strokeWidth={0.5}
                  style={{
                    default: { outline: "none" },
                    hover: { outline: "none", fill: "#252545" },
                    pressed: { outline: "none" },
                  }}
                />
              ))
            }
          </Geographies>

          {/* Glow katmani - kalın, yarim saydam */}
          {uniqueAttacks.map((attack, i) => (
            <Line
              key={`glow-${i}`}
              from={[attack.lon, attack.lat]}
              to={[target.lon, target.lat]}
              stroke={PROT_GLOW[attack.type] || "rgba(255,68,68,0.3)"}
              strokeWidth={Math.max(6 / zoom, 3)}
              strokeLinecap="round"
              fill="transparent"
            />
          ))}

          {/* Ana saldırı çizgileri - parlak, kalın */}
          {uniqueAttacks.map((attack, i) => (
            <Line
              key={`line-${i}`}
              from={[attack.lon, attack.lat]}
              to={[target.lon, target.lat]}
              stroke={PROT_COLORS[attack.type] || "#ff4444"}
              strokeWidth={Math.max(2.5 / zoom, 1.5)}
              strokeLinecap="round"
              fill="transparent"
              style={{ filter: "url(#glow-red)" }}
            />
          ))}

          {/* Saldırgan noktaları */}
          {uniqueAttacks.map((attack, i) => (
            <Marker key={`src-${i}`} coordinates={[attack.lon, attack.lat]}>
              <circle
                r={Math.max(4 / zoom, 2)}
                fill={PROT_COLORS[attack.type] || "#ff4444"}
                opacity={1}
                className="attack-dot"
              />
              <circle
                r={Math.max(8 / zoom, 4)}
                fill="none"
                stroke={PROT_COLORS[attack.type] || "#ff4444"}
                strokeWidth={Math.max(1 / zoom, 0.5)}
                opacity={0.6}
                className="attack-ring"
              />
            </Marker>
          ))}

          {/* Hedef nokta (Turkiye) */}
          <Marker coordinates={[target.lon, target.lat]}>
            <circle
              r={Math.max(6 / zoom, 3)}
              fill="#00F0FF"
              opacity={1}
              className="target-pulse"
              style={{ filter: "url(#glow-target)" }}
            />
            <circle
              r={Math.max(12 / zoom, 5)}
              fill="none"
              stroke="#00F0FF"
              strokeWidth={Math.max(1.5 / zoom, 0.5)}
              opacity={0.6}
              className="target-ring"
            />
            <text
              textAnchor="middle"
              y={Math.max(-18 / zoom, -10)}
              style={{
                fontFamily: "system-ui",
                fill: "#00F0FF",
                fontSize: `${Math.max(9 / zoom, 5)}px`,
                fontWeight: 600,
              }}
            >
              {target.label}
            </text>
          </Marker>
        </ZoomableGroup>
      </ComposableMap>
    </div>
  );
}

export const DdosWorldMap = memo(DdosWorldMapInner);
