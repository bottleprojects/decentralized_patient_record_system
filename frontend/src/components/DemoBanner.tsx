interface DemoBannerProps {
  className?: string;
}

export default function DemoBanner({ className = '' }: DemoBannerProps) {
  // Only render if explicitly requested via environment variable
  if (import.meta.env.VITE_SHOW_DEMO_BANNER !== 'true') {
    return null;
  }

  return (
    <div
      role="alert"
      className={`bg-amber-50 border border-amber-200 text-amber-900 px-4 py-2.5 rounded-lg flex items-center justify-center gap-2.5 text-xs sm:text-sm font-medium ${className}`}
    >
      <span>
        <strong className="font-semibold">Demo project on a test network.</strong> Do not upload real patient data.
      </span>
    </div>
  );
}
