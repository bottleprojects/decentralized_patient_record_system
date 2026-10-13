import { useEffect, useState } from 'react';
import { ShieldCheck, ShieldAlert, FileText, Download, Loader2, User, FileHeart, Bell, Upload, X, Shield } from 'lucide-react';
import { fetchApi } from '../lib/api';

interface Record {
  id: number;
  file_type: string;
  description?: string;
  created_at: string;
  doctor_id: number;
  blockchain_tx_hash: string | null;
}

interface Consent {
  id: number;
  doctor_id: number;
  granted_at: string;
}

interface PendingRequest {
  id: number;
  doctor_id: number;
  doctor_name: string;
  created_at: string;
}

export default function PatientDashboard() {
  const [records, setRecords] = useState<Record[]>([]);
  const [consents, setConsents] = useState<Consent[]>([]);
  const [pendingRequests, setPendingRequests] = useState<PendingRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadType, setUploadType] = useState('General Health Record');
  const [uploading, setUploading] = useState(false);
  const [downloadingRecordId, setDownloadingRecordId] = useState<number | null>(null);
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const userData = await fetchApi('/users/me');
        setUser(userData);
        const [recordsData, consentsData, requestsData] = await Promise.all([
          fetchApi('/records'),
          fetchApi('/consent/active'),
          fetchApi('/consent/requests/pending')
        ]);
        setRecords(recordsData);
        setConsents(consentsData);
        setPendingRequests(requestsData);
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleRevoke = async (doctorId: number) => {
    try {
      await fetchApi(`/consent/revoke/${doctorId}`, { method: 'POST' });
      setConsents(consents.filter(c => c.doctor_id !== doctorId));
    } catch (err) {
      alert("Failed to revoke consent");
    }
  };

  const handleApproveRequest = async (requestId: number) => {
    try {
      await fetchApi(`/consent/requests/${requestId}/approve`, { method: 'POST' });
      setPendingRequests(pendingRequests.filter(r => r.id !== requestId));
      const consentsData = await fetchApi('/consent/active');
      setConsents(consentsData);
    } catch (err) {
      alert("Failed to approve request");
    }
  };

  const handleRejectRequest = async (requestId: number) => {
    try {
      await fetchApi(`/consent/requests/${requestId}/reject`, { method: 'POST' });
      setPendingRequests(pendingRequests.filter(r => r.id !== requestId));
    } catch (err) {
      alert("Failed to reject request");
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile || !user) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('patient_id', user.id.toString());
      formData.append('file_type', uploadType);
      formData.append('file', uploadFile);

      await fetchApi('/records', {
        method: 'POST',
        body: formData,
      });
      setIsUploadModalOpen(false);
      setUploadFile(null);
      const recordsData = await fetchApi('/records');
      setRecords(recordsData);
    } catch (err: any) {
      alert(err.message || "Failed to upload record");
    } finally {
      setUploading(false);
    }
  };

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
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center shadow-sm border border-slate-200">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
        <p className="text-slate-500 font-medium">Loading your secure health portal...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 tracking-tight">Welcome back, {user?.full_name?.split(' ')[0] || 'Patient'}</h2>
          <p className="text-slate-500 mt-1 text-sm font-medium">Manage your medical records and access permissions securely.</p>
        </div>
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <button 
            onClick={async () => {
              try {
                const bundle = await fetchApi(`/fhir/v4/Observation?patient=${user.id}`);
                const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `fhir_observations_${user.id}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
              } catch (e: any) {
                alert("Failed to export FHIR data: " + e.message);
              }
            }}
            className="w-full sm:w-auto btn-secondary flex items-center justify-center gap-2 text-sm"
          >
            <Download className="w-4 h-4" /> Export FHIR
          </button>
          <button 
            onClick={async () => {
              try {
                const data = await fetchApi('/records/export');
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `full_history_${user.id}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
              } catch (e: any) {
                alert("Failed to export history: " + e.message);
              }
            }}
            className="w-full sm:w-auto btn-secondary flex items-center justify-center gap-2 text-sm"
          >
            <Download className="w-4 h-4" /> Export History
          </button>
          <button onClick={() => setIsUploadModalOpen(true)} className="w-full sm:w-auto btn-primary flex items-center justify-center gap-2 text-sm">
            <Upload className="w-4 h-4" /> Upload Record
          </button>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="medical-card p-6 flex items-center gap-4">
          <div className="p-3 bg-blue-50 text-blue-700 rounded-lg border border-blue-100">
            <FileHeart className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Medical Records</p>
            <h3 className="text-2xl font-bold text-slate-800 mt-1">{records.length}</h3>
          </div>
        </div>
        
        <div className="medical-card p-6 flex items-center gap-4">
          <div className="p-3 bg-green-50 text-green-700 rounded-lg border border-green-100">
            <User className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Access</p>
            <h3 className="text-2xl font-bold text-slate-800 mt-1">{consents.length}</h3>
          </div>
        </div>
        
        <div className="medical-card p-6 flex items-center gap-4">
          <div className="p-3 bg-indigo-50 text-indigo-700 rounded-lg border border-indigo-100">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Verified Records</p>
            <h3 className="text-2xl font-bold text-slate-800 mt-1">
              {records.filter(r => r.blockchain_tx_hash).length}
            </h3>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Records */}
        <div className="lg:col-span-2 space-y-6">
          <div className="medical-card flex flex-col h-full">
            <div className="p-5 sm:p-6 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <FileText className="w-5 h-5 text-slate-400" /> Recent Medical Records
              </h3>
            </div>
            
            <div className="p-5 sm:p-6 flex-1">
              {records.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
                  <FileText className="w-10 h-10 text-slate-300 mb-3" />
                  <h4 className="text-slate-700 font-semibold mb-1">No medical records yet</h4>
                  <p className="text-sm text-slate-500 max-w-sm">Upload your first medical record or wait for your doctor to share one.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {records.map((record) => (
                    <div key={record.id} className="group flex flex-col sm:flex-row sm:items-center justify-between p-4 bg-white border border-slate-200 rounded-xl hover:border-blue-200 transition-all shadow-sm">
                      <div className="flex items-start gap-4 mb-4 sm:mb-0">
                        <div className="mt-1 p-2 bg-slate-50 rounded-lg border border-slate-100 shrink-0">
                          <FileText className="w-6 h-6 text-slate-400" />
                        </div>
                        <div>
                          <h4 className="font-semibold text-slate-800 leading-tight">{record.file_type || 'Clinical Document'}</h4>
                          {record.description && (
                            <p className="text-sm text-slate-600 mt-1">"{record.description}"</p>
                          )}
                          <p className="text-xs text-slate-500 font-medium mt-1">
                            {record.doctor_id ? `Uploaded by Dr. ID: ${record.doctor_id}` : 'Uploaded by You'} • {record.created_at ? new Date(record.created_at).toLocaleDateString() : 'Unknown Date'}
                          </p>
                          <div className="mt-2">
                            {record.blockchain_tx_hash ? (
                              <span className="badge badge-success gap-1">
                                <ShieldCheck className="w-3 h-3" /> Blockchain Verified
                              </span>
                            ) : (
                              <span className="badge badge-warning gap-1">
                                <ShieldAlert className="w-3 h-3" /> Pending Verification
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <button 
                        onClick={() => handleDownload(record.id)}
                        disabled={downloadingRecordId === record.id}
                        className="btn-secondary w-full sm:w-auto text-sm px-3 py-1.5 flex justify-center items-center gap-1.5"
                      >
                        {downloadingRecordId === record.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Download className="w-4 h-4" />
                        )}
                        Download
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column - Consents & Requests */}
        <div className="space-y-6">
          
          {/* Pending Requests */}
          {pendingRequests.length > 0 && (
            <div className="medical-card border-amber-200 overflow-hidden">
              <div className="bg-amber-50 p-4 border-b border-amber-100 flex items-center justify-between">
                <h3 className="text-sm font-bold text-amber-800 flex items-center gap-2">
                  <Bell className="w-4 h-4" /> Pending Access Requests
                </h3>
                <span className="bg-amber-200 text-amber-800 text-xs font-bold px-2 py-0.5 rounded-full">{pendingRequests.length}</span>
              </div>
              <div className="p-4 space-y-3 bg-white">
                {pendingRequests.map(req => (
                  <div key={req.id} className="p-3 bg-slate-50 border border-slate-100 rounded-lg">
                    <p className="text-sm font-semibold text-slate-800 mb-1">Dr. {req.doctor_name}</p>
                    <p className="text-xs text-slate-500 mb-3">Requested access to your records on {new Date(req.created_at).toLocaleDateString()}</p>
                    <div className="flex gap-2">
                      <button onClick={() => handleApproveRequest(req.id)} className="flex-1 btn-primary py-1.5 text-xs">
                        Approve
                      </button>
                      <button onClick={() => handleRejectRequest(req.id)} className="flex-1 btn-danger py-1.5 text-xs">
                        Reject
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Active Consents */}
          <div className="medical-card">
            <div className="p-5 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <Shield className="w-5 h-5 text-slate-400" /> Active Access
              </h3>
            </div>
            <div className="p-5">
              {consents.length === 0 ? (
                <div className="text-center py-6">
                  <ShieldAlert className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm text-slate-500">No doctors currently have access to your records.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {consents.map((consent) => (
                    <div key={consent.id} className="p-3 border border-slate-100 rounded-lg flex items-center justify-between hover:bg-slate-50 transition-colors">
                      <div>
                        <p className="text-sm font-bold text-slate-800">Doctor ID: {consent.doctor_id}</p>
                        <p className="text-xs text-slate-500">Granted: {new Date(consent.granted_at).toLocaleDateString()}</p>
                      </div>
                      <button onClick={() => handleRevoke(consent.doctor_id)} className="text-xs font-semibold text-red-600 hover:text-red-700 underline px-2 py-1">
                        Revoke
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

        </div>
      </div>

      {/* Upload Modal */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 modal-overlay z-[60] flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-800">Upload Medical Record</h3>
              <button onClick={() => setIsUploadModalOpen(false)} className="text-slate-400 hover:text-slate-600 p-1 rounded-md hover:bg-slate-100">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleUpload} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Document Type</label>
                <select value={uploadType} onChange={(e) => setUploadType(e.target.value)} className="input-field">
                  <option value="General Health Record">General Health Record</option>
                  <option value="Blood Test Results">Blood Test Results</option>
                  <option value="Prescription">Prescription</option>
                  <option value="X-Ray / Scan">X-Ray / Scan</option>
                  <option value="Clinical Notes">Clinical Notes</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">File</label>
                <div className="border border-slate-200 rounded-lg p-1">
                  <input type="file" required onChange={(e) => setUploadFile(e.target.files?.[0] || null)} className="w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 transition-all cursor-pointer" />
                </div>
              </div>
              <div className="pt-2">
                <button type="submit" disabled={uploading || !uploadFile} className="w-full btn-primary py-2.5">
                  {uploading ? 'Encrypting & Uploading...' : 'Secure Upload'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
