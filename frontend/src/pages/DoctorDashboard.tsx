import { useEffect, useState, useRef } from 'react';
import { Search, CheckCircle2, Upload, Loader2, FileCheck, Users, ShieldAlert, UserPlus, ArrowRight, X } from 'lucide-react';
import { fetchApi } from '../lib/api';
import { useNavigate } from 'react-router-dom';

interface Record {
  id: number;
  file_type: string;
  created_at: string;
  patient_id: number;
  blockchain_tx_hash: string | null;
}

export default function DoctorDashboard() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [records, setRecords] = useState<Record[]>([]);
  const [patients, setPatients] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Upload State
  const [uploadPatientId, setUploadPatientId] = useState('');
  const [entryMode, setEntryMode] = useState('Other');
  const [uploadDescription, setUploadDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Search Dropdown State
  const [isSearchFocused, setIsSearchFocused] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setIsSearchFocused(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const [patientSearchQuery, setPatientSearchQuery] = useState('');
  
  // Emergency Access State
  const [showEmergencyModal, setShowEmergencyModal] = useState(false);
  const [emergencySearch, setEmergencySearch] = useState('');
  const [emergencyPatientId, setEmergencyPatientId] = useState('');
  const [emergencyJustification, setEmergencyJustification] = useState('');
  const [emergencyLoading, setEmergencyLoading] = useState(false);

  const fetchRecords = async () => {
    try {
      const [recordsData, patientsData] = await Promise.all([
        fetchApi('/records'),
        fetchApi('/users/patients')
      ]);
      setRecords(recordsData);
      setPatients(patientsData);
    } catch (err) {
      console.error("Failed to fetch records:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadPatientId) {
      alert("Please select a patient");
      return;
    }
    if (!fileInputRef.current?.files?.[0]) {
      alert("Please select a file to upload");
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('patient_id', uploadPatientId);
      formData.append('file_type', entryMode);
      if (uploadDescription) formData.append('description', uploadDescription);
      formData.append('file', fileInputRef.current.files[0]);

      await fetchApi('/records', {
        method: 'POST',
        body: formData,
      });
      alert('Record encrypted and uploaded successfully!');
      if (fileInputRef.current) fileInputRef.current.value = '';
      setUploadPatientId('');
      setUploadDescription('');
      fetchRecords();
    } catch (err: any) {
      alert(err.message || 'Upload failed. Check if patient has granted you consent.');
    } finally {
      setUploading(false);
    }
  };

  const handleRequestConsent = async (patientId: number) => {
    try {
      const res = await fetchApi(`/consent/request/${patientId}`, { method: 'POST' });
      alert(res.message);
      setPatients(patients.map(pat => pat.id === patientId ? {...pat, consent_status: 'pending'} : pat));
    } catch (err: any) {
      alert(err.message || 'Failed to request consent');
    }
  };

  const handleEmergencyAccess = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emergencyPatientId) {
      alert("Please select a patient from the search results");
      return;
    }
    setEmergencyLoading(true);
    try {
      const res = await fetchApi('/consent/emergency', {
        method: 'POST',
        body: JSON.stringify({
          patient_id: parseInt(emergencyPatientId),
          justification: emergencyJustification
        })
      });
      alert(res.message);
      setShowEmergencyModal(false);
      setEmergencyPatientId('');
      setEmergencySearch('');
      setEmergencyJustification('');
      fetchRecords();
    } catch (err: any) {
      alert(err.message || 'Failed to request emergency access');
    } finally {
      setEmergencyLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center shadow-sm border border-slate-200">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
        <p className="text-slate-500 font-medium">Loading clinical workspace...</p>
      </div>
    );
  }

  const consentedPatients = patients.filter(p => p.consent_status === 'granted');
  
  const dashboardFilteredPatients = consentedPatients.filter(p => 
    p.full_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    p.id.toString().includes(searchQuery)
  );

  const accessSearchFilteredPatients = patients.filter(p =>
    p.id.toString().includes(patientSearchQuery) ||
    p.full_name.toLowerCase().includes(patientSearchQuery.toLowerCase()) ||
    p.email.toLowerCase().includes(patientSearchQuery.toLowerCase())
  ).slice(0, 3);

  const emergencyFilteredPatients = emergencySearch ? patients.filter(p => 
    p.full_name.toLowerCase().includes(emergencySearch.toLowerCase()) || 
    p.id.toString().includes(emergencySearch)
  ).slice(0, 5) : [];

  return (
    <div className="space-y-6">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-2xl font-bold text-slate-800 tracking-tight">Clinical Workspace</h2>
          </div>
          <p className="text-slate-500 font-medium text-sm">Manage patients, upload secure records, and request access.</p>
        </div>
        
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <div className="relative w-full sm:w-64 z-20" ref={searchRef}>
            <input 
              type="text" 
              placeholder="Search My Patients..."
              className="input-field !pl-10 !py-2.5"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setIsSearchFocused(true)}
            />
            <Search className="w-5 h-5 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
            
            {isSearchFocused && searchQuery && (
              <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden">
                {dashboardFilteredPatients.length > 0 ? (
                  <div className="max-h-64 overflow-y-auto divide-y divide-slate-100">
                    {dashboardFilteredPatients.map(p => (
                      <div 
                        key={p.id}
                        onClick={() => navigate(`/doctor/patient/${p.id}`)}
                        className="px-4 py-3 hover:bg-slate-50 cursor-pointer transition-colors"
                      >
                        <p className="font-bold text-slate-800 text-sm">{p.full_name}</p>
                        <p className="text-xs text-slate-500">Patient ID: {p.id}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="px-4 py-6 text-center text-sm text-slate-500">
                    No authorized patients found.
                  </div>
                )}
              </div>
            )}
          </div>
          
          <button 
            onClick={() => setShowEmergencyModal(true)}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2.5 bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 font-semibold rounded-lg transition-colors"
          >
            <ShieldAlert className="w-4 h-4" /> Emergency Access
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Upload Panel */}
        <div className="medical-card">
          <div className="p-5 sm:p-6 border-b border-slate-100 flex items-start gap-4">
            <div className="w-10 h-10 bg-blue-50 border border-blue-100 rounded-lg flex items-center justify-center shrink-0">
              <Upload className="w-5 h-5 text-blue-700" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-800">Secure Document Upload</h3>
              <p className="text-sm text-slate-500 mt-1">Upload records for patients in your care.</p>
            </div>
          </div>
          
          <div className="p-5 sm:p-6">
            <form onSubmit={handleUpload} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1.5 uppercase tracking-wider">Patient</label>
                  <select 
                    required
                    value={uploadPatientId}
                    onChange={e => setUploadPatientId(e.target.value)}
                    className="input-field !py-2"
                  >
                    <option value="" disabled>Select patient</option>
                    {consentedPatients.map(p => (
                      <option key={p.id} value={p.id}>{p.full_name} (ID: {p.id})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1.5 uppercase tracking-wider">Document Type</label>
                  <select 
                    value={entryMode} 
                    onChange={e => setEntryMode(e.target.value)} 
                    className="input-field !py-2"
                  >
                    <option>Observation (Vitals)</option>
                    <option>Diagnosis</option>
                    <option>Prescription</option>
                    <option>Lab Results</option>
                    <option>Other</option>
                  </select>
                </div>
              </div>
              
              {entryMode === 'Other' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1.5 uppercase tracking-wider">Clinical Notes</label>
                  <textarea 
                    required
                    placeholder="Enter clinical description..."
                    className="input-field min-h-[80px]"
                    value={uploadDescription}
                    onChange={e => setUploadDescription(e.target.value)}
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1.5 uppercase tracking-wider">File Attachment</label>
                <div className="border border-slate-200 rounded-lg p-1">
                  <input type="file" required ref={fileInputRef} className="w-full text-sm text-slate-500 bg-white file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 transition-all cursor-pointer" />
                </div>
              </div>
              
              <button type="submit" disabled={uploading} className="w-full btn-primary py-2.5 mt-4">
                {uploading ? (
                  <span className="flex items-center justify-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Processing...</span>
                ) : (
                  'Upload & Cryptographically Seal'
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Request Access Panel */}
        <div className="medical-card flex flex-col">
          <div className="p-5 sm:p-6 border-b border-slate-100 flex items-start gap-4">
            <div className="w-10 h-10 bg-emerald-50 border border-emerald-100 rounded-lg flex items-center justify-center shrink-0">
              <UserPlus className="w-5 h-5 text-emerald-700" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-800">Request Patient Access</h3>
              <p className="text-sm text-slate-500 mt-1">Search the registry for new patients.</p>
            </div>
          </div>
          
          <div className="p-5 sm:p-6 flex flex-col flex-1">
            <div className="relative mb-4">
              <input 
                type="text" 
                placeholder="Search by name, ID, or email..."
                className="input-field !pl-10"
                value={patientSearchQuery}
                onChange={(e) => setPatientSearchQuery(e.target.value)}
              />
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
            </div>

            <div className="space-y-3 flex-1 overflow-y-auto">
              {patientSearchQuery && accessSearchFilteredPatients.length === 0 && (
                <p className="text-sm text-slate-500 text-center py-4">No patients found matching criteria.</p>
              )}
              {patientSearchQuery && accessSearchFilteredPatients.map(p => (
                <div key={p.id} className="flex flex-col sm:flex-row sm:items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-lg gap-3">
                  <div className="min-w-0">
                    <p className="font-bold text-slate-800 text-sm truncate">{p.full_name}</p>
                    <p className="text-xs text-slate-500 truncate">ID: {p.id}</p>
                  </div>
                  {p.consent_status === 'granted' ? (
                    <span className="w-full sm:w-auto px-3 py-1 bg-blue-100 text-blue-700 font-semibold rounded text-xs text-center border border-blue-200">
                      Authorized
                    </span>
                  ) : p.consent_status === 'pending' ? (
                    <span className="w-full sm:w-auto px-3 py-1 bg-amber-100 text-amber-700 font-semibold rounded text-xs text-center border border-amber-200">
                      Pending
                    </span>
                  ) : (
                    <button onClick={() => handleRequestConsent(p.id)} className="w-full sm:w-auto px-3 py-1.5 bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 font-semibold rounded text-xs transition-colors shrink-0">
                      Request Access
                    </button>
                  )}
                </div>
              ))}
              {!patientSearchQuery && (
                <div className="flex flex-col items-center justify-center h-full text-center py-8">
                  <FileCheck className="w-12 h-12 text-slate-200 mb-3" />
                  <p className="text-sm text-slate-500">
                    Enter details above to find a patient in the system.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Authorized Patients Table */}
      <div className="medical-card mt-8">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-lg font-bold text-slate-800">My Patients</h3>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 text-slate-600 text-xs font-bold rounded-md">
            <Users className="w-3.5 h-3.5" /> {dashboardFilteredPatients.length}
          </span>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-xs text-slate-500 uppercase tracking-wider font-semibold">
                <th className="py-3 px-6">ID</th>
                <th className="py-3 px-6">Name</th>
                <th className="py-3 px-6">Contact</th>
                <th className="py-3 px-6 text-center">Clinical Records</th>
                <th className="py-3 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {dashboardFilteredPatients.map((patient) => {
                const patientRecordsCount = records.filter(r => r.patient_id === patient.id).length;
                return (
                  <tr key={patient.id} onClick={() => navigate(`/doctor/patient/${patient.id}`)} className="border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer">
                    <td className="py-3 px-6 text-sm font-medium text-slate-600">
                      {patient.id}
                    </td>
                    <td className="py-3 px-6 text-sm font-bold text-slate-800">{patient.full_name}</td>
                    <td className="py-3 px-6 text-sm text-slate-500">{patient.email}</td>
                    <td className="py-3 px-6 text-sm text-center">
                      <span className="px-2 py-1 bg-slate-100 text-slate-600 rounded text-xs font-semibold">{patientRecordsCount}</span>
                    </td>
                    <td className="py-3 px-6 text-right">
                      <button className="inline-flex items-center gap-1 text-blue-600 font-semibold text-sm hover:text-blue-800 transition-colors">
                        View <ArrowRight className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
              
              {dashboardFilteredPatients.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-12 px-6 text-center">
                    <div className="flex flex-col items-center justify-center">
                      <Users className="w-10 h-10 text-slate-300 mb-3" />
                      <p className="text-slate-600 font-semibold">No patients found</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Emergency Access Modal */}
      {showEmergencyModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center modal-overlay p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden relative border-t-4 border-red-600 animate-in fade-in zoom-in duration-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-red-50/50">
              <h3 className="text-lg font-bold text-red-800 flex items-center gap-2">
                <ShieldAlert className="w-5 h-5" /> Break-Glass Access
              </h3>
              <button onClick={() => setShowEmergencyModal(false)} className="text-red-400 hover:text-red-600 p-1 rounded-md hover:bg-red-100">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="px-6 py-3 bg-red-50 border-b border-red-100 text-xs text-red-700">
              <strong>Warning:</strong> Use only in life-threatening situations. All emergency access is permanently logged in the audit trail.
            </div>
            <form onSubmit={handleEmergencyAccess} className="p-6 space-y-4 bg-white">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Locate Patient</label>
                <div className="relative">
                  <input 
                    type="text" 
                    placeholder="Search registry..."
                    className="input-field !pl-9"
                    value={emergencySearch}
                    onChange={e => {
                      setEmergencySearch(e.target.value);
                      setEmergencyPatientId('');
                    }}
                  />
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3.5" />
                </div>
                
                {emergencySearch && !emergencyPatientId && (
                  <div className="mt-2 max-h-32 overflow-y-auto border border-slate-200 rounded-lg bg-slate-50 divide-y divide-slate-100">
                    {emergencyFilteredPatients.length > 0 ? emergencyFilteredPatients.map(p => (
                      <div 
                        key={p.id} 
                        onClick={() => {
                          setEmergencyPatientId(p.id.toString());
                          setEmergencySearch(`${p.full_name} (ID: ${p.id})`);
                        }}
                        className="px-3 py-2 cursor-pointer hover:bg-blue-50 transition-colors flex justify-between items-center"
                      >
                        <span className="font-semibold text-slate-700 text-sm">{p.full_name}</span>
                        <span className="text-xs text-slate-500 bg-slate-200 px-2 py-0.5 rounded">ID: {p.id}</span>
                      </div>
                    )) : (
                      <div className="px-3 py-2 text-sm text-slate-500 text-center">No matching patients found.</div>
                    )}
                  </div>
                )}
                
                {emergencyPatientId && (
                  <div className="mt-2 text-xs text-emerald-600 font-semibold flex items-center gap-1 bg-emerald-50 p-2 rounded border border-emerald-100">
                    <CheckCircle2 className="w-4 h-4" /> Selected Patient ID: {emergencyPatientId}
                  </div>
                )}
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Clinical Justification (Required)</label>
                <textarea 
                  required
                  placeholder="State the medical necessity for emergency override..."
                  className="input-field min-h-[100px] resize-y"
                  value={emergencyJustification}
                  onChange={e => setEmergencyJustification(e.target.value)}
                ></textarea>
              </div>
              <div className="pt-4 flex gap-3">
                <button type="button" onClick={() => setShowEmergencyModal(false)} className="flex-1 btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={emergencyLoading || !emergencyPatientId} className="flex-1 btn-danger flex items-center justify-center">
                  {emergencyLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Override Access'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
