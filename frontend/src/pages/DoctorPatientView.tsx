import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, Loader2, Clock, FileDown, FileText } from 'lucide-react';
import { fetchApi } from '../lib/api';

interface Record {
  id: number;
  file_type: string;
  description?: string;
  created_at: string;
  patient_id: number;
  blockchain_tx_hash: string | null;
}

export default function DoctorPatientView() {
  const { id } = useParams<{ id: string }>();
  const [records, setRecords] = useState<Record[]>([]);
  const [patientInfo, setPatientInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [downloadingRecordId, setDownloadingRecordId] = useState<number | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [recordsData, patientsData] = await Promise.all([
          fetchApi('/records'),
          fetchApi('/users/patients')
        ]);
        
        const patientRecords = recordsData.filter((r: Record) => r.patient_id.toString() === id);
        setRecords(patientRecords);
        
        const patient = patientsData.find((p: any) => p.id.toString() === id);
        setPatientInfo(patient);
      } catch (err) {
        console.error("Failed to fetch patient data:", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [id]);

  const handleDownload = async (recordId: number) => {
    try {
      setDownloadingRecordId(recordId);
      
      const token = localStorage.getItem('access_token');
      const apiUrl = import.meta.env.DEV ? 'http://localhost:8000' : 'https://backend-production-30645.up.railway.app';
      const response = await fetch(`${apiUrl}/records/${recordId}/download`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Download failed');
      }
      
      let filename = `record_${recordId}.enc`;
      const disposition = response.headers.get('Content-Disposition');
      if (disposition && disposition.indexOf('filename=') !== -1) {
        const matches = /filename="([^"]*)"/.exec(disposition);
        if (matches != null && matches[1]) filename = matches[1];
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.message || 'Failed to download record');
    } finally {
      setDownloadingRecordId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
          <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center shadow-sm border border-slate-200">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
          </div>
          <p className="text-slate-500 font-medium">Loading patient electronic records...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Link to="/doctor" className="p-2.5 bg-white border border-slate-200 text-slate-500 hover:text-slate-800 hover:bg-slate-50 rounded-lg transition-colors shadow-sm">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h2 className="text-2xl font-bold text-slate-800 tracking-tight flex items-center gap-2">
            {patientInfo ? patientInfo.full_name : `Patient #${id}`} 
            <span className="text-sm font-semibold text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded-full ml-2 border border-slate-200">
              ID: {id}
            </span>
          </h2>
          <p className="text-slate-500 font-medium text-sm mt-1">
            Securely access and review complete medical history.
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="medical-card">
        <div className="p-5 sm:p-6 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <FileText className="w-5 h-5 text-slate-400" /> Patient Medical History
          </h3>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-50 text-blue-700 text-xs font-bold rounded-full border border-blue-100">
            {records.length} Documents
          </span>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-xs text-slate-500 uppercase tracking-wider font-semibold">
                <th className="py-4 px-6">Record ID</th>
                <th className="py-4 px-6">Document Type</th>
                <th className="py-4 px-6">Upload Date</th>
                <th className="py-4 px-6">Blockchain Status</th>
                <th className="py-4 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {records.map((record) => (
                <tr key={record.id} className="hover:bg-slate-50 transition-colors">
                  <td className="py-4 px-6 text-sm font-semibold text-slate-600 font-mono">#{record.id}</td>
                  <td className="py-4 px-6">
                    <p className="text-sm font-bold text-slate-800">{record.file_type}</p>
                    {record.description && (
                      <p className="text-xs text-slate-500 mt-1 max-w-xs">{record.description}</p>
                    )}
                  </td>
                  <td className="py-4 px-6 text-sm text-slate-600 font-medium">
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-4 h-4 text-slate-400" />
                      {new Date(record.created_at).toLocaleDateString()}
                    </div>
                  </td>
                  <td className="py-4 px-6">
                    {record.blockchain_tx_hash ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Verified
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" /> Pending
                      </span>
                    )}
                  </td>
                  <td className="py-4 px-6 text-right">
                    <button 
                      onClick={() => handleDownload(record.id)}
                      disabled={downloadingRecordId === record.id}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 btn-secondary text-sm font-semibold disabled:opacity-50"
                    >
                      {downloadingRecordId === record.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <FileDown className="w-4 h-4" />
                      )}
                      Download
                    </button>
                  </td>
                </tr>
              ))}
              
              {records.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-12 px-6 text-center">
                    <div className="flex flex-col items-center justify-center">
                      <FileText className="w-10 h-10 text-slate-300 mb-3" />
                      <p className="text-slate-600 font-semibold">No records found</p>
                      <p className="text-sm text-slate-500 mt-1">This patient does not have any medical documents yet.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
