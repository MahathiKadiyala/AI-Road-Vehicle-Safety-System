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
  { value: 'low', label: 'Low', color: 'text-emerald-400 border-emerald-700 bg-emerald-950/50' },
  { value: 'medium', label: 'Medium', color: 'text-amber-400 border-amber-700 bg-amber-950/50' },
  { value: 'high', label: 'High', color: 'text-orange-400 border-orange-700 bg-orange-950/50' },
  { value: 'critical', label: 'Critical', color: 'text-rose-400 border-rose-700 bg-rose-950/50' },
];

export const HazardReportForm: React.FC<HazardReportFormProps> = ({
  selectedLat,
  selectedLon,
  onReportCreated,
  onRequestLocation,
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
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-amber-600 to-orange-600 flex items-center justify-center">
            <AlertTriangle className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Report a Road Hazard</h3>
            <p className="text-[10px] text-slate-400">User-submitted citizen report · Not AI-verified</p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Title */}
        <div>
          <label htmlFor="hazard-title" className="block text-xs font-medium text-slate-300 mb-1">
            Hazard Title <span className="text-rose-400">*</span>
          </label>
          <input
            id="hazard-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={150}
            placeholder="e.g. Deep pothole near bus stop"
            className="w-full bg-slate-950/60 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50 focus:border-sky-600 transition-all"
          />
        </div>

        {/* Hazard Type */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">Hazard Type</label>
          <div className="grid grid-cols-3 gap-2">
            {HAZARD_TYPES.map((ht) => (
              <button
                key={ht.value}
                type="button"
                onClick={() => setHazardType(ht.value)}
                className={`px-2 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 justify-center ${
                  hazardType === ht.value
                    ? 'bg-sky-600/20 border-sky-600 text-sky-300 shadow-sm shadow-sky-600/10'
                    : 'bg-slate-950/40 border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-300'
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
          <label className="block text-xs font-medium text-slate-300 mb-1.5">Severity Level</label>
          <div className="grid grid-cols-4 gap-2">
            {SEVERITY_LEVELS.map((sv) => (
              <button
                key={sv.value}
                type="button"
                onClick={() => setSeverity(sv.value)}
                className={`px-2 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                  severity === sv.value
                    ? sv.color + ' shadow-sm'
                    : 'bg-slate-950/40 border-slate-700 text-slate-400 hover:border-slate-600'
                }`}
              >
                {sv.label}
              </button>
            ))}
          </div>
        </div>

        {/* Location */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Location <span className="text-rose-400">*</span>
          </label>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-slate-950/60 border border-slate-700 rounded-xl px-3 py-2 text-xs font-mono text-slate-300">
              <MapPin className="w-3.5 h-3.5 text-sky-400 inline mr-1.5" />
              {selectedLat.toFixed(5)}, {selectedLon.toFixed(5)}
            </div>
            <button
              type="button"
              onClick={onRequestLocation}
              className="px-3 py-2 rounded-xl text-xs font-medium bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-white transition-all"
            >
              Pick on Map
            </button>
          </div>
          <p className="text-[10px] text-slate-500 mt-1">Click on the map above to set hazard location.</p>
        </div>

        {/* Description */}
        <div>
          <label htmlFor="hazard-desc" className="block text-xs font-medium text-slate-300 mb-1">
            Description <span className="text-slate-500">(optional)</span>
          </label>
          <textarea
            id="hazard-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            placeholder="Describe the hazard, approximate size, lane affected..."
            className="w-full bg-slate-950/60 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50 focus:border-sky-600 transition-all resize-none"
          />
        </div>

        {/* Image Upload */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Photo Evidence <span className="text-slate-500">(optional, JPEG/PNG/WebP, max 10 MB)</span>
          </label>

          {imagePreview ? (
            <div className="relative rounded-xl overflow-hidden border border-slate-700 bg-slate-950">
              <img
                src={imagePreview}
                alt="Preview"
                className="w-full h-32 object-cover"
              />
              <button
                type="button"
                onClick={clearImage}
                className="absolute top-2 right-2 bg-slate-900/80 backdrop-blur-sm p-1 rounded-lg border border-slate-700 text-slate-300 hover:text-white hover:bg-rose-900/60 transition-all"
              >
                <X className="w-4 h-4" />
              </button>
              <div className="absolute bottom-2 left-2 bg-slate-900/80 backdrop-blur-sm px-2 py-1 rounded-lg text-[10px] text-slate-300 border border-slate-700">
                <ImageIcon className="w-3 h-3 inline mr-1" />
                {imageFile?.name} ({((imageFile?.size || 0) / 1024).toFixed(0)} KB)
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="w-full border-2 border-dashed border-slate-700 rounded-xl py-6 flex flex-col items-center gap-2 text-slate-400 hover:border-sky-600 hover:text-sky-400 transition-all bg-slate-950/30"
            >
              <Camera className="w-6 h-6" />
              <span className="text-xs">Click to upload photo evidence</span>
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
          <div className="flex items-start gap-2 p-3 rounded-xl bg-rose-950/40 border border-rose-800/50 text-rose-300 text-xs">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Success Display */}
        {success && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-emerald-950/40 border border-emerald-800/50 text-emerald-300 text-xs">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>Hazard report submitted successfully! It will appear on the map shortly.</span>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={submitting || !title.trim()}
          className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all ${
            submitting || !title.trim()
              ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
              : 'bg-gradient-to-r from-sky-600 to-indigo-600 text-white hover:from-sky-500 hover:to-indigo-500 shadow-lg shadow-sky-600/20 active:scale-[0.98]'
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
          This report is classified as a <strong>citizen-submitted observation</strong>, not an AI-verified detection.
        </p>
      </form>
    </div>
  );
};
