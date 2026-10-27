import React, { useState, useRef, useCallback } from 'react';
import { HazardType, HazardSeverity } from '../../types';
import { createHazardReport } from '../../services/api';
import {
  Camera,
  Send,
  X,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  MapPin,
  ImageIcon,
} from 'lucide-react';

interface HazardReportFormProps {
  selectedLat: number;
  selectedLon: number;
  onReportCreated: () => void;
  onRequestLocation: () => void;
  prefill?: {
    title?: string;
    description?: string;
    hazard_type?: HazardType;
    severity?: HazardSeverity;
    imageFile?: File;
  } | null;
}

const HAZARD_TYPES: { value: HazardType; label: string; emoji: string }[] = [
  { value: 'pothole', label: 'Pothole', emoji: '🕳️' },
  { value: 'crack', label: 'Crack', emoji: '⚡' },
  { value: 'debris', label: 'Debris', emoji: '🪨' },
  { value: 'waterlogging', label: 'Waterlogging', emoji: '🌊' },
  { value: 'obstacle', label: 'Obstacle', emoji: '🚧' },
  { value: 'other', label: 'Other', emoji: '⚠️' },
];

const SEVERITY_LEVELS: { value: HazardSeverity; label: string; color: string }[] = [
  { value: 'low', label: 'Low', color: 'text-emerald-700 border-emerald-300 bg-emerald-50 font-semibold' },
  { value: 'medium', label: 'Medium', color: 'text-amber-800 border-amber-300 bg-amber-50 font-semibold' },
  { value: 'high', label: 'High', color: 'text-orange-800 border-orange-300 bg-orange-50 font-semibold' },
  { value: 'critical', label: 'Critical', color: 'text-rose-700 border-rose-300 bg-rose-50 font-semibold' },
];

export const HazardReportForm: React.FC<HazardReportFormProps> = ({
  selectedLat,
  selectedLon,
  onReportCreated,
  onRequestLocation,
  prefill,
}) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [hazardType, setHazardType] = useState<HazardType>('pothole');
  const [severity, setSeverity] = useState<HazardSeverity>('medium');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync prefilled data if provided (e.g. from AI Road Damage detection)
  React.useEffect(() => {
    if (prefill) {
      if (prefill.title) setTitle(prefill.title);
      if (prefill.description) setDescription(prefill.description);
      if (prefill.hazard_type) setHazardType(prefill.hazard_type);
      if (prefill.severity) setSeverity(prefill.severity);
      if (prefill.imageFile) {
        setImageFile(prefill.imageFile);
        setImagePreview(URL.createObjectURL(prefill.imageFile));
      }
    }
  }, [prefill]);

  const handleImageSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Client-side file type check
    const allowed = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowed.includes(file.type)) {
      setError('Please select a JPEG, PNG, or WebP image.');
      return;
    }

    // Client-side size check (10 MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('Image must be under 10 MB.');
      return;
    }

    setImageFile(file);
    setError(null);

    // Generate preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  }, []);

  const clearImage = useCallback(() => {
    setImageFile(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  const resetForm = useCallback(() => {
    setTitle('');
    setDescription('');
    setHazardType('pothole');
    setSeverity('medium');
    clearImage();
    setError(null);
    setSuccess(false);
  }, [clearImage]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    // Client-side validation
    if (!title.trim()) {
      setError('Title is required.');
      return;
    }
    if (selectedLat === 0 && selectedLon === 0) {
      setError('Please click the map to select a location for this hazard.');
      return;
    }

    setSubmitting(true);
    try {
      await createHazardReport({
        title: title.trim(),
        description: description.trim() || undefined,
        hazard_type: hazardType,
        severity,
        latitude: selectedLat,
        longitude: selectedLon,
        image: imageFile,
      });
      setSuccess(true);
      resetForm();
      onReportCreated();

      // Auto-dismiss success message
      setTimeout(() => setSuccess(false), 4000);
    } catch (err: any) {
      setError(err.message || 'Failed to submit report. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
      <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-5">
        <div className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-amber-500 to-orange-500 flex items-center justify-center shadow-sm">
            <AlertTriangle className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">Report a Road Hazard</h3>
            <p className="text-[11px] text-slate-500">Citizen-submitted observation · Not an AI-verified detection</p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Title */}
        <div>
          <label htmlFor="hazard-title" className="block text-xs font-semibold text-slate-700 mb-1.5">
            Hazard Title <span className="text-rose-500">*</span>
          </label>
          <input
            id="hazard-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={150}
            placeholder="e.g. Deep pothole near inner ring road"
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 focus:bg-white transition-all"
          />
        </div>

        {/* Hazard Type */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">Hazard Type</label>
          <div className="grid grid-cols-3 gap-2">
            {HAZARD_TYPES.map((ht) => (
              <button
                key={ht.value}
                type="button"
                onClick={() => setHazardType(ht.value)}
                className={`px-2.5 py-2 rounded-xl text-xs font-medium border transition-all flex items-center gap-1.5 justify-center ${
                  hazardType === ht.value
                    ? 'bg-sky-50 border-sky-300 text-sky-800 shadow-sm font-semibold'
                    : 'bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300 hover:text-slate-900'
                }`}
              >
                <span>{ht.emoji}</span>
                {ht.label}
              </button>
            ))}
          </div>
        </div>

        {/* Severity */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">Severity Level</label>
          <div className="grid grid-cols-4 gap-2">
            {SEVERITY_LEVELS.map((sv) => (
              <button
                key={sv.value}
                type="button"
                onClick={() => setSeverity(sv.value)}
                className={`px-2 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                  severity === sv.value
                    ? sv.color + ' shadow-sm'
                    : 'bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300 hover:text-slate-900'
                }`}
              >
                {sv.label}
              </button>
            ))}
          </div>
        </div>

        {/* Location */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Location <span className="text-rose-500">*</span>
          </label>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-xs font-mono text-slate-700 font-medium">
              <MapPin className="w-3.5 h-3.5 text-sky-600 inline mr-1.5" />
              {selectedLat.toFixed(5)}, {selectedLon.toFixed(5)}
            </div>
            <button
              type="button"
              onClick={onRequestLocation}
              className="px-3.5 py-2.5 rounded-xl text-xs font-semibold bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 hover:text-slate-900 shadow-sm transition-all"
            >
              Pick on Map
            </button>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Click anywhere on the map above to update these coordinates.</p>
        </div>

        {/* Description */}
        <div>
          <label htmlFor="hazard-desc" className="block text-xs font-semibold text-slate-700 mb-1.5">
            Description <span className="text-slate-400 font-normal">(optional)</span>
          </label>
          <textarea
            id="hazard-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            placeholder="Describe the hazard dimensions, lane obstruction, or surrounding landmarks..."
            className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 focus:bg-white transition-all resize-none"
          />
        </div>

        {/* Image Upload */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Photo Evidence <span className="text-slate-400 font-normal">(optional, JPEG/PNG/WebP, max 10 MB)</span>
          </label>

          {imagePreview ? (
            <div className="relative rounded-xl overflow-hidden border border-slate-200 bg-slate-100">
              <img
                src={imagePreview}
                alt="Preview"
                className="w-full h-36 object-cover"
              />
              <button
                type="button"
                onClick={clearImage}
                aria-label="Remove image"
                className="absolute top-2.5 right-2.5 bg-white/90 backdrop-blur-sm p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:text-rose-600 hover:bg-rose-50 transition-all shadow-sm"
              >
                <X className="w-4 h-4" />
              </button>
              <div className="absolute bottom-2.5 left-2.5 bg-white/90 backdrop-blur-sm px-2.5 py-1 rounded-lg text-[11px] text-slate-700 border border-slate-200 font-mono shadow-sm">
                <ImageIcon className="w-3.5 h-3.5 inline mr-1 text-sky-600" />
                {imageFile?.name} ({((imageFile?.size || 0) / 1024).toFixed(0)} KB)
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="w-full border-2 border-dashed border-slate-200 rounded-xl py-6 flex flex-col items-center gap-2 text-slate-500 hover:border-sky-400 hover:text-sky-600 hover:bg-sky-50/20 transition-all bg-slate-50/50"
            >
              <Camera className="w-6 h-6 text-slate-400" />
              <span className="text-xs font-medium">Click to upload photo evidence</span>
            </button>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleImageSelect}
            className="hidden"
          />
        </div>

        {/* Error Display */}
        {error && (
          <div className="flex items-start gap-2.5 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600" />
            <span>{error}</span>
          </div>
        )}

        {/* Success Display */}
        {success && (
          <div className="flex items-center gap-2.5 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
            <span>Hazard report submitted successfully! The marker is now visible on the map.</span>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={submitting || !title.trim()}
          className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all ${
            submitting || !title.trim()
              ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
              : 'bg-gradient-to-r from-sky-600 to-indigo-600 text-white hover:from-sky-500 hover:to-indigo-500 shadow-md shadow-sky-600/20 active:scale-[0.99]'
          }`}
        >
          {submitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Submitting Report...
            </>
          ) : (
            <>
              <Send className="w-4 h-4" />
              Submit Citizen Report
            </>
          )}
        </button>

        <p className="text-[10px] text-slate-500 text-center">
          Submitted records are saved as <strong>citizen observations</strong> for municipal review, not certified AI classifications.
        </p>
      </form>
    </div>
  );
};
