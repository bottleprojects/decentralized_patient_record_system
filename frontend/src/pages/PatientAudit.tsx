import { useEffect, useState } from 'react';
import { Clock, Loader2, FileText, CheckCircle, ShieldAlert, Upload, Shield } from 'lucide-react';
import { fetchApi } from '../lib/api';

interface AuditLog {
  id: number;
  action: string;
  resource_id: string | null;
  timestamp: string;
}

export default function PatientAudit() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const data = await fetchApi('/audit');
      setLogs(data);
    } catch (err) {
      console.error("Failed to load audit logs", err);
    } finally {
      setLoading(false);
    }
  };

  const getActionDetails = (action: string, resource_id: string | null) => {
    switch (action) {
      case 'UPLOAD_RECORD':
        return { icon: <Upload className="w-5 h-5 text-blue-600" />, text: `Uploaded a new medical record`, bg: 'bg-blue-50', border: 'border-blue-100' };
      case 'GRANT_CONSENT':
      case 'APPROVE_CONSENT_REQUEST':
        return { icon: <CheckCircle className="w-5 h-5 text-emerald-600" />, text: `Granted access to Provider #${resource_id}`, bg: 'bg-emerald-50', border: 'border-emerald-100' };
      case 'REVOKE_CONSENT':
      case 'REJECT_CONSENT_REQUEST':
        return { icon: <ShieldAlert className="w-5 h-5 text-red-600" />, text: `Revoked access for Provider #${resource_id}`, bg: 'bg-red-50', border: 'border-red-100' };
      case 'VIEW_OWN_RECORDS':
        return { icon: <FileText className="w-5 h-5 text-indigo-600" />, text: `Viewed electronic health records`, bg: 'bg-indigo-50', border: 'border-indigo-100' };
      default:
        return { icon: <Clock className="w-5 h-5 text-slate-500" />, text: `${action} (Resource ID: ${resource_id || 'N/A'})`, bg: 'bg-slate-100', border: 'border-slate-200' };
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
          <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center shadow-sm border border-slate-200">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
          </div>
          <p className="text-slate-500 font-medium">Loading security audit trail...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <div className="w-12 h-12 bg-slate-100 border border-slate-200 rounded-xl flex items-center justify-center shrink-0">
          <Shield className="w-6 h-6 text-slate-700" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-slate-800 tracking-tight">Security & Activity Log</h2>
          <p className="text-slate-500 mt-1 font-medium text-sm">
            A chronological, immutable record of all access and modifications to your account.
          </p>
        </div>
      </div>

      <div className="medical-card p-6 sm:p-8">
        <div className="space-y-6 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-slate-200">
          {logs.map((log) => {
            const { icon, text, bg, border } = getActionDetails(log.action, log.resource_id);
            return (
              <div key={log.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group">
                {/* Timeline Icon */}
                <div className={`flex items-center justify-center w-10 h-10 rounded-full border-4 border-white ${bg} shadow-sm shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10`}>
                  {icon}
                </div>
                
                {/* Event Card */}
                <div className={`w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-xl border ${border} bg-white shadow-sm hover:shadow-md transition-shadow`}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-slate-800 text-sm">{text}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    <time className="text-xs font-semibold text-slate-500">
                      {new Date(log.timestamp).toLocaleString(undefined, { 
                        year: 'numeric', 
                        month: 'short', 
                        day: 'numeric', 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </time>
                  </div>
                </div>
              </div>
            );
          })}
          
          {logs.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 px-4 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200 relative z-10">
              <Clock className="w-10 h-10 text-slate-300 mb-3" />
              <h4 className="text-slate-700 font-semibold mb-1">No activities logged yet</h4>
              <p className="text-sm text-slate-500 max-w-sm">When you or a doctor interact with your records, the activity will appear here securely.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
