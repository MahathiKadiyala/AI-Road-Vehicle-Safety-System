import React, { useState, useEffect } from 'react';
import { MapContainer as LeafletMap, TileLayer, Marker, Popup, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import { MapPin, Navigation, Eye, Crosshair } from 'lucide-react';
import { Hazard } from '../../types';
import { getHazardImageUrl } from '../../services/api';

interface MapContainerProps {
  initialLat?: number;
  initialLon?: number;
  initialZoom?: number;
  onLocationSelect?: (lat: number, lon: number) => void;
  hazards?: Hazard[];
  focusHazard?: Hazard | null;
}

// Severity-based marker colors
const severityColors: Record<string, string> = {
  low: '#10b981',
  medium: '#f59e0b',
  high: '#f97316',
  critical: '#ef4444',
};

// Custom modern SVG marker for Leaflet using DivIcon (avoids broken PNG bundle issues)
const createModernPin = (color: string = '#0ea5e9') => {
  return L.divIcon({
    className: 'custom-map-pin',
    html: `
      <div style="position: relative; transform: translate(-50%, -100%);">
        <div style="
          background: ${color};
          color: white;
          width: 32px;
          height: 32px;
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 14px rgba(0,0,0,0.4);
          border: 2px solid white;
        ">
          <div style="transform: rotate(45deg); font-size: 14px;">📍</div>
        </div>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
};

// Hazard-specific marker with severity color
const createHazardPin = (severity: string) => {
  const color = severityColors[severity] || '#f59e0b';
  return L.divIcon({
    className: 'hazard-map-pin',
    html: `
      <div style="position: relative; transform: translate(-50%, -100%);">
        <div style="
          background: ${color};
          color: white;
          width: 28px;
          height: 28px;
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 3px 12px rgba(0,0,0,0.4);
          border: 2px solid rgba(255,255,255,0.9);
        ">
          <div style="transform: rotate(45deg); font-size: 12px;">⚠️</div>
        </div>
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 28],
    popupAnchor: [0, -28],
  });
};

// Component to handle map clicks and user coordinate inspection
const MapClickHandler: React.FC<{ onSelect: (lat: number, lon: number) => void }> = ({ onSelect }) => {
  useMapEvents({
    click(e) {
      onSelect(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
};

// Component to programmatically fly to a position
const MapFlyTo: React.FC<{ lat: number; lon: number; zoom?: number }> = ({ lat, lon, zoom = 16 }) => {
  const map = useMap();
  useEffect(() => {
    map.flyTo([lat, lon], zoom, { duration: 0.8 });
  }, [lat, lon, zoom, map]);
  return null;
};

export const MapContainer: React.FC<MapContainerProps> = ({
  initialLat = 12.9716, // Bangalore default
  initialLon = 77.5946,
  initialZoom = 13,
  onLocationSelect,
  hazards = [],
  focusHazard,
}) => {
  const [clickedCoord, setClickedCoord] = useState<{ lat: number; lon: number } | null>({
    lat: initialLat,
    lon: initialLon,
  });

  const handleMapClick = (lat: number, lon: number) => {
    setClickedCoord({ lat, lon });
    if (onLocationSelect) {
      onLocationSelect(lat, lon);
    }
  };

  const samplePin = createModernPin('#0284c7');

  return (
    <div className="relative w-full h-[540px] rounded-2xl overflow-hidden border border-slate-800 bg-slate-950 shadow-2xl">
      {/* Floating Map HUD Top */}
      <div className="absolute top-4 left-4 z-[400] flex flex-wrap items-center gap-2 pointer-events-none">
        <div className="bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-slate-700/60 shadow-lg pointer-events-auto flex items-center gap-2 text-xs">
          <Navigation className="w-3.5 h-3.5 text-sky-400" />
          <span className="font-semibold text-slate-200">OpenStreetMap Live Layer</span>
          <span className="text-[10px] text-slate-400 font-mono">EPSG:4326</span>
        </div>

        {clickedCoord && (
          <div className="bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-slate-700/60 shadow-lg pointer-events-auto flex items-center gap-2 text-xs">
            <Crosshair className="w-3.5 h-3.5 text-emerald-400" />
            <span className="font-mono text-slate-300">
              {clickedCoord.lat.toFixed(5)}, {clickedCoord.lon.toFixed(5)}
            </span>
          </div>
        )}

        {hazards.length > 0 && (
          <div className="bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-slate-700/60 shadow-lg pointer-events-auto flex items-center gap-2 text-xs">
            <MapPin className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-slate-300">{hazards.length} hazard{hazards.length !== 1 ? 's' : ''} on map</span>
          </div>
        )}
      </div>

      {/* Floating Map HUD Bottom Helper */}
      <div className="absolute bottom-4 left-4 z-[400] pointer-events-none">
        <div className="bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-slate-700/60 shadow-lg pointer-events-auto flex items-center gap-2 text-[11px] text-slate-300">
          <Eye className="w-3.5 h-3.5 text-sky-400" />
          <span>Click anywhere to set hazard location. Colored markers show reported hazards.</span>
        </div>
      </div>

      {/* Actual Leaflet Map Canvas */}
      <LeafletMap
        center={[initialLat, initialLon]}
        zoom={initialZoom}
        scrollWheelZoom={true}
        className="w-full h-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        <MapClickHandler onSelect={handleMapClick} />

        {/* Fly to focused hazard if set */}
        {focusHazard && (
          <MapFlyTo lat={focusHazard.latitude} lon={focusHazard.longitude} />
        )}

        {/* Selected location marker */}
        {clickedCoord && (
          <Marker position={[clickedCoord.lat, clickedCoord.lon]} icon={samplePin}>
            <Popup>
              <div className="text-xs space-y-1">
                <div className="font-bold text-sky-400 flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5" />
                  Selected Report Location
                </div>
                <div className="text-slate-300 font-mono text-[11px]">
                  Latitude: {clickedCoord.lat.toFixed(5)}<br />
                  Longitude: {clickedCoord.lon.toFixed(5)}
                </div>
                <p className="text-[10px] text-slate-400 pt-1 border-t border-slate-700">
                  Use the form to submit a hazard report at this location.
                </p>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Hazard report markers from backend */}
        {hazards.map((hazard) => {
          const hazardPin = createHazardPin(hazard.severity);
          const imageUrl = getHazardImageUrl(hazard.image_url);

          return (
            <Marker
              key={hazard.id}
              position={[hazard.latitude, hazard.longitude]}
              icon={hazardPin}
            >
              <Popup maxWidth={280} minWidth={200}>
                <div className="text-xs space-y-2" style={{ minWidth: '180px' }}>
                  <div>
                    <div className="font-bold text-white text-sm">{hazard.title}</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      Citizen Report · {hazard.hazard_type} · {hazard.severity}
                    </div>
                  </div>

                  {hazard.description && (
                    <p className="text-slate-300 text-[11px] leading-relaxed">
                      {hazard.description}
                    </p>
                  )}

                  {imageUrl && (
                    <div className="rounded-lg overflow-hidden border border-slate-700">
                      <img
                        src={imageUrl}
                        alt={hazard.title}
                        className="w-full h-24 object-cover"
                        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                      />
                    </div>
                  )}

                  <div className="text-[10px] text-slate-400 font-mono pt-1 border-t border-slate-700 space-y-0.5">
                    <div>📍 {hazard.latitude.toFixed(5)}, {hazard.longitude.toFixed(5)}</div>
                    <div>🕐 {new Date(hazard.created_at).toLocaleString()}</div>
                    <div>📋 Status: {hazard.status}</div>
                  </div>

                  <div className="text-[9px] text-slate-500 italic pt-1 border-t border-slate-700">
                    User-submitted report — not verified by AI or authorities.
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </LeafletMap>
    </div>
  );
};
