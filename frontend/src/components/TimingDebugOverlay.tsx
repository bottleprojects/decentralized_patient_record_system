import React, { useEffect, useState } from 'react';

interface MetricEntry {
  name: string;
  value: string;
  timestamp: string;
}

export default function TimingDebugOverlay() {
  const [enabled, setEnabled] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [metrics, setMetrics] = useState<MetricEntry[]>([]);

  useEffect(() => {
    // Only activate if ?debug=1 or debug=true in URL query params
    const params = new URLSearchParams(window.location.search);
    const isDebug = params.get('debug') === '1' || params.get('debug') === 'true';
    setEnabled(isDebug);

    if (!isDebug) return;

    console.log('[DPRMS Timing Debug] Debug mode active via ?debug=1');

    // 1. Navigation Timing Metrics (FCP, LCP, Load)
    const collectNavigationTimings = () => {
      const perfEntries = performance.getEntriesByType('navigation');
      if (perfEntries.length > 0) {
        const nav = perfEntries[0] as PerformanceNavigationTiming;
        const dnsTime = Math.round(nav.domainLookupEnd - nav.domainLookupStart);
        const tcpTime = Math.round(nav.connectEnd - nav.connectStart);
        const ttfb = Math.round(nav.responseStart - nav.requestStart);
        const totalLoad = Math.round(nav.loadEventEnd - nav.startTime);

        const newMetrics: MetricEntry[] = [
          { name: 'DNS Lookup', value: `${dnsTime} ms`, timestamp: new Date().toLocaleTimeString() },
          { name: 'TCP Connect', value: `${tcpTime} ms`, timestamp: new Date().toLocaleTimeString() },
          { name: 'TTFB (Backend Latency)', value: `${ttfb} ms`, timestamp: new Date().toLocaleTimeString() },
          { name: 'Total Page Load', value: `${totalLoad > 0 ? totalLoad : 'In Progress'} ms`, timestamp: new Date().toLocaleTimeString() }
        ];

        // Paint Timing (FCP)
        const paintEntries = performance.getEntriesByType('paint');
        paintEntries.forEach((paint) => {
          newMetrics.push({
            name: paint.name === 'first-contentful-paint' ? 'FCP' : paint.name,
            value: `${Math.round(paint.startTime)} ms`,
            timestamp: new Date().toLocaleTimeString()
          });
        });

        setMetrics((prev) => [...newMetrics, ...prev]);
        console.table(newMetrics);
      }
    };

    if (document.readyState === 'complete') {
      collectNavigationTimings();
    } else {
      window.addEventListener('load', collectNavigationTimings);
    }

    // 2. Observe Largest Contentful Paint (LCP)
    try {
      const lcpObserver = new PerformanceObserver((entryList) => {
        const entries = entryList.getEntries();
        const lastEntry = entries[entries.length - 1];
        if (lastEntry) {
          const lcpValue = Math.round(lastEntry.startTime);
          setMetrics((prev) => [
            { name: 'LCP (Largest Contentful Paint)', value: `${lcpValue} ms`, timestamp: new Date().toLocaleTimeString() },
            ...prev
          ]);
          console.log(`[DPRMS Timing Debug] LCP: ${lcpValue} ms`);
        }
      });
      lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });
    } catch (e) {
      // Observer may not be supported on all browsers
    }

    // 3. Listen for custom window event: 'dprms-benchmark-timing'
    const handleCustomTiming = (event: any) => {
      const { operation, durationMs, details } = event.detail || {};
      const entry: MetricEntry = {
        name: operation || 'Operation',
        value: `${Math.round(durationMs)} ms ${details ? `(${details})` : ''}`,
        timestamp: new Date().toLocaleTimeString()
      };
      setMetrics((prev) => [entry, ...prev.slice(0, 30)]);
      console.log(`[DPRMS Timing Debug] ${entry.name}: ${entry.value}`);
    };

    window.addEventListener('dprms-benchmark-timing', handleCustomTiming);

    return () => {
      window.removeEventListener('load', collectNavigationTimings);
      window.removeEventListener('dprms-benchmark-timing', handleCustomTiming);
    };
  }, []);

  if (!enabled) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '16px',
        right: '16px',
        zIndex: 99999,
        fontFamily: 'monospace',
        fontSize: '12px',
        maxWidth: '360px',
        width: '90vw',
        background: 'rgba(15, 23, 42, 0.92)',
        color: '#f8fafc',
        backdropFilter: 'blur(8px)',
        border: '1px solid rgba(255, 255, 255, 0.15)',
        borderRadius: '12px',
        boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
        padding: '12px',
        userSelect: 'none'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: minimized ? 0 : '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#22c55e' }} />
          <strong style={{ fontSize: '13px', color: '#38bdf8' }}>DPRMS Timing Debug</strong>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setMinimized(!minimized)}
            style={{
              background: 'rgba(255, 255, 255, 0.1)',
              border: 'none',
              color: '#94a3b8',
              borderRadius: '4px',
              padding: '2px 6px',
              cursor: 'pointer'
            }}
          >
            {minimized ? 'Expand' : 'Collapse'}
          </button>
          <button
            onClick={() => setMetrics([])}
            style={{
              background: 'rgba(255, 255, 255, 0.1)',
              border: 'none',
              color: '#94a3b8',
              borderRadius: '4px',
              padding: '2px 6px',
              cursor: 'pointer'
            }}
          >
            Clear
          </button>
        </div>
      </div>

      {!minimized && (
        <>
          <div style={{ maxHeight: '200px', overflowY: 'auto', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '6px' }}>
            {metrics.length === 0 ? (
              <p style={{ color: '#64748b', fontStyle: 'italic', margin: '4px 0' }}>Listening for measurements...</p>
            ) : (
              metrics.map((m, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <span style={{ color: '#cbd5e1' }}>{m.name}</span>
                  <span style={{ color: '#4ade80', fontWeight: 'bold' }}>{m.value}</span>
                </div>
              ))
            )}
          </div>
          <div style={{ marginTop: '8px', fontSize: '10px', color: '#64748b' }}>
            Active mode: ?debug=1 | Logs emitted to console
          </div>
        </>
      )}
    </div>
  );
}
