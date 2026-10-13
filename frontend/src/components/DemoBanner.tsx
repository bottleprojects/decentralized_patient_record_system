import { AlertTriangle } from 'lucide-react';

interface DemoBannerProps {
  className?: string;
}

export default function DemoBanner({ className = '' }: DemoBannerProps) {
  return (
    <div
      role="alert"
      className={`bg-amber-50 border border-amber-200 text-amber-900 px-4 py-2.5 rounded-lg flex items-center justify-center gap-2.5 text-xs sm:text-sm font-medium ${className}`}
    >
      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
      <span>
        <strong className="font-semibold">Demo project on a test network.</strong> Do not upload real patient data.
      </span>
    </div>
  );
}
