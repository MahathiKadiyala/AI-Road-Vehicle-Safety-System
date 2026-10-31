import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  FileText,
  RotateCcw,
  Sparkles,
  Info,
  Car,
  Gauge,
  Sliders,
  Scale,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  VehicleAssessmentPayload,
  VehicleAssessmentResult,
  VehicleStandardsResponse,
} from '../../types';
import { assessVehicle, fetchVehicleStandards } from '../../services/api';

interface VehicleAssessmentViewProps {
  onApplyToRisk?: (score: number) => void;
}

export const VehicleAssessmentView: React.FC<VehicleAssessmentViewProps> = ({ onApplyToRisk }) => {
  // Form input state
  const [make, setMake] = useState<string>('Maruti Suzuki');
  const [model, setModel] = useState<string>('Swift VXi');
  const [year, setYear] = useState<number>(2020);
  const [odometerKm, setOdometerKm] = useState<number>(45000);
  const [vehicleCategory, setVehicleCategory] = useState<string>('M1_passenger_car');
  const [tyreTreadMm, setTyreTreadMm] = useState<number>(4.2);
  const [brakePadMm, setBrakePadMm] = useState<number>(6.5);
  const [serviceRecordsCount, setServiceRecordsCount] = useState<number>(4);
  const [pastAccidentsCount, setPastAccidentsCount] = useState<number>(0);
  const [pucValid, setPucValid] = useState<boolean | null>(true);
  const [insuranceValid, setInsuranceValid] = useState<boolean | null>(true);
  const [fitnessValid, setFitnessValid] = useState<boolean | null>(null);
  const [disclaimerAck, setDisclaimerAck] = useState<boolean>(false);

  // API interaction state
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<VehicleAssessmentResult | null>(null);

  // Standards registry drawer/collapse
  const [standards, setStandards] = useState<VehicleStandardsResponse | null>(null);
  const [showStandards, setShowStandards] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    async function loadStandards() {
      try {
        const data = await fetchVehicleStandards();
        if (isMounted) setStandards(data);
      } catch (err) {
        console.warn('Could not load standards registry:', err);
      }
    }
    loadStandards();
    return () => {
      isMounted = false;
    };
  }, []);

  // Category-dependent statutory thresholds
  const statTyreLimit = vehicleCategory === 'L_two_three_wheeler' ? 0.8 : 1.6;
  const advisoryTyreLimit = vehicleCategory === 'L_two_three_wheeler' ? 1.5 : 2.5;

  // Presets for quick evaluation demonstrations
  const loadPreset = (type: 'compliant_car' | 'compliant_2w' | 'cmvr_tyre_violation' | 'critical_brake_wear' | 'high_mileage') => {
    setErrorMsg(null);
    setResult(null);
    setDisclaimerAck(true);

    if (type === 'compliant_car') {
      setVehicleCategory('M1_passenger_car');
      setMake('Honda');
      setModel('City ZX');
      setYear(2022);
      setOdometerKm(28000);
      setTyreTreadMm(5.5);
      setBrakePadMm(8.0);
      setServiceRecordsCount(4);
      setPastAccidentsCount(0);
      setPucValid(true);
      setInsuranceValid(true);
      setFitnessValid(null);
    } else if (type === 'compliant_2w') {
      // Demonstrates category-specific 0.8 mm threshold under CMVR Rule 95
      setVehicleCategory('L_two_three_wheeler');
      setMake('Hero');
      setModel('Splendor Plus');
      setYear(2021);
      setOdometerKm(18000);
      setTyreTreadMm(1.2); // Compliant for 2W (>=0.8 mm), but would violate 1.6 mm car rule!
      setBrakePadMm(3.8);
      setServiceRecordsCount(3);
      setPastAccidentsCount(0);
      setPucValid(true);
      setInsuranceValid(true);
      setFitnessValid(null);
    } else if (type === 'cmvr_tyre_violation') {
      setVehicleCategory('M1_passenger_car');
      setMake('Hyundai');
      setModel('i20 Sportz');
      setYear(2017);
      setOdometerKm(72000);
      setTyreTreadMm(1.2); // Below 1.6 mm statutory limit for cars
      setBrakePadMm(4.5);
      setServiceRecordsCount(2);
      setPastAccidentsCount(0);
      setPucValid(true);
      setInsuranceValid(true);
      setFitnessValid(null);
    } else if (type === 'critical_brake_wear') {
      setVehicleCategory('M1_passenger_car');
      setMake('Tata');
      setModel('Nexon XZ');
      setYear(2018);
      setOdometerKm(88000);
      setTyreTreadMm(2.2);
      setBrakePadMm(1.4); // Below 2.0 mm manufacturer discard threshold (Advisory)
      setServiceRecordsCount(1);
      setPastAccidentsCount(2);
      setPucValid(false);
      setInsuranceValid(true);
      setFitnessValid(null);
    } else if (type === 'high_mileage') {
      setVehicleCategory('M1_passenger_car');
      setMake('Toyota');
      setModel('Innova Crysta');
      setYear(2008);
      setOdometerKm(195000);
      setTyreTreadMm(2.0);
      setBrakePadMm(3.0);
      setServiceRecordsCount(8);
      setPastAccidentsCount(1);
      setPucValid(true);
      setInsuranceValid(true);
      setFitnessValid(false); // Age > 15 years, unrenewed registration
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!disclaimerAck) {
      setErrorMsg('Mandatory Disclaimer: You must acknowledge that this is an advisory estimate and not a legal roadworthiness certification before running the assessment.');
      return;
    }

    setLoading(true);
    try {
      const payload: VehicleAssessmentPayload = {
        make,
        model,
        year: Number(year),
        odometer_km: Number(odometerKm),
        vehicle_category: vehicleCategory,
        tyre_tread_depth_mm: Number(tyreTreadMm),
        brake_pad_thickness_mm: Number(brakePadMm),
        service_records_count: Number(serviceRecordsCount),
        past_accidents_count: Number(pastAccidentsCount),
        puc_valid: pucValid,
        insurance_valid: insuranceValid,
        fitness_certificate_valid: fitnessValid,
        disclaimer_acknowledged: true,
      };

      const res = await assessVehicle(payload);
      setResult(res);
      // Smooth scroll to results
      setTimeout(() => {
        const el = document.getElementById('assessment-results-section');
        if (el) el.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } catch (err: any) {
      setErrorMsg(err.message || 'Vehicle assessment failed.');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setResult(null);
    setErrorMsg(null);
  };

  return (
    <div className="space-y-6">
      {/* Header Banner — Simple Light Design */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-sky-50 text-sky-700 border border-sky-200">
                Phase 4 Active
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                CMVR / AIS Audited
              </span>
            </div>
            <h1 className="text-xl md:text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5">
              <Car className="w-6 h-6 text-sky-600" />
              Vehicle Safety & Statutory Compliance Assessment
            </h1>
            <p className="text-xs md:text-sm text-slate-500 max-w-3xl leading-relaxed">
              Transparent, rule-based vehicle safety evaluation distinguishing Indian statutory standards (CMVR 1989 Rule 95) from advisory maintenance wear guidelines.
            </p>
          </div>

          <button
            type="button"
            onClick={() => setShowStandards(!showStandards)}
            className="self-start md:self-auto px-3.5 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs font-medium text-slate-700 transition-all flex items-center gap-2 shadow-xs"
          >
            <Scale className="w-4 h-4 text-sky-600" />
            <span>Authoritative Standards</span>
            {showStandards ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Expandable Standards Registry — Clean Light Cards */}
        {showStandards && (
          <div className="mt-5 pt-5 border-t border-slate-100 animate-in fade-in duration-200 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs uppercase font-mono tracking-wider text-slate-700 font-semibold flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-sky-600" />
                Verified Indian Legal & Technical Standards Registry
              </h3>
              <span className="text-[10px] text-slate-400 font-mono">
                Version: {standards?.version || 'CMVR-AIS-Advisory-v2.0'}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">Tyre Tread (NSD)</span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 font-mono font-semibold border border-rose-200">
                    Statutory
                  </span>
                </div>
                <div className="text-slate-700 text-[11px]">
                  <strong>1.6 mm min</strong> (4W M1) / <strong>0.8 mm</strong> (2/3W L)
                </div>
                <p className="text-[10px] text-slate-500">
                  CMVR 1989 Rule 95(3)(iv) & AIS-044. Non-negotiable statutory limit across tyre breadth.
                </p>
              </div>

              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">Brake Lining</span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 font-mono font-semibold border border-amber-200">
                    Advisory OEM
                  </span>
                </div>
                <div className="text-slate-700 text-[11px]">
                  <strong>&lt; 2.0 mm</strong> (Discard) / <strong>2.0–3.5 mm</strong> (Advisory)
                </div>
                <p className="text-[10px] text-slate-500">
                  Advisory Manufacturer Practice. CMVR Rule 96 regulates stopping performance, not lining mm.
                </p>
              </div>

              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">Emission PUC</span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-sky-50 text-sky-700 font-mono font-semibold border border-sky-200">
                    Statutory
                  </span>
                </div>
                <div className="text-slate-700 text-[11px]">
                  Mandatory Valid Certificate
                </div>
                <p className="text-[10px] text-slate-500">
                  CMVR 1989 Rule 115(7). Periodic emission compliance certification.
                </p>
              </div>

              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">Registration / Fitness</span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 font-mono font-semibold border border-indigo-200">
                    Statutory
                  </span>
                </div>
                <div className="text-slate-700 text-[11px]">
                  15-Yr Private Renewal / Transport Fitness
                </div>
                <p className="text-[10px] text-slate-500">
                  MVA 1988 Sec 41(8) & CMVR 52 (Private) vs CMVR 62 (Transport). Age alone is not an automatic violation.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Evaluation Presets */}
      <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-sky-600" />
          <span className="text-xs font-semibold text-slate-800">Quick Test Scenarios:</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => loadPreset('compliant_car')}
            className="px-2.5 py-1 text-xs rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 font-medium transition-colors"
          >
            ✓ Compliant Car (M1)
          </button>
          <button
            type="button"
            onClick={() => loadPreset('compliant_2w')}
            className="px-2.5 py-1 text-xs rounded-lg bg-sky-50 text-sky-700 border border-sky-200 hover:bg-sky-100 font-medium transition-colors"
          >
            ✓ 2-Wheeler (1.2mm compliant under 0.8mm rule)
          </button>
          <button
            type="button"
            onClick={() => loadPreset('cmvr_tyre_violation')}
            className="px-2.5 py-1 text-xs rounded-lg bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 font-medium transition-colors"
          >
            ⚠ CMVR 95 Car Tyre Violation (&lt;1.6mm)
          </button>
          <button
            type="button"
            onClick={() => loadPreset('critical_brake_wear')}
            className="px-2.5 py-1 text-xs rounded-lg bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 font-medium transition-colors"
          >
            ⚠ Critical Brake Wear (&lt;2.0mm Advisory)
          </button>
          <button
            type="button"
            onClick={() => loadPreset('high_mileage')}
            className="px-2.5 py-1 text-xs rounded-lg bg-slate-100 text-slate-700 border border-slate-300 hover:bg-slate-200 font-medium transition-colors"
          >
            ⏱ Unrenewed &gt;15 Yr Reg (CMVR 52)
          </button>
        </div>
      </div>

      {/* Main Grid: Assessment Form & Results */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Input Form (7 cols) */}
        <form onSubmit={handleSubmit} className="lg:col-span-7 bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6">
          <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Sliders className="w-4 h-4 text-sky-600" />
                Vehicle Specifications & Physical Wear Inputs
              </h2>
              <p className="text-[11px] text-slate-500">
                Input measured physical attributes. The evaluation engine applies category-specific statutory rules and advisory bounds.
              </p>
            </div>
            {result && (
              <button
                type="button"
                onClick={resetForm}
                className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 font-medium"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Reset
              </button>
            )}
          </div>

          {/* Section 1: Vehicle Identity & Category */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider font-mono">
              1. Vehicle Profile & CMVR Classification
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  CMVR Vehicle Category <span className="text-rose-500">*</span>
                </label>
                <select
                  value={vehicleCategory}
                  onChange={(e) => setVehicleCategory(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-sky-500 focus:outline-none bg-white font-medium"
                >
                  <option value="M1_passenger_car">Passenger Car (Category M1) — 1.6 mm Tyre Limit</option>
                  <option value="L_two_three_wheeler">Two/Three-Wheeler (Category L) — 0.8 mm Tyre Limit</option>
                  <option value="commercial_transport">Commercial Transport — 1.6 mm & Annual Fitness (CMVR 62)</option>
                  <option value="unknown">Unknown Category (Requires Explicit Verification)</option>
                </select>
                <span className="text-[10px] text-slate-400">
                  {vehicleCategory === 'L_two_three_wheeler' ? 'Statutory tyre floor under CMVR Rule 95 is 0.8 mm' : 'Statutory tyre floor under CMVR Rule 95 is 1.6 mm'}
                </span>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Make / Brand</label>
                <input
                  type="text"
                  value={make}
                  onChange={(e) => setMake(e.target.value)}
                  required
                  placeholder="e.g. Maruti Suzuki, Tata, Hero"
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Model / Variant</label>
                <input
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  required
                  placeholder="e.g. Swift VXi, Nexon XZ, Splendor"
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Year of Manufacture</label>
                <input
                  type="number"
                  min="1970"
                  max="2030"
                  value={year}
                  onChange={(e) => setYear(Number(e.target.value))}
                  required
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
                <span className="text-[10px] text-slate-400">
                  {new Date().getFullYear() - year >= 15 ? '⚠️ Age ≥ 15 years: CMVR Rule 52 registration renewal applies' : 'Current age: ' + (new Date().getFullYear() - year) + ' years'}
                </span>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-slate-700 mb-1">Odometer Reading (km)</label>
                <input
                  type="number"
                  min="0"
                  max="1000000"
                  value={odometerKm}
                  onChange={(e) => setOdometerKm(Number(e.target.value))}
                  required
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Physical Wear Measurements with Category-Specific Gauges */}
          <div className="space-y-4 pt-2 border-t border-slate-100">
            <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider font-mono flex items-center justify-between">
              <span>2. Critical Mechanical Wear Measurements</span>
              <span className="text-[10px] text-indigo-600 font-normal">Physical gauge readings</span>
            </h3>

            {/* Tyre Tread Depth */}
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/90 space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                    Tyre Non-Skid Depth (NSD)
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 font-semibold border border-rose-200">
                      CMVR Rule 95 Statutory
                    </span>
                  </label>
                  <p className="text-[11px] text-slate-500">
                    Statutory limit for {vehicleCategory === 'L_two_three_wheeler' ? '2/3-Wheelers (Category L)' : 'Passenger Cars (Category M1)'}: <strong className="text-rose-700">{statTyreLimit.toFixed(1)} mm</strong>. Advisory wear buffer: <strong className="text-amber-700">{advisoryTyreLimit.toFixed(1)} mm</strong>.
                  </p>
                </div>
                <div className="text-right">
                  <span className={`text-base font-extrabold font-mono ${tyreTreadMm < statTyreLimit ? 'text-rose-600' : tyreTreadMm < advisoryTyreLimit ? 'text-amber-600' : 'text-emerald-600'}`}>
                    {tyreTreadMm.toFixed(1)} mm
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="0.0"
                  max="10.0"
                  step="0.1"
                  value={tyreTreadMm}
                  onChange={(e) => setTyreTreadMm(Number(e.target.value))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-sky-600"
                />
                <input
                  type="number"
                  min="0.0"
                  max="25.0"
                  step="0.1"
                  value={tyreTreadMm}
                  onChange={(e) => setTyreTreadMm(Number(e.target.value))}
                  className="w-20 px-2 py-1 text-xs border border-slate-300 rounded-lg text-right font-mono"
                />
              </div>

              <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                <span className="text-rose-600 font-semibold">0.0 mm (Bald)</span>
                <span className="text-rose-600 font-semibold">▲ {statTyreLimit.toFixed(1)} mm (CMVR 95 Limit)</span>
                <span className="text-amber-600 font-semibold">{advisoryTyreLimit.toFixed(1)} mm (Advisory)</span>
                <span className="text-emerald-600 font-semibold">8.0 mm (New)</span>
              </div>
            </div>

            {/* Brake Pad Thickness */}
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/90 space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                    Brake Pad Lining Thickness
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-semibold border border-amber-200">
                      Advisory OEM Guideline
                    </span>
                  </label>
                  <p className="text-[11px] text-slate-500">
                    Industry discard limit: <strong className="text-rose-700">&lt; 2.0 mm</strong>. Advisory window: <strong className="text-amber-700">2.0–3.5 mm</strong>. (Note: CMVR Rule 96 prescribes stopping performance, not a statutory lining thickness).
                  </p>
                </div>
                <div className="text-right">
                  <span className={`text-base font-extrabold font-mono ${brakePadMm < 2.0 ? 'text-rose-600' : brakePadMm < 3.5 ? 'text-amber-600' : 'text-emerald-600'}`}>
                    {brakePadMm.toFixed(1)} mm
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="0.5"
                  max="14.0"
                  step="0.1"
                  value={brakePadMm}
                  onChange={(e) => setBrakePadMm(Number(e.target.value))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-sky-600"
                />
                <input
                  type="number"
                  min="0.0"
                  max="20.0"
                  step="0.1"
                  value={brakePadMm}
                  onChange={(e) => setBrakePadMm(Number(e.target.value))}
                  className="w-20 px-2 py-1 text-xs border border-slate-300 rounded-lg text-right font-mono"
                />
              </div>

              <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                <span className="text-rose-600 font-semibold">0.5 mm (Backing plate hazard)</span>
                <span className="text-rose-600 font-semibold">▲ 2.0 mm (OEM Discard)</span>
                <span className="text-amber-600 font-semibold">3.5 mm (Advisory Window)</span>
                <span className="text-emerald-600 font-semibold">12.0 mm (New)</span>
              </div>
            </div>
          </div>

          {/* Section 3: Maintenance & History */}
          <div className="space-y-3 pt-2 border-t border-slate-100">
            <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider font-mono">
              3. Service History & Incident Records
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Documented Authorized Service Records
                </label>
                <input
                  type="number"
                  min="0"
                  max="50"
                  value={serviceRecordsCount}
                  onChange={(e) => setServiceRecordsCount(Number(e.target.value))}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
                <span className="text-[10px] text-slate-400">Maintains preventative fluid & belt replacement trail</span>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Past Reported Structural Accidents
                </label>
                <input
                  type="number"
                  min="0"
                  max="20"
                  value={pastAccidentsCount}
                  onChange={(e) => setPastAccidentsCount(Number(e.target.value))}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
                <span className="text-[10px] text-slate-400">Flags potential structural chassis alignment concerns</span>
              </div>
            </div>
          </div>

          {/* Section 4: Indian Statutory Compliance Checks (Self-Reported) */}
          <div className="space-y-3 pt-2 border-t border-slate-100">
            <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider font-mono flex items-center justify-between">
              <span>4. Indian Statutory Document Status (Self-Reported)</span>
              <span className="text-[10px] text-amber-700 font-mono font-medium">Not verified against Parivahan/VAHAN</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* PUC */}
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-xs font-semibold text-slate-800 block">Valid PUC</span>
                <span className="text-[10px] text-slate-500 block mb-2">CMVR Rule 115(7)</span>
                <select
                  value={pucValid === null ? 'unknown' : pucValid ? 'yes' : 'no'}
                  onChange={(e) => setPucValid(e.target.value === 'unknown' ? null : e.target.value === 'yes')}
                  className="w-full text-xs p-1.5 border border-slate-300 rounded-lg bg-white"
                >
                  <option value="yes">Yes (Self-Reported Active)</option>
                  <option value="no">No (Expired / Lapsed)</option>
                  <option value="unknown">Not Provided (Unverified)</option>
                </select>
              </div>

              {/* Insurance */}
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-xs font-semibold text-slate-800 block">Valid Insurance</span>
                <span className="text-[10px] text-slate-500 block mb-2">MVA 1988 Sec 146</span>
                <select
                  value={insuranceValid === null ? 'unknown' : insuranceValid ? 'yes' : 'no'}
                  onChange={(e) => setInsuranceValid(e.target.value === 'unknown' ? null : e.target.value === 'yes')}
                  className="w-full text-xs p-1.5 border border-slate-300 rounded-lg bg-white"
                >
                  <option value="yes">Yes (Self-Reported Active)</option>
                  <option value="no">No (Expired / Lapsed)</option>
                  <option value="unknown">Not Provided (Unverified)</option>
                </select>
              </div>

              {/* Fitness / Registration Renewal */}
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-xs font-semibold text-slate-800 block">Reg. Renewal / Fitness</span>
                <span className="text-[10px] text-slate-500 block mb-2">CMVR Rule 52 / 62</span>
                <select
                  value={fitnessValid === null ? 'unknown' : fitnessValid ? 'yes' : 'no'}
                  onChange={(e) => setFitnessValid(e.target.value === 'unknown' ? null : e.target.value === 'yes')}
                  className="w-full text-xs p-1.5 border border-slate-300 rounded-lg bg-white"
                >
                  <option value="unknown">Not Provided (Unverified)</option>
                  <option value="yes">Yes (Renewed / Active)</option>
                  <option value="no">No (Expired / Lapsed)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Section 5: Mandatory Legal Disclaimer Acknowledgment */}
          <div className="p-4 bg-sky-50 border border-sky-200 rounded-xl space-y-2">
            <div className="flex items-start gap-2.5">
              <input
                id="disclaimer-checkbox"
                type="checkbox"
                checked={disclaimerAck}
                onChange={(e) => setDisclaimerAck(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
              />
              <label htmlFor="disclaimer-checkbox" className="text-xs text-sky-950 leading-relaxed cursor-pointer select-none">
                <strong className="text-sky-900">Mandatory Statutory & Advisory Acknowledgment:</strong> I understand that this module provides a preliminary, rule-based engineering estimate derived from self-reported parameters. It does <em>not</em> constitute a physical vehicle inspection, an RTO roadworthiness certification, or a structural crashworthiness guarantee. Document statuses have not been verified against official government registries.
              </label>
            </div>
          </div>

          {errorMsg && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl font-bold text-xs uppercase tracking-wider text-white bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-700 hover:to-indigo-700 shadow-md shadow-sky-600/20 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Evaluating Parameters...</span>
              </>
            ) : (
              <>
                <Gauge className="w-4 h-4" />
                <span>Calculate Safety Index & Audit Compliance</span>
              </>
            )}
          </button>
        </form>

        {/* Right Column: Results & Explainability (5 cols) */}
        <div id="assessment-results-section" className="lg:col-span-5 space-y-4">
          {!result ? (
            <div className="bg-white border border-slate-200 rounded-2xl p-8 text-center shadow-sm space-y-3">
              <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
                <Gauge className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-bold text-slate-800">No Assessment Run Yet</h3>
              <p className="text-xs text-slate-500 leading-relaxed">
                Fill in the measured vehicle parameters on the left or select a Quick Test Scenario to see deterministic scoring, statutory violations, and explainable parameter audits.
              </p>
              <div className="pt-2 text-left bg-slate-50 p-3.5 rounded-xl border border-slate-100 space-y-1.5 text-[11px] text-slate-600">
                <div className="font-semibold text-slate-800 flex items-center gap-1">
                  <Info className="w-3.5 h-3.5 text-sky-600" />
                  Audited Phase 4 Engine Standards:
                </div>
                <ul className="list-disc pl-4 space-y-1 text-slate-500 text-[10px]">
                  <li><strong>CMVR Rule 95(3)(iv)</strong> non-skid tyre tread limit: 1.6 mm (M1 car) vs 0.8 mm (2/3W L).</li>
                  <li><strong>Manufacturer Practice</strong>: &lt; 2.0 mm brake friction wear discard guideline.</li>
                  <li>Age, mileage, and accident rate degradation.</li>
                  <li>Explicit audit of missing / unverified attributes (zero false assumptions).</li>
                </ul>
              </div>
            </div>
          ) : (
            <div className="space-y-4 animate-in fade-in duration-300">
              {/* Score Card */}
              <div className={`p-5 rounded-2xl border shadow-xs ${
                result.risk_tier === 'Critical'
                  ? 'bg-rose-50/70 border-rose-200'
                  : result.risk_tier === 'High'
                  ? 'bg-amber-50/70 border-amber-200'
                  : result.risk_tier === 'Moderate'
                  ? 'bg-amber-50/40 border-amber-200'
                  : 'bg-emerald-50/70 border-emerald-200'
              }`}>
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase font-mono tracking-wider font-bold text-slate-600">
                    Preliminary Safety Index
                  </span>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold font-mono ${
                    result.risk_tier === 'Critical'
                      ? 'bg-rose-600 text-white'
                      : result.risk_tier === 'High'
                      ? 'bg-amber-600 text-white'
                      : result.risk_tier === 'Moderate'
                      ? 'bg-amber-500 text-white'
                      : 'bg-emerald-600 text-white'
                  }`}>
                    {result.risk_tier} Risk
                  </span>
                </div>

                <div className="mt-3 flex items-baseline gap-2">
                  <span className={`text-4xl font-extrabold font-mono tracking-tight ${
                    result.risk_tier === 'Critical'
                      ? 'text-rose-700'
                      : result.risk_tier === 'High'
                      ? 'text-amber-700'
                      : result.risk_tier === 'Moderate'
                      ? 'text-amber-700'
                      : 'text-emerald-700'
                  }`}>
                    {result.preliminary_score.toFixed(1)}
                  </span>
                  <span className="text-xs font-semibold text-slate-500">/ 100</span>
                </div>

                <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                  Vehicle: <strong className="text-slate-900">{result.make} {result.model} ({result.year})</strong> · Category: <strong className="text-slate-900 font-mono text-[11px]">{result.vehicle_category}</strong> with <strong className="text-slate-900">{result.odometer_km.toLocaleString()} km</strong>.
                </p>

                <div className="mt-3 pt-3 border-t border-slate-200/80 flex items-center justify-between text-[11px] text-slate-600">
                  <span>Data Completeness:</span>
                  <span className="font-semibold text-slate-800">{result.data_completeness}</span>
                </div>
                <div className="mt-1 flex items-center justify-between text-[11px] text-slate-600">
                  <span>Document Source:</span>
                  <span className="font-mono text-[10px] text-amber-800 font-semibold">{result.document_verification_source}</span>
                </div>

                {onApplyToRisk && (
                  <div className="mt-4 pt-3 border-t border-slate-200">
                    <button
                      type="button"
                      onClick={() => onApplyToRisk(result.preliminary_score)}
                      className="w-full py-2.5 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-sm transition-colors flex items-center justify-center gap-2 cursor-pointer"
                    >
                      <ShieldAlert className="w-4 h-4 text-indigo-200" />
                      <span>Assess Corridor Risk with this Vehicle Profile ({result.preliminary_score.toFixed(1)}/100)</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Critical Statutory Violations Banner */}
              {result.statutory_violations.length > 0 && (
                <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl space-y-2">
                  <div className="flex items-center gap-2 text-rose-900 font-bold text-xs uppercase tracking-wider font-mono">
                    <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
                    <span>Statutory Law Violations Detected</span>
                  </div>
                  <ul className="space-y-1.5 pl-5 list-disc text-xs text-rose-950 font-medium">
                    {result.statutory_violations.map((viol, idx) => (
                      <li key={idx} className="leading-snug">{viol}</li>
                    ))}
                  </ul>
                  <div className="text-[10px] text-rose-800 font-mono mt-1 pt-1 border-t border-rose-200/80">
                    ⚠ Operating a motor vehicle in this state violates Central Motor Vehicles Rules and is punishable under the Motor Vehicles Act.
                  </div>
                </div>
              )}

              {/* Advisory Technical Warnings Banner */}
              {result.advisory_warnings.length > 0 && (
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-2">
                  <div className="flex items-center gap-2 text-amber-900 font-bold text-xs uppercase tracking-wider font-mono">
                    <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                    <span>Advisory Mechanical Warnings</span>
                  </div>
                  <ul className="space-y-1.5 pl-5 list-disc text-xs text-amber-950 font-medium">
                    {result.advisory_warnings.map((adv, idx) => (
                      <li key={idx} className="leading-snug">{adv}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Unverified / Missing Attributes Card */}
              <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-xs space-y-2">
                <div className="flex items-center gap-1.5 text-slate-800 font-bold text-xs">
                  <HelpCircle className="w-4 h-4 text-slate-500" />
                  <span>Unverified Physical & Electronic Attributes</span>
                </div>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  The following safety-critical systems were not verified in this self-reported assessment and require physical workshop inspection:
                </p>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {result.missing_unverified_attributes.map((attr, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded text-[10px] bg-slate-100 text-slate-600 border border-slate-200 font-mono"
                    >
                      • {attr}
                    </span>
                  ))}
                </div>
              </div>

              {/* Legal Disclaimer Box */}
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-[10px] text-slate-600 leading-relaxed">
                <strong className="text-slate-800">Advisory Disclaimer:</strong> {result.disclaimer_text}
                <div className="mt-1 font-mono text-slate-400 text-[9px]">
                  Disclaimer Version: {result.legal_disclaimer_version} · ID: {result.id}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Full-width Parameter Audit Breakdown Table (When result exists) */}
      {result && result.parameter_breakdown && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-sky-600" />
                Comprehensive Parameter Audit & Legal Reference Breakdown
              </h3>
              <p className="text-xs text-slate-500">
                Detailed explainability showing citations, compliance findings, recommendations, and point deductions for each vehicle factor.
              </p>
            </div>
            <span className="text-xs font-mono text-slate-500">
              Total Factors Audited: {result.parameter_breakdown.length}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-700 font-semibold font-mono text-[11px]">
                  <th className="py-2.5 px-3">Parameter</th>
                  <th className="py-2.5 px-3">Measured Value</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Category</th>
                  <th className="py-2.5 px-3">Standard Reference</th>
                  <th className="py-2.5 px-3">Finding & Implication</th>
                  <th className="py-2.5 px-3">Recommendation</th>
                  <th className="py-2.5 px-3 text-right">Deduction</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {result.parameter_breakdown.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-3 font-semibold text-slate-900 whitespace-nowrap">
                      {item.parameter}
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-700 whitespace-nowrap">
                      {item.measured_value}
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap">
                      {item.status === 'compliant' && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                          <CheckCircle2 className="w-3 h-3" /> Compliant
                        </span>
                      )}
                      {item.status === 'warning' && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800">
                          <AlertTriangle className="w-3 h-3" /> Advisory Warning
                        </span>
                      )}
                      {item.status === 'violation' && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-100 text-rose-800">
                          <ShieldAlert className="w-3 h-3" /> Violation
                        </span>
                      )}
                      {item.status === 'unverified' && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">
                          <HelpCircle className="w-3 h-3" /> Unverified
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap">
                      {item.is_statutory ? (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                          Statutory
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-sky-50 text-sky-700 border border-sky-200">
                          Advisory
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 font-mono text-[11px] text-slate-600">
                      {item.statutory_reference}
                    </td>
                    <td className="py-3 px-3 text-slate-700 min-w-[200px] leading-relaxed">
                      {item.finding}
                    </td>
                    <td className="py-3 px-3 text-slate-600 min-w-[200px] leading-relaxed">
                      {item.recommendation}
                    </td>
                    <td className="py-3 px-3 text-right font-mono font-bold whitespace-nowrap">
                      {item.deduction_applied > 0 ? (
                        <span className="text-rose-600">-{item.deduction_applied.toFixed(1)}</span>
                      ) : (
                        <span className="text-emerald-600">0.0</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
