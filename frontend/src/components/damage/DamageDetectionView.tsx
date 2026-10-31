import React, { useState, useEffect, useRef } from 'react';
import {
  UploadCloud,
  Cpu,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Info,
  Clock,
  ChevronRight,
  ShieldAlert,
  FileText,
  Eye,
} from 'lucide-react';
import {
  DamageDetectionResponse,
  DamageModelStatusResponse,
  DamageDetectionItem,
} from '../../types';
import { fetchDamageModelStatus, detectRoadDamage, getHazardImageUrl } from '../../services/api';

interface DamageDetectionViewProps {
  onPrefillHazard?: (data: {
    hazard_type: string;
    severity: string;
    title: string;
    description: string;
    imageFile?: File;
  }) => void;
}

export const DamageDetectionView: React.FC<DamageDetectionViewProps> = ({ onPrefillHazard }) => {
  const [modelStatus, setModelStatus] = useState<DamageModelStatusResponse | null>(null);
  const [loadingStatus, setLoadingStatus] = useState<boolean>(true);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.25);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [result, setResult] = useState<DamageDetectionResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'annotated' | 'original'>('annotated');

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load model diagnostics on mount
  useEffect(() => {
    let isMounted = true;
    async function loadStatus() {
      try {
        const data = await fetchDamageModelStatus();
        if (isMounted) setModelStatus(data);
      } catch (err: any) {
        console.warn('Could not load model status:', err);
      } finally {
        if (isMounted) setLoadingStatus(false);
      }
    }
    loadStatus();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResult(null);
      setErrorMsg(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith('image/')) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResult(null);
      setErrorMsg(null);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedFile) return;

    setAnalyzing(true);
    setErrorMsg(null);
    setResult(null);

    try {
      const data = await detectRoadDamage(selectedFile, confidenceThreshold);
      setResult(data);
      setViewMode('annotated');
    } catch (err: any) {
      setErrorMsg(err.message || 'Road distress detection failed.');
    } finally {
      setAnalyzing(false);
    }
  };

  const getClassBadgeColor = (code: string) => {
    switch (code) {
      case 'D00':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'D10':
        return 'bg-cyan-50 text-cyan-700 border-cyan-200';
      case 'D20':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'D40':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  const handlePrefillReport = (item?: DamageDetectionItem) => {
    if (!onPrefillHazard) return;

    const topItem = item || (result?.detections && result.detections[0]);
    const hazardType = topItem?.suggested_hazard_type || 'pothole';
    const severity = topItem?.suggested_severity || 'medium';
    const distressName = topItem?.class_name || 'Road distress';
    const classCode = topItem?.class_code || 'D40';

    onPrefillHazard({
      hazard_type: hazardType,
      severity: severity,
      title: `AI Advisory Observation: ${distressName} (${classCode})`,
      description: `Detected by YOLO Road Damage Model with ${
        topItem ? Math.round(topItem.confidence * 100) : 0
      }% confidence. Coordinates: ${
        topItem
          ? `box [xmin: ${topItem.box.xmin.toFixed(2)}, ymin: ${topItem.box.ymin.toFixed(2)}]`
          : 'N/A'
      }. Needs municipal field verification.`,
      imageFile: selectedFile || undefined,
    });
  };

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 text-xs font-semibold uppercase font-mono tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200 rounded">
                Phase 3 Active
              </span>
              <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                AI Road-Damage Detection (YOLO)
              </h2>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              Automated road surface damage localization for cracks (D00, D10, D20) and potholes (D40) with bounding box inference.
            </p>
          </div>

          {/* Model Status Badge */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl">
              <Cpu className="w-4 h-4 text-slate-600" />
              <div className="text-xs">
                <span className="text-slate-500 block">Compute Target</span>
                <span className="font-semibold text-slate-800 uppercase font-mono">
                  {modelStatus?.device || 'CPU'}
                </span>
              </div>
            </div>

            <div className={`flex items-center gap-2 px-3 py-2 border rounded-xl ${
              modelStatus?.available
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-amber-50 border-amber-200 text-amber-800'
            }`}>
              {modelStatus?.available ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-amber-600" />
              )}
              <div className="text-xs">
                <span className="block opacity-80">Model Status</span>
                <span className="font-semibold">
                  {loadingStatus
                    ? 'Checking...'
                    : modelStatus?.available
                    ? 'YOLO Online'
                    : 'Weights Pending'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Model Pending Warning Box (Non-blocking) */}
        {!loadingStatus && !modelStatus?.available && (
          <div className="mt-4 p-4 bg-amber-50/70 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start gap-3">
            <Info className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-semibold">Trained YOLO weights file is not loaded yet.</p>
              <p className="text-amber-800">
                {modelStatus?.details ||
                  'Place your trained road_damage_yolo.pt weights in backend/app/ml/artifacts/ or run the training pipeline with convert_rdd.py and train.py.'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Tri-Fold Status Guide Banner */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-sky-50/60 border border-sky-200/80 rounded-xl p-4">
          <div className="flex items-center gap-2 font-semibold text-sky-900 text-sm mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-500"></span>
            1. AI Advisory Detection
          </div>
          <p className="text-xs text-sky-800/90 leading-relaxed">
            Automated neural network inference on image pixels. Advisory triage assistance only; not an official road audit.
          </p>
        </div>

        <div className="bg-amber-50/60 border border-amber-200/80 rounded-xl p-4">
          <div className="flex items-center gap-2 font-semibold text-amber-900 text-sm mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
            2. Citizen-Submitted Report
          </div>
          <p className="text-xs text-amber-800/90 leading-relaxed">
            Self-reported observation by drivers or pedestrians with geotagged coordinates. Unverified until inspection.
          </p>
        </div>

        <div className="bg-emerald-50/60 border border-emerald-200/80 rounded-xl p-4">
          <div className="flex items-center gap-2 font-semibold text-emerald-900 text-sm mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            3. Verified Road Hazard
          </div>
          <p className="text-xs text-emerald-800/90 leading-relaxed">
            Authenticated by municipal engineers or authorized road maintenance teams for repair scheduling.
          </p>
        </div>
      </div>

      {/* Main Analysis Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Upload & Controls Column */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wider font-mono">
              Upload Road Image
            </h3>

            {/* Dropzone */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-300 hover:border-indigo-400 bg-slate-50/50 hover:bg-indigo-50/20 rounded-2xl p-6 text-center cursor-pointer transition-colors"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileChange}
                className="hidden"
              />
              <UploadCloud className="w-10 h-10 text-indigo-500 mx-auto mb-2" />
              <p className="text-sm font-medium text-slate-800">
                {selectedFile ? selectedFile.name : 'Click to select or drop road image'}
              </p>
              <p className="text-xs text-slate-500 mt-1">JPEG, PNG, or WebP up to 10 MB</p>
            </div>

            {/* Confidence Slider */}
            <div className="space-y-2 pt-2 border-t border-slate-100">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-slate-700 flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-slate-500" />
                  Confidence Threshold
                </span>
                <span className="font-mono font-semibold text-indigo-600">
                  {Math.round(confidenceThreshold * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0.10"
                max="0.80"
                step="0.05"
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                className="w-full accent-indigo-600 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                <span>10% (High Recall)</span>
                <span>80% (High Precision)</span>
              </div>
            </div>

            {/* Target Distress Classes Reference */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs space-y-1.5">
              <span className="font-semibold text-slate-700 block">Target Distress Classes:</span>
              <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                  <span className="font-mono font-medium">D00:</span> Longitudinal
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-cyan-500"></span>
                  <span className="font-mono font-medium">D10:</span> Transverse
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                  <span className="font-mono font-medium">D20:</span> Alligator
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                  <span className="font-mono font-medium">D40:</span> Pothole
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <button
              onClick={handleAnalyze}
              disabled={!selectedFile || analyzing}
              className="w-full py-3 px-4 rounded-xl font-medium text-sm text-white bg-gradient-to-r from-indigo-600 to-sky-600 hover:from-indigo-700 hover:to-sky-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-indigo-500/20 transition-all flex items-center justify-center gap-2"
            >
              {analyzing ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Running Neural Inference...
                </>
              ) : (
                <>
                  Run Road Damage Detection
                  <ChevronRight className="w-4 h-4" />
                </>
              )}
            </button>

            {errorMsg && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}
          </div>
        </div>

        {/* Results & Visualization Column */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wider font-mono flex items-center gap-2">
                <Eye className="w-4 h-4 text-indigo-600" />
                Detection Visualizer
              </h3>

              {result && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setViewMode('annotated')}
                    className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-colors ${
                      viewMode === 'annotated'
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    AI Annotated
                  </button>
                  <button
                    onClick={() => setViewMode('original')}
                    className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-colors ${
                      viewMode === 'original'
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    Original Photo
                  </button>
                </div>
              )}
            </div>

            {/* Image Canvas / Preview */}
            <div className="relative rounded-xl overflow-hidden bg-slate-900 min-h-[300px] flex items-center justify-center border border-slate-800">
              {result && viewMode === 'annotated' && result.annotated_image_url ? (
                <img
                  src={getHazardImageUrl(result.annotated_image_url) || result.annotated_image_url}
                  alt="AI Annotated Detections"
                  className="max-h-[460px] w-auto mx-auto object-contain"
                />
              ) : previewUrl ? (
                <img
                  src={previewUrl}
                  alt="Original Road Surface"
                  className="max-h-[460px] w-auto mx-auto object-contain"
                />
              ) : (
                <div className="text-center p-8 text-slate-400 text-xs">
                  <UploadCloud className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                  Select an image and click "Run Road Damage Detection" to view annotated results.
                </div>
              )}

              {analyzing && (
                <div className="absolute inset-0 bg-slate-900/70 backdrop-blur-xs flex flex-col items-center justify-center text-white space-y-2">
                  <div className="w-8 h-8 border-2 border-indigo-400/30 border-t-indigo-400 rounded-full animate-spin" />
                  <p className="text-xs font-mono">Running YOLOv8 inference on CPU...</p>
                </div>
              )}
            </div>

            {/* Detection Summary Bar */}
            {result && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs">
                  <div className="flex items-center gap-4">
                    <div>
                      <span className="text-slate-500 block">Detections Found</span>
                      <span className="font-bold text-slate-900 text-sm">
                        {result.detections_count} {result.detections_count === 1 ? 'distress' : 'distresses'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Inference Latency</span>
                      <span className="font-mono font-semibold text-slate-800 flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                        {result.inference_time_ms} ms
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Image Dimensions</span>
                      <span className="font-mono text-slate-800">
                        {result.image_width} x {result.image_height}
                      </span>
                    </div>
                  </div>

                  {/* Quick Action to File Report */}
                  {result.detections_count > 0 && onPrefillHazard && (
                    <button
                      onClick={() => handlePrefillReport()}
                      className="px-3 py-1.5 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 shadow-sm"
                    >
                      <FileText className="w-3.5 h-3.5" />
                      Prefill Citizen Report
                    </button>
                  )}
                </div>

                {/* Detections List */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider font-mono">
                    Classified Damage Items
                  </h4>
                  {result.detections.length === 0 ? (
                    <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      No road distress detected above the {Math.round(confidenceThreshold * 100)}% confidence threshold.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {result.detections.map((det, idx) => (
                        <div
                          key={idx}
                          className="p-3 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2 hover:border-indigo-300 transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <span
                              className={`px-2 py-0.5 rounded text-xs font-mono font-bold border ${getClassBadgeColor(
                                det.class_code
                              )}`}
                            >
                              {det.class_code}: {det.class_name}
                            </span>
                            <span className="text-xs font-mono font-semibold text-slate-700">
                              {Math.round(det.confidence * 100)}%
                            </span>
                          </div>

                          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="bg-indigo-600 h-1.5 rounded-full"
                              style={{ width: `${det.confidence * 100}%` }}
                            />
                          </div>

                          <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-50">
                            <span>
                              Severity:{' '}
                              <strong className="text-slate-700 uppercase font-mono">
                                {det.suggested_severity}
                              </strong>
                            </span>
                            {onPrefillHazard && (
                              <button
                                type="button"
                                onClick={() => handlePrefillReport(det)}
                                className="text-[10px] font-semibold text-sky-700 hover:text-sky-900 bg-sky-50 hover:bg-sky-100 px-2 py-0.5 rounded-md border border-sky-200 transition-colors flex items-center gap-1 cursor-pointer"
                                title="Prefill citizen report with this specific distress"
                              >
                                <FileText className="w-3 h-3 text-sky-600" />
                                <span>Report Item</span>
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Mandatory Advisory Notice Banner */}
                <div className="p-4 bg-indigo-50/70 border border-indigo-200 rounded-xl text-xs text-indigo-950 flex items-start gap-3">
                  <ShieldAlert className="w-5 h-5 text-indigo-600 flex-shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <p className="font-bold">MANDATORY ADVISORY NOTICE</p>
                    <p className="text-indigo-900/90 leading-relaxed">{result.disclaimer}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
