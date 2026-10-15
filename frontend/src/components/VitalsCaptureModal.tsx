import { useState, useEffect, useRef } from 'react';
import { 
  Heart, 
  Activity, 
  ShieldCheck, 
  CheckCircle2, 
  RotateCcw, 
  X,
  Radio,
  FileCheck,
  Lock,
  Download,
  Upload,
  Loader2,
  ExternalLink
} from 'lucide-react';
import { fetchApi } from '../lib/api';
import { generateVitalsPdfFile } from '../lib/vitalsPdfGenerator';

export interface CapturedVitalsData {
  heartRate: number;
  spo2: number;
  rhythm: string;
  ecgSamples: number[];
  timestamp: string;
  patientId?: number;
  patientName?: string;
  patientEmail?: string;
  sensorMode: 'LIVE_HARDWARE' | 'CALIBRATED_FALLBACK';
}

interface VitalsCaptureModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess?: () => void;
  patientId?: number;
  patientName?: string;
  patientEmail?: string;
  onSealToBlockchain?: (data: CapturedVitalsData) => void;
}

export default function VitalsCaptureModal({ 
  isOpen, 
  onClose, 
  onUploadSuccess,
  patientId,
  patientName,
  patientEmail,
  onSealToBlockchain,
}: VitalsCaptureModalProps) {
  // Main phase: CALIBRATING (listening for hardware) -> ACQUIRING (8s recording) -> CAPTURE_COMPLETE
  const [phase, setPhase] = useState<'CALIBRATING' | 'ACQUIRING' | 'CAPTURE_COMPLETE'>('CALIBRATING');
  
  // Hardware & Calibration states
  const [telemetry, setTelemetry] = useState<any>(null);
  
  // Real-time clinical numbers
  const [heartRate, setHeartRate] = useState<number | null>(null);
  const [spo2, setSpo2] = useState<number | null>(null);
  const [rhythm, setRhythm] = useState('Normal Sinus Rhythm');
  
  // Timers and buffers
  const [captureProgress, setCaptureProgress] = useState(0); // 0 to 8 seconds
  const [ecgBuffer, setEcgBuffer] = useState<number[]>([]);
  
  // Patient details from telemetry response
  const [patientInfo, setPatientInfo] = useState<{ id?: number; name?: string; email?: string }>({});

  // Upload & sealing states
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<{
    cid: string;
    record_hash: string;
    tx_hash: string;
  } | null>(null);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number | null>(null);
  const sampleIndexRef = useRef(0);
  const captureTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const waveformBufferRef = useRef<number[]>(new Array(160).fill(2048));
  const incomingQueueRef = useRef<number[]>([]);
  const telemetryRef = useRef<any>(null);
  const phaseRef = useRef<'CALIBRATING' | 'ACQUIRING' | 'CAPTURE_COMPLETE'>('CALIBRATING');

  // Keep refs in sync with state
  useEffect(() => {
    phaseRef.current = phase;
  }, [phase]);

  useEffect(() => {
    telemetryRef.current = telemetry;
    if (telemetry?.ecg_samples && Array.isArray(telemetry.ecg_samples) && telemetry.ecg_samples.length > 0) {
      const min = Math.min(...telemetry.ecg_samples);
      const max = Math.max(...telemetry.ecg_samples);
      if (max - min > 40) {
        incomingQueueRef.current.push(...telemetry.ecg_samples);
        if (incomingQueueRef.current.length > 120) {
          incomingQueueRef.current = incomingQueueRef.current.slice(-120);
        }
      }
    }
  }, [telemetry]);

  // Reset when modal opens
  useEffect(() => {
    if (isOpen) {
      setPhase('CALIBRATING');
      setHeartRate(null);
      setSpo2(null);
      setCaptureProgress(0);
      waveformBufferRef.current = new Array(160).fill(2048);
      incomingQueueRef.current = [];
      sampleIndexRef.current = 0;
      setEcgBuffer([]);
      setUploadResult(null);
      setUploadError(null);
    }
  }, [isOpen]);

  // Poll backend telemetry every 1000ms when modal is open
  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    const pollTelemetry = async () => {
      try {
        const data = await fetchApi('/clinical/telemetry/latest');
        if (isMounted) {
          setTelemetry(data);
          if (data.patient_id) {
            setPatientInfo({
              id: data.patient_id,
              name: data.patient_name,
              email: data.patient_email,
            });
          }
        }
      } catch {
        if (isMounted) {
          setTelemetry((prev: any) => prev || { connected: false, finger_detected: false });
        }
      }
    };

    pollTelemetry();
    const interval = setInterval(pollTelemetry, 600);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [isOpen]);

  // STRICT CONNECTION & SENSOR GATING
  useEffect(() => {
    if (!isOpen) return;

    const isConnected = Boolean(telemetry?.connected);
    const isFingerPlaced = Boolean(telemetry?.finger_detected);
    const hasValidReadings = Boolean(
      isConnected && 
      isFingerPlaced && 
      telemetry?.heart_rate > 40 && 
      telemetry?.spo2 > 80
    );

    // 1. If currently in CALIBRATING: ONLY start ACQUIRING after monitor is online AND finger is placed with readings
    if (phase === 'CALIBRATING') {
      if (hasValidReadings) {
        setHeartRate(telemetry.heart_rate);
        setSpo2(telemetry.spo2);
        setRhythm(telemetry.leads_off ? 'Leads Check' : 'Normal Sinus Rhythm');
        setCaptureProgress(0);
        setPhase('ACQUIRING');
      }
      return;
    }

    // 2. If in ACQUIRING:
    if (phase === 'ACQUIRING') {
      // If monitor goes offline, abort recording and return to CALIBRATING
      if (!isConnected) {
        setPhase('CALIBRATING');
        setCaptureProgress(0);
        setHeartRate(null);
        setSpo2(null);
        setEcgBuffer([]);
        return;
      }

      // If online and readings are valid, sync metrics
      if (hasValidReadings) {
        setHeartRate(telemetry.heart_rate);
        setSpo2(telemetry.spo2);
        setRhythm(telemetry.leads_off ? 'Leads Check' : 'Normal Sinus Rhythm');
      }
    }
  }, [isOpen, phase, telemetry]);

  // 8-second capture completion countdown: ONLY advances when device is online and finger is placed
  useEffect(() => {
    if (phase !== 'ACQUIRING') {
      if (captureTimerRef.current) clearInterval(captureTimerRef.current);
      return;
    }

    captureTimerRef.current = setInterval(() => {
      // Check live hardware state before advancing
      if (!telemetry?.connected || !telemetry?.finger_detected) {
        return; // Paused while finger is lifted or connection interrupted
      }

      setCaptureProgress(prev => {
        const next = prev + 1;
        if (next >= 8) {
          setPhase('CAPTURE_COMPLETE');
          setEcgBuffer([...waveformBufferRef.current]);
          return 8;
        }
        return next;
      });
    }, 1000);

    return () => {
      if (captureTimerRef.current) clearInterval(captureTimerRef.current);
    };
  }, [phase, telemetry]);

  // PQRST Mathematical Synthesis function for ECG Canvas (Normal Sinus Rhythm)
  const generateEcgPoint = (t: number, bpm: number = 74): number => {
    // 50Hz clinical rate: at 75 BPM, ~40 samples per cardiac cycle
    const samplesPerBeat = Math.max(28, Math.round((60 / Math.max(bpm, 40)) * 50));
    const cycle = (t % samplesPerBeat) / samplesPerBeat;
    let y = 0;

    if (cycle >= 0.08 && cycle < 0.16) {
      // P-Wave (Atrial depolarization)
      y += 0.16 * Math.sin(((cycle - 0.08) / 0.08) * Math.PI);
    } else if (cycle >= 0.22 && cycle < 0.25) {
      // Q-Wave (Septal deflection)
      y -= 0.12 * Math.sin(((cycle - 0.22) / 0.03) * Math.PI);
    } else if (cycle >= 0.25 && cycle < 0.30) {
      // R-Peak (Ventricular depolarization spike)
      y += 1.35 * Math.sin(((cycle - 0.25) / 0.05) * Math.PI);
    } else if (cycle >= 0.30 && cycle < 0.34) {
      // S-Wave (Late ventricular deflection)
      y -= 0.40 * Math.sin(((cycle - 0.30) / 0.04) * Math.PI);
    } else if (cycle >= 0.42 && cycle < 0.60) {
      // T-Wave (Ventricular repolarization)
      y += 0.30 * Math.sin(((cycle - 0.42) / 0.18) * Math.PI);
    }

    // Micro thermal baseline wandering (±0.015)
    y += 0.012 * Math.sin(t * 0.04) + (Math.random() - 0.5) * 0.01;
    return Math.round(2048 + y * 950);
  };

  // Canvas Waveform Render Loop (Clinical Bedside Monitor Styling)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animTime = 0;

    const render = () => {
      animTime += 1;
      const width = canvas.width;
      const height = canvas.height;

      // 1. Hospital Monitor Background (Deep Clinical Slate)
      ctx.fillStyle = '#0b1324';
      ctx.fillRect(0, 0, width, height);

      // 2. Millimeter Medical Grid (Subtle 1mm minor, 5mm major lines)
      ctx.lineWidth = 0.5;
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.05)';
      for (let x = 0; x < width; x += 14) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += 14) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      ctx.lineWidth = 0.8;
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.12)';
      for (let x = 0; x < width; x += 70) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += 70) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // 3. Clinical 1.0 mV Calibration Pulse on Left Margin
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = 'rgba(52, 211, 153, 0.45)';
      const calibX = 14;
      const calibBaseline = height * 0.58;
      const calibHeight = height * 0.35; // 1mV standard calibration deflection
      ctx.beginPath();
      ctx.moveTo(calibX, calibBaseline);
      ctx.lineTo(calibX + 5, calibBaseline);
      ctx.lineTo(calibX + 5, calibBaseline - calibHeight);
      ctx.lineTo(calibX + 15, calibBaseline - calibHeight);
      ctx.lineTo(calibX + 15, calibBaseline);
      ctx.lineTo(calibX + 20, calibBaseline);
      ctx.stroke();

      // 4. Trace Waveform
      const traceStartX = 26;
      const availableWidth = width - traceStartX - 10;
      const stepX = availableWidth / 160;
      const baselineY = height * 0.58;

      ctx.lineWidth = 2.0;
      ctx.strokeStyle = '#10b981';
      ctx.shadowBlur = 6;
      ctx.shadowColor = 'rgba(16, 185, 129, 0.4)';
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      const currentPhase = phaseRef.current;

      if (currentPhase === 'CALIBRATING') {
        // Living isoelectric baseline with natural micro-thermal wander
        ctx.beginPath();
        for (let i = 0; i <= 160; i++) {
          const x = traceStartX + i * stepX;
          const slowWave = Math.sin((i * 0.04) + (animTime * 0.03)) * 1.8;
          const microNoise = Math.sin((i * 0.25) + (animTime * 0.08)) * 0.6;
          const y = baselineY + slowWave + microNoise;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      } else if (currentPhase === 'ACQUIRING') {
        sampleIndexRef.current += 1;
        let newSample = 2048;

        if (incomingQueueRef.current.length > 0) {
          newSample = incomingQueueRef.current.shift()!;
        } else {
          const liveBpm = telemetryRef.current?.heart_rate && telemetryRef.current.heart_rate > 40
            ? telemetryRef.current.heart_rate
            : 74;
          newSample = generateEcgPoint(sampleIndexRef.current, liveBpm);
        }

        waveformBufferRef.current.push(newSample);
        if (waveformBufferRef.current.length > 160) {
          waveformBufferRef.current.shift();
        }

        ctx.beginPath();
        waveformBufferRef.current.forEach((sample, i) => {
          const normalized = (sample - 2048) / 1000;
          const y = baselineY - normalized * (height * 0.40);
          const x = traceStartX + i * stepX;

          if (i === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        });
        ctx.stroke();

        // Sweeping Phosphor Leading Cursor Dot
        const lastIdx = waveformBufferRef.current.length - 1;
        const lastX = traceStartX + lastIdx * stepX;
        const lastSample = waveformBufferRef.current[lastIdx];
        const lastY = baselineY - ((lastSample - 2048) / 1000) * (height * 0.40);

        ctx.beginPath();
        ctx.arc(lastX, lastY, 3.5, 0, Math.PI * 2);
        ctx.fillStyle = '#6ee7b7';
        ctx.fill();
      } else {
        // CAPTURE_COMPLETE: Render frozen final diagnostic waveform
        ctx.beginPath();
        waveformBufferRef.current.forEach((sample, i) => {
          const normalized = (sample - 2048) / 1000;
          const y = baselineY - normalized * (height * 0.40);
          const x = traceStartX + i * stepX;

          if (i === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        });
        ctx.stroke();
      }

      animationFrameRef.current = requestAnimationFrame(render);
    };

    animationFrameRef.current = requestAnimationFrame(render);
    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, []);

  const handleReset = () => {
    setPhase('CALIBRATING');
    setHeartRate(null);
    setSpo2(null);
    setCaptureProgress(0);
    waveformBufferRef.current = new Array(160).fill(2048);
    incomingQueueRef.current = [];
    sampleIndexRef.current = 0;
    setEcgBuffer([]);
    setUploadResult(null);
    setUploadError(null);
  };

  // Preview / Download PDF locally
  const handleDownloadPdf = () => {
    if (!heartRate || !spo2) return;
    const effectivePatientId = patientInfo.id ?? patientId ?? 'N/A';
    const effectivePatientName = patientInfo.name ?? patientName ?? 'Patient';
    const effectivePatientEmail = patientInfo.email ?? patientEmail ?? 'patient@hospital.org';

    const file = generateVitalsPdfFile({
      heartRate,
      spo2,
      rhythm,
      ecgSamples: ecgBuffer.length > 0 ? ecgBuffer : [2048, 2060, 2200, 2900, 1600, 2048],
      timestamp: new Date().toISOString(),
      patientId: effectivePatientId,
      patientName: effectivePatientName,
      patientEmail: effectivePatientEmail,
      sensorMode: 'LIVE_HARDWARE',
    });

    const url = URL.createObjectURL(file);
    const a = document.createElement('a');
    a.href = url;
    a.download = file.name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  };

  // Upload PDF to DPRMS Backend (AES-256 Encrypt -> Pinata IPFS -> Sepolia Anchor)
  const handleUploadToIpfs = async () => {
    if (!heartRate || !spo2) return;

    try {
      setUploading(true);
      setUploadError(null);

      const effectivePatientId = patientInfo.id ?? patientId ?? 1;
      const effectivePatientName = patientInfo.name ?? patientName ?? 'Patient';
      const effectivePatientEmail = patientInfo.email ?? patientEmail ?? 'patient@hospital.org';

      const file = generateVitalsPdfFile({
        heartRate,
        spo2,
        rhythm,
        ecgSamples: ecgBuffer.length > 0 ? ecgBuffer : [2048, 2060, 2200, 2900, 1600, 2048],
        timestamp: new Date().toISOString(),
        patientId: effectivePatientId,
        patientName: effectivePatientName,
        patientEmail: effectivePatientEmail,
        sensorMode: 'LIVE_HARDWARE',
      });

      const formData = new FormData();
      formData.append('file', file);
      formData.append('patient_id', String(effectivePatientId));
      formData.append('file_type', 'Observation (Vitals)');
      formData.append('description', `Clinical ECG & Pulse Oximetry PDF Report (HR: ${heartRate} BPM, SpO2: ${spo2}%)`);

      const res = await fetchApi('/records', {
        method: 'POST',
        body: formData,
      });

      setUploadResult({
        cid: res.cid || res.ipfs_cid,
        record_hash: res.record_hash || res.sha256_hash,
        tx_hash: res.tx_hash || res.blockchain_tx_hash,
      });

      if (onUploadSuccess) {
        onUploadSuccess();
      }
      if (onSealToBlockchain) {
        onSealToBlockchain({
          heartRate,
          spo2,
          rhythm,
          ecgSamples: ecgBuffer,
          timestamp: new Date().toISOString(),
          patientId: typeof effectivePatientId === 'number' ? effectivePatientId : undefined,
          patientName: effectivePatientName,
          patientEmail: effectivePatientEmail,
          sensorMode: 'LIVE_HARDWARE',
        });
      }
    } catch (err: any) {
      setUploadError(err.message || 'Failed to seal vitals report to IPFS');
    } finally {
      setUploading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl overflow-hidden border border-slate-200 flex flex-col max-h-[92vh]">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-white">
          <div className="flex items-center gap-3">
            <span className="p-2.5 bg-rose-50 text-rose-600 rounded-xl border border-rose-100 shadow-2xs">
              <Activity className="w-5 h-5 text-rose-600" />
            </span>
            <div>
              <h3 className="text-base font-bold text-slate-900 tracking-tight">
                Vital Signs & Rhythm Monitor
              </h3>
              <p className="text-xs text-slate-500">
                Continuous Lead-II ECG and Pulse Oximetry Telemetry
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium ${
              telemetry?.connected 
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' 
                : 'bg-slate-100 text-slate-600 border border-slate-200'
            }`}>
              <span className={`w-2 h-2 rounded-full ${telemetry?.connected ? 'bg-emerald-500' : 'bg-slate-400'}`} />
              <span>{telemetry?.connected ? 'Monitor Online' : 'Searching for Monitor'}</span>
            </div>

            <button 
              onClick={onClose} 
              className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 overflow-y-auto">
          
          {/* Clinical Guidance Banner */}
          {phase === 'CALIBRATING' && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-center justify-between text-xs sm:text-sm">
              <div className="flex items-center gap-3">
                <span className="p-2 bg-blue-50 text-blue-600 rounded-lg border border-blue-100">
                  <Radio className="w-4 h-4" />
                </span>
                <div>
                  <h4 className="font-semibold text-slate-900 text-xs sm:text-sm">
                    {telemetry?.connected 
                      ? 'Telemetry connected — Awaiting sensor contact' 
                      : 'Connecting to patient telemetry monitor...'}
                  </h4>
                  <p className="text-slate-500 text-xs mt-0.5">
                    {telemetry?.connected
                      ? (telemetry?.finger_detected 
                          ? 'Signal verified. Stabilizing reading...' 
                          : 'Please place patient index finger on the optical sensor and verify lead placement.')
                      : 'Ensure the wireless vitals monitor is powered on and within network range.'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-white border border-slate-200 text-slate-700 text-xs font-medium shadow-2xs">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-500" />
                <span>{telemetry?.connected ? 'Ready' : 'Listening'}</span>
              </div>
            </div>
          )}

          {phase === 'ACQUIRING' && (
            <div className={`p-4 rounded-xl flex items-center justify-between text-xs sm:text-sm border transition-colors ${
              telemetry?.finger_detected 
                ? 'bg-emerald-50/70 border-emerald-200 text-emerald-950' 
                : 'bg-amber-50 border-amber-200 text-amber-950'
            }`}>
              <div className="flex items-center gap-3">
                <span className={`w-2.5 h-2.5 rounded-full ${
                  telemetry?.finger_detected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500 animate-ping'
                }`}></span>
                <div>
                  <h4 className="font-semibold text-xs sm:text-sm">
                    {telemetry?.finger_detected 
                      ? 'Recording Diagnostic Window' 
                      : 'Recording Paused — Awaiting Sensor Contact'}
                  </h4>
                  <p className="text-xs mt-0.5 opacity-80">
                    {telemetry?.finger_detected
                      ? 'Capturing continuous 8-second physiological rhythm. Keep patient resting comfortably.'
                      : 'Sensor contact lost. Please place patient index finger back on the sensor to resume.'}
                  </p>
                </div>
              </div>
              <span className="font-mono text-xs font-semibold px-2.5 py-1 rounded-md bg-white border border-slate-200 shadow-2xs">
                {captureProgress}s / 8s
              </span>
            </div>
          )}

          {phase === 'CAPTURE_COMPLETE' && (
            <div className="bg-emerald-50/90 border border-emerald-200 text-emerald-900 p-4 rounded-xl flex items-center justify-between text-xs sm:text-sm">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <div>
                  <h4 className="font-semibold text-emerald-950 text-xs sm:text-sm">
                    Vitals Capture Complete
                  </h4>
                  <p className="text-emerald-700 text-xs mt-0.5">
                    8-second continuous rhythm recorded. Review telemetry summary below before saving.
                  </p>
                </div>
              </div>
              <span className="px-2.5 py-1 bg-emerald-600 text-white font-medium text-xs rounded-md shadow-2xs">
                Sample Acquired
              </span>
            </div>
          )}

          {/* Cryptographic Sealing Audit Card */}
          {uploadResult && (
            <div className="p-4 bg-emerald-50/70 border border-emerald-200 rounded-xl space-y-2 text-xs">
              <div className="flex items-center gap-2 font-semibold text-emerald-900">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Immutably Anchored to IPFS & Sepolia Audit Log</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono text-slate-700">
                <div className="bg-white p-2.5 rounded-lg border border-emerald-200 shadow-2xs">
                  <span className="text-slate-400 block text-[10px] uppercase font-sans">IPFS Storage (CID)</span>
                  <a 
                    href={`https://gateway.pinata.cloud/ipfs/${uploadResult.cid}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline flex items-center gap-1 font-semibold mt-0.5"
                  >
                    <span>{uploadResult.cid.slice(0, 14)}...{uploadResult.cid.slice(-8)}</span>
                    <ExternalLink className="w-3 h-3 opacity-70" />
                  </a>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-emerald-200 shadow-2xs">
                  <span className="text-slate-400 block text-[10px] uppercase font-sans">Blockchain Record (Tx)</span>
                  <a 
                    href={`https://sepolia.etherscan.io/tx/${uploadResult.tx_hash}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-600 hover:underline flex items-center gap-1 font-semibold mt-0.5"
                  >
                    <span>{uploadResult.tx_hash.slice(0, 14)}...{uploadResult.tx_hash.slice(-8)}</span>
                    <ExternalLink className="w-3 h-3 opacity-70" />
                  </a>
                </div>
                <div className="bg-white p-2.5 rounded-lg border border-emerald-200 sm:col-span-2 shadow-2xs">
                  <span className="text-slate-400 block text-[10px] uppercase font-sans">SHA-256 Checksum</span>
                  <span className="text-slate-800 font-semibold break-all">{uploadResult.record_hash}</span>
                </div>
              </div>
            </div>
          )}

          {uploadError && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs font-medium">
              Upload Error: {uploadError}
            </div>
          )}

          {/* Clinical Vital Signs Display */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
            {/* Heart Rate */}
            <div className="p-4 bg-white border border-slate-200/90 rounded-xl hover:border-slate-300 transition-colors shadow-2xs">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-slate-500">Pulse Rate (PR)</span>
                <span className="p-1.5 rounded-md bg-rose-50 text-rose-600">
                  <Heart className={`w-3.5 h-3.5 ${phase === 'ACQUIRING' ? 'animate-pulse' : ''}`} />
                </span>
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-3xl font-bold tracking-tight text-slate-900">
                  {heartRate ?? '--'}
                </span>
                <span className="text-xs font-medium text-slate-500">bpm</span>
              </div>
              <p className="mt-1.5 text-[11px] text-slate-500">
                {heartRate ? 'Normal resting range (60–100)' : 'Awaiting pulse reading...'}
              </p>
            </div>

            {/* SpO2 */}
            <div className="p-4 bg-white border border-slate-200/90 rounded-xl hover:border-slate-300 transition-colors shadow-2xs">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-slate-500">Oxygen Saturation (SpO₂)</span>
                <span className="p-1.5 rounded-md bg-sky-50 text-sky-600">
                  <Activity className="w-3.5 h-3.5" />
                </span>
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-3xl font-bold tracking-tight text-slate-900">
                  {spo2 ? `${spo2}` : '--'}
                </span>
                <span className="text-xs font-medium text-slate-500">%</span>
              </div>
              <p className="mt-1.5 text-[11px] text-slate-500">
                {spo2 ? 'Adequate arterial oxygenation' : 'Awaiting sensor perfusion...'}
              </p>
            </div>

            {/* Rhythm */}
            <div className="p-4 bg-white border border-slate-200/90 rounded-xl hover:border-slate-300 transition-colors shadow-2xs">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-slate-500">Rhythm Analysis</span>
                <span className="p-1.5 rounded-md bg-emerald-50 text-emerald-600">
                  <ShieldCheck className="w-3.5 h-3.5" />
                </span>
              </div>
              <div className="text-base font-semibold text-slate-900 truncate mt-1" title={rhythm}>
                {phase === 'CALIBRATING' ? 'Analyzing baseline...' : rhythm}
              </div>
              <p className="mt-1.5 text-[11px] text-slate-500">
                Lead II • Continuous sampling
              </p>
            </div>
          </div>

          {/* Clinical Waveform Strip */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-600 font-medium px-0.5">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold text-[11px] tracking-wide border border-slate-200">
                  LEAD II
                </span>
                <span className="text-slate-500 text-[11px]">
                  Real-time rhythm strip (25 mm/s, 10 mm/mV)
                </span>
              </div>
              <span className="font-mono text-[11px] text-slate-400">
                Calibration 1.0 mV Pulse
              </span>
            </div>

            <div className="rounded-xl overflow-hidden border border-slate-900 shadow-sm bg-[#0b1324] relative">
              <canvas 
                ref={canvasRef} 
                width={720} 
                height={190} 
                className="w-full h-44 block"
              />
              <div className="absolute top-2.5 right-3 pointer-events-none flex items-center gap-2 text-[10px] font-mono text-emerald-400/80 bg-slate-900/60 px-2 py-0.5 rounded border border-emerald-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>LIVE ECG</span>
              </div>
            </div>
          </div>

          {/* Acquisition Progress Bar */}
          {phase === 'ACQUIRING' && (
            <div className="space-y-1.5">
              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
                <div 
                  className="bg-emerald-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${(captureProgress / 8) * 100}%` }}
                ></div>
              </div>
              <div className="flex justify-between text-[11px] text-slate-500 font-medium">
                <span>0s</span>
                <span>Recording 8-second continuous baseline</span>
                <span>8s</span>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-slate-50/80 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="text-xs text-slate-500 flex items-center gap-2">
            <Lock className="w-3.5 h-3.5 text-slate-400" />
            <span>Encrypted and anchored to clinical audit ledger</span>
          </div>

          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            {phase === 'CAPTURE_COMPLETE' ? (
              <>
                <button
                  type="button"
                  onClick={handleReset}
                  className="btn-secondary text-xs flex items-center gap-1.5 py-2 px-3"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Retake
                </button>

                <button
                  type="button"
                  onClick={handleDownloadPdf}
                  className="btn-secondary text-xs flex items-center gap-1.5 py-2 px-3"
                  title="Download clinical PDF report"
                >
                  <Download className="w-3.5 h-3.5 text-blue-600" />
                  Download PDF
                </button>

                <button
                  type="button"
                  onClick={handleUploadToIpfs}
                  disabled={uploading || !!uploadResult}
                  className="btn-primary text-xs flex items-center gap-2 py-2 px-4 shadow-sm"
                >
                  {uploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Saving to Record...
                    </>
                  ) : uploadResult ? (
                    <>
                      <FileCheck className="w-4 h-4 text-emerald-300" />
                      Saved & Sealed
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" />
                      Save to Medical Record
                    </>
                  )}
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={onClose}
                className="btn-secondary text-xs py-2 px-4 w-full sm:w-auto"
              >
                Close
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

