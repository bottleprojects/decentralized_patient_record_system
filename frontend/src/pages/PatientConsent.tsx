import { useEffect, useState } from 'react';
import { Shield, Search, Loader2, CheckCircle, ShieldAlert, Stethoscope } from 'lucide-react';
import { fetchApi } from '../lib/api';

export default function PatientConsent() {
  const [doctors, setDoctors] = useState<any[]>([]);
  const [consents, setConsents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [doctorsData, consentsData] = await Promise.all([
        fetchApi('/users/doctors'),
        fetchApi('/consent/active')
      ]);
      setDoctors(doctorsData);
      setConsents(consentsData);
    } catch (err) {
      console.error("Failed to load consent data", err);
    } finally {
      setLoading(false);
    }
  };

  const handleGrantConsent = async (doctorId: number) => {
    try {
      await fetchApi(`/consent/grant/${doctorId}`, { method: 'POST' });
      loadData();
    } catch (err: any) {
      alert(err.message || "Failed to grant consent");
    }
  };

  const handleRevokeConsent = async (doctorId: number) => {
    try {
      await fetchApi(`/consent/revoke/${doctorId}`, { method: 'POST' });
      loadData();
    } catch (err: any) {
      alert(err.message || "Failed to revoke consent");
    }
  };

  const filteredDoctors = doctors.filter(d => 
    d.full_name.toLowerCase().includes(search.toLowerCase()) || 
    d.email.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
          <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center shadow-sm border border-slate-200">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
          </div>
          <p className="text-slate-500 font-medium">Loading medical personnel registry...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <div className="w-12 h-12 bg-indigo-50 border border-indigo-100 rounded-xl flex items-center justify-center shrink-0">
          <Shield className="w-6 h-6 text-indigo-700" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-slate-800 tracking-tight">Consent Management</h2>
          <p className="text-slate-500 mt-1 font-medium text-sm">
            Proactively manage which healthcare providers can access your secure records.
          </p>
        </div>
      </div>

      <div className="medical-card">
        <div className="p-5 sm:p-6 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <Stethoscope className="w-5 h-5 text-slate-400" /> Healthcare Provider Directory
          </h3>
        </div>
        
        <div className="p-5 sm:p-6">
          <div className="relative mb-6">
            <Search className="w-5 h-5 absolute left-3.5 top-3 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search providers by name or email..." 
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="input-field !pl-11"
            />
          </div>

          <div className="space-y-3">
            {filteredDoctors.map(doctor => {
              const hasConsent = consents.some(c => c.doctor_id === doctor.id);
              return (
                <div key={doctor.id} className="flex flex-col sm:flex-row sm:items-center justify-between p-4 bg-slate-50 border border-slate-200 rounded-xl hover:border-slate-300 transition-colors gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-white border border-slate-200 rounded-full flex items-center justify-center font-bold text-slate-600 text-sm shadow-sm shrink-0">
                      DR
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-800">Dr. {doctor.full_name}</h4>
                      <p className="text-xs text-slate-500 mt-0.5 font-medium">Provider ID: {doctor.id} • License: {doctor.license_number || 'N/A'}</p>
                    </div>
                  </div>
                  <div className="flex sm:justify-end">
                    {hasConsent ? (
                      <button 
                        onClick={() => handleRevokeConsent(doctor.id)} 
                        className="w-full sm:w-auto btn-danger flex items-center justify-center gap-2 py-2 px-4 text-sm"
                      >
                        <ShieldAlert className="w-4 h-4" /> Revoke Access
                      </button>
                    ) : (
                      <button 
                        onClick={() => handleGrantConsent(doctor.id)} 
                        className="w-full sm:w-auto btn-primary flex items-center justify-center gap-2 py-2 px-4 text-sm"
                      >
                        <CheckCircle className="w-4 h-4" /> Grant Access
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
            
            {filteredDoctors.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 text-center bg-white rounded-xl border border-dashed border-slate-200">
                <Search className="w-10 h-10 text-slate-300 mb-3" />
                <h4 className="text-slate-700 font-semibold mb-1">No providers found</h4>
                <p className="text-sm text-slate-500 max-w-sm">Try adjusting your search terms to find the doctor you are looking for.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
