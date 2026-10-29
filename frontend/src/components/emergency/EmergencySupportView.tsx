import React, { useState, useEffect } from 'react';
import {
  Ambulance,
  Phone,
  MapPin,
  AlertTriangle,
  CheckCircle2,
  Search,
  Navigation,
  Info,
  RotateCcw,
} from 'lucide-react';
import { NearbyHospital, NearbyHospitalsResponse } from '../../types';
import { fetchNearbyHospitals } from '../../services/api';

export const EmergencySupportView: React.FC = () => {
  // Coordinates and query params (defaults to Bengaluru center)
  const [latitude, setLatitude] = useState<number>(12.9716);
  const [longitude, setLongitude] = useState<number>(77.5946);
  const [radiusKm, setRadiusKm] = useState<number>(10);
  const [emergencyOnly, setEmergencyOnly] = useState<boolean>(true);

  // Results state
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<NearbyHospitalsResponse | null>(null);

  const handleSearch = async () => {
    setLoading(true);
    setError(null);
    try {
      const radiusMeters = radiusKm * 1000;
      const data = await fetchNearbyHospitals(latitude, longitude, radiusMeters, emergencyOnly);
      setResponse(data);
    } catch (err: any) {
      setError(err.message || 'Failed to query nearby hospitals.');
    } finally {
      setLoading(false);
    }
  };

  // Perform initial search on mount
  useEffect(() => {
    handleSearch();
  }, []);

  const setLocation = (lat: number, lon: number) => {
    setLatitude(lat);
    setLongitude(lon);
  };

  return (
    <div className="space-y-6">
      {/* Header and Helplines Banner */}
      <div className="bg-gradient-to-r from-red-600 via-rose-600 to-indigo-700 rounded-3xl p-6 text-white shadow-lg space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-xl bg-white/10 backdrop-blur-sm">
                <Ambulance className="w-6 h-6 text-white" />
              </span>
              <h2 className="text-xl sm:text-2xl font-bold tracking-tight">
                Emergency Response & Trauma Center Locator
              </h2>
            </div>
            <p className="text-xs sm:text-sm text-rose-100 max-w-2xl leading-relaxed">
              Locate verified trauma centers, casualty wards, and specialty hospitals closest to the accident scene.
              Distances are straight-line approximations for situational awareness.
            </p>
          </div>

          <div className="flex flex-wrap sm:flex-nowrap gap-2">
            <a
              href="tel:112"
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white text-rose-700 font-bold text-sm shadow hover:bg-rose-50 transition-colors"
            >
              <Phone className="w-4 h-4 text-rose-600" />
              <span>Dial 112 (National)</span>
            </a>
            <a
              href="tel:108"
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-400 text-slate-900 font-bold text-sm shadow hover:bg-amber-300 transition-colors"
            >
              <Ambulance className="w-4 h-4 text-slate-900" />
              <span>Dial 108 (Ambulance)</span>
            </a>
          </div>
        </div>

        {/* Quick Helplines Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-white/20 text-xs">
          <div className="bg-white/10 backdrop-blur-xs p-2.5 rounded-xl">
            <span className="text-rose-200 block text-[10px] uppercase font-mono">National Helpline</span>
            <span className="font-bold text-base">112</span>
            <span className="text-[10px] text-rose-100 block">All-in-one Emergency</span>
          </div>
          <div className="bg-white/10 backdrop-blur-xs p-2.5 rounded-xl">
            <span className="text-rose-200 block text-[10px] uppercase font-mono">Medical Ambulance</span>
            <span className="font-bold text-base">108</span>
            <span className="text-[10px] text-rose-100 block">Free 24/7 Ambulance</span>
          </div>
          <div className="bg-white/10 backdrop-blur-xs p-2.5 rounded-xl">
            <span className="text-rose-200 block text-[10px] uppercase font-mono">Police Emergency</span>
            <span className="font-bold text-base">100</span>
            <span className="text-[10px] text-rose-100 block">Immediate Police Dispatch</span>
          </div>
          <div className="bg-white/10 backdrop-blur-xs p-2.5 rounded-xl">
            <span className="text-rose-200 block text-[10px] uppercase font-mono">Traffic Police</span>
            <span className="font-bold text-base">103</span>
            <span className="text-[10px] text-rose-100 block">Accident Clearance</span>
          </div>
        </div>
      </div>

      {/* Search Parameters Card */}
      <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Navigation className="w-4 h-4 text-indigo-600" />
              Incident Coordinates & Proximity Radius
            </h3>
            <p className="text-xs text-slate-500">
              Provide incident GPS coordinates or choose a preset corridor to search for verified facilities.
            </p>
          </div>

          {/* Quick Corridor Presets */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] text-slate-400 font-medium">Presets:</span>
            <button
              type="button"
              onClick={() => setLocation(12.9716, 77.5946)}
              className="text-xs px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700 font-medium transition-colors"
            >
              Central Bengaluru
            </button>
            <button
              type="button"
              onClick={() => setLocation(12.9345, 77.6265)}
              className="text-xs px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700 font-medium transition-colors"
            >
              Koramangala
            </button>
            <button
              type="button"
              onClick={() => setLocation(12.9996, 77.5710)}
              className="text-xs px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700 font-medium transition-colors"
            >
              Malleshwaram
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Latitude (°N)
            </label>
            <input
              type="number"
              step="0.0001"
              value={latitude}
              onChange={(e) => setLatitude(parseFloat(e.target.value) || 0)}
              className="w-full text-xs font-mono px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Longitude (°E)
            </label>
            <input
              type="number"
              step="0.0001"
              value={longitude}
              onChange={(e) => setLongitude(parseFloat(e.target.value) || 0)}
              className="w-full text-xs font-mono px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Search Radius: <span className="text-indigo-600 font-mono font-bold">{radiusKm} km</span>
            </label>
            <input
              type="range"
              min="1"
              max="50"
              step="1"
              value={radiusKm}
              onChange={(e) => setRadiusKm(parseInt(e.target.value, 10))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600 mt-2"
            />
          </div>

          <div className="flex flex-col justify-end">
            <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-700 mb-2">
              <input
                type="checkbox"
                checked={emergencyOnly}
                onChange={(e) => setEmergencyOnly(e.target.checked)}
                className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span>24/7 Emergency Wards Only</span>
            </label>
            <button
              type="button"
              onClick={handleSearch}
              disabled={loading}
              className="w-full text-xs font-bold px-4 py-2.5 rounded-xl bg-indigo-600 text-white shadow-sm hover:bg-indigo-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
            >
              {loading ? (
                <>
                  <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                  <span>Searching Facilities...</span>
                </>
              ) : (
                <>
                  <Search className="w-3.5 h-3.5" />
                  <span>Search Nearby Facilities</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Unable to complete proximity search</p>
            <p className="text-[11px] text-amber-700 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Response and Facilities Grid */}
      {response && (
        <div className="space-y-4">
          {/* Query Summary Bar */}
          <div className="bg-slate-50 border border-slate-200 rounded-2xl px-5 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-bold text-slate-900">Found {response.total_found} verified facility(ies)</span>
              <span className="text-slate-400">·</span>
              <span className="text-slate-600 font-mono">Radius: {response.search_radius_meters / 1000} km</span>
              <span className="text-slate-400">·</span>
              <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-white border border-slate-200 text-slate-600">
                Engine: {response.spatial_engine}
              </span>
            </div>
            {response.emergency_only_filter && (
              <span className="text-[11px] font-semibold text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-lg self-start sm:self-auto">
                Filtered: 24/7 Casualty Only
              </span>
            )}
          </div>

          {/* Empty state */}
          {response.total_found === 0 ? (
            <div className="bg-white border border-slate-200 rounded-3xl p-8 text-center space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
                <Ambulance className="w-6 h-6" />
              </div>
              <h4 className="text-sm font-bold text-slate-800">No Verified Facilities Found Within {radiusKm} km</h4>
              <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
                No verified medical or trauma facilities were located in the specified search radius.
                Consider increasing the radius slider above, or contact national emergency dispatch directly at 112 / 108.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {response.hospitals.map((hospital: NearbyHospital) => (
                <div
                  key={hospital.id}
                  className="bg-white border border-slate-200 hover:border-indigo-300 rounded-2xl p-5 shadow-sm space-y-3 flex flex-col justify-between transition-all"
                >
                  <div className="space-y-2">
                    {/* Header: Facility type and Verified Badge */}
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase tracking-wider ${
                          hospital.facility_type.toLowerCase().includes('trauma')
                            ? 'bg-red-50 text-red-700 border border-red-200'
                            : hospital.facility_type.toLowerCase().includes('specialty')
                            ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                            : 'bg-sky-50 text-sky-700 border border-sky-200'
                        }`}
                      >
                        {hospital.facility_type}
                      </span>
                      {hospital.is_verified_facility && (
                        <span className="flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          Verified
                        </span>
                      )}
                    </div>

                    {/* Facility Name */}
                    <h4 className="text-sm font-bold text-slate-900 leading-snug">
                      {hospital.name}
                    </h4>

                    {/* Distance Badge */}
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                      <Navigation className="w-3.5 h-3.5 text-indigo-600" />
                      <span className="font-bold text-indigo-900 font-mono">
                        {hospital.straight_line_distance_km} km
                      </span>
                      <span className="text-[10px] text-slate-500">(straight-line)</span>
                    </div>

                    {/* Address */}
                    {hospital.address && (
                      <div className="flex items-start gap-1.5 text-xs text-slate-600">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                        <span className="line-clamp-2 leading-relaxed">{hospital.address}</span>
                      </div>
                    )}

                    {/* Bed Capacity Benchmark */}
                    {hospital.total_beds_reference && (
                      <div className="text-[11px] text-slate-500">
                        Reference capacity: <span className="font-semibold text-slate-700">{hospital.total_beds_reference} beds</span> (public reference)
                      </div>
                    )}
                  </div>

                  {/* Contact / Emergency Footer */}
                  <div className="pt-3 border-t border-slate-100 space-y-2">
                    {hospital.contact_phone ? (
                      <a
                        href={`tel:${hospital.contact_phone}`}
                        className="w-full flex items-center justify-center gap-2 text-xs font-bold px-3 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-800 border border-slate-200 transition-colors"
                      >
                        <Phone className="w-3.5 h-3.5 text-emerald-600" />
                        <span>{hospital.contact_phone}</span>
                      </a>
                    ) : (
                      <div className="text-[11px] text-slate-400 text-center py-1">
                        Phone contact not listed — call 108
                      </div>
                    )}

                    {hospital.has_emergency_service && (
                      <div className="flex items-center justify-center gap-1 text-[10px] font-semibold text-rose-700">
                        <Ambulance className="w-3 h-3 text-rose-600" />
                        <span>24/7 Casualty & Triage Service Active</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Advisory Notices & Disclaimer */}
          <div className="bg-amber-50/60 border border-amber-200 rounded-2xl p-4 text-xs text-amber-950 space-y-2">
            <div className="flex items-center gap-1.5 font-bold text-amber-900">
              <Info className="w-4 h-4 text-amber-600" />
              <span>Emergency Disclaimer & Navigation Guidelines</span>
            </div>
            <p className="text-[11px] text-amber-900 leading-relaxed">
              {response.disclaimer}
            </p>
            {response.advisory_notes.length > 0 && (
              <ul className="list-disc list-inside space-y-1 text-[11px] text-amber-800 pt-1">
                {response.advisory_notes.map((note: string, idx: number) => (
                  <li key={idx}>{note}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
export default EmergencySupportView;
