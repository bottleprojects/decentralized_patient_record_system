import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, Users, FileText, CheckCircle, LogOut, Trash2, KeyRound, Loader2, Database, Shield, X, CheckCircle2 } from 'lucide-react';
import { fetchApi } from '../lib/api';

export default function AdminDashboard() {
  const [users, setUsers] = useState<any[]>([]);
  const [records, setRecords] = useState<any[]>([]);
  const [consents, setConsents] = useState<any[]>([]);
  const [pendingDoctors, setPendingDoctors] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('users');
  
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [usersData, recordsData, consentsData, pendingDocsData] = await Promise.all([
        fetchApi('/users'),
        fetchApi('/records'),
        fetchApi('/consent'),
        fetchApi('/users/doctors/pending')
      ]);
      setUsers(usersData);
      setRecords(recordsData);
      setConsents(consentsData);
      setPendingDoctors(pendingDocsData);
    } catch (err: any) {
      setError(err.message || 'Failed to load admin data');
      if (err.message.includes('401')) {
        navigate('/login');
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    navigate('/login');
  };

  const changePassword = async () => {
    try {
      setPasswordLoading(true);
      await fetchApi('/users/change-password', {
        method: 'POST',
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
      });
      alert("Password changed successfully!");
      setShowPasswordModal(false);
      setCurrentPassword('');
      setNewPassword('');
    } catch (err: any) {
      alert(err.message || "Failed to change password");
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!window.confirm('Are you sure you want to delete this user and all associated records? This action cannot be undone.')) {
      return;
    }
    try {
      await fetchApi(`/users/${userId}`, { method: 'DELETE' });
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to delete user');
    }
  };

  const handleCleanup = async () => {
    if (!window.confirm('Are you absolutely sure you want to WIPE the entire database? This will delete all users, patients, doctors, records, and consents except for the admin account. This CANNOT BE UNDONE!')) {
      return;
    }
    
    if (window.prompt('Type "DELETE EVERYTHING" to confirm database wipe:') !== 'DELETE EVERYTHING') {
      alert("Cleanup cancelled.");
      return;
    }

    try {
      await fetchApi('/users/admin/cleanup', { method: 'DELETE' });
      alert("Database wiped successfully!");
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to cleanup database');
      alert(err.message || 'Failed to cleanup database');
    }
  };

  const handleVerifyDoctor = async (userId: number, status: string) => {
    try {
      await fetchApi(`/users/${userId}/verify?status=${status}`, { method: 'POST' });
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to update verification status');
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-slate-800 rounded-xl flex items-center justify-center shrink-0 shadow-sm">
            <Database className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-800 tracking-tight">Administration Console</h2>
            <p className="text-slate-500 mt-1 text-sm font-medium">System-wide monitoring and management</p>
          </div>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-3">
          <button onClick={handleCleanup} className="btn-danger flex items-center justify-center gap-2 text-sm px-4">
            <Trash2 className="w-4 h-4" /> System Wipe
          </button>
          <button onClick={() => setShowPasswordModal(true)} className="btn-secondary flex items-center justify-center gap-2 text-sm px-4">
            <KeyRound className="w-4 h-4" /> Password
          </button>
          <button onClick={handleLogout} className="btn-secondary flex items-center justify-center gap-2 text-sm px-4">
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-xl flex items-center gap-3 border border-red-200 shadow-sm">
          <ShieldAlert className="w-5 h-5 shrink-0 text-red-500" />
          <span className="font-medium text-sm">{error}</span>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div 
          onClick={() => setActiveTab('users')}
          className={`medical-card p-5 cursor-pointer transition-all border-b-4 ${activeTab === 'users' ? 'border-b-blue-600 bg-blue-50/30' : 'border-b-transparent hover:border-b-slate-300'}`}
        >
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Users</p>
            <Users className={`w-5 h-5 ${activeTab === 'users' ? 'text-blue-600' : 'text-slate-400'}`} />
          </div>
          <h3 className="text-2xl font-bold text-slate-800">{users.length}</h3>
        </div>
        
        <div 
          onClick={() => setActiveTab('records')}
          className={`medical-card p-5 cursor-pointer transition-all border-b-4 ${activeTab === 'records' ? 'border-b-blue-600 bg-blue-50/30' : 'border-b-transparent hover:border-b-slate-300'}`}
        >
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Records</p>
            <FileText className={`w-5 h-5 ${activeTab === 'records' ? 'text-blue-600' : 'text-slate-400'}`} />
          </div>
          <h3 className="text-2xl font-bold text-slate-800">{records.length}</h3>
        </div>
        
        <div 
          onClick={() => setActiveTab('consents')}
          className={`medical-card p-5 cursor-pointer transition-all border-b-4 ${activeTab === 'consents' ? 'border-b-blue-600 bg-blue-50/30' : 'border-b-transparent hover:border-b-slate-300'}`}
        >
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Consents</p>
            <CheckCircle className={`w-5 h-5 ${activeTab === 'consents' ? 'text-blue-600' : 'text-slate-400'}`} />
          </div>
          <h3 className="text-2xl font-bold text-slate-800">{consents.length}</h3>
        </div>
        
        <div 
          onClick={() => setActiveTab('verification')}
          className={`medical-card p-5 cursor-pointer transition-all border-b-4 ${activeTab === 'verification' ? 'border-b-amber-500 bg-amber-50/30' : 'border-b-transparent hover:border-b-slate-300'}`}
        >
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Verifications</p>
            <ShieldAlert className={`w-5 h-5 ${activeTab === 'verification' ? 'text-amber-500' : 'text-slate-400'}`} />
          </div>
          <h3 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            {pendingDoctors.length}
            {pendingDoctors.length > 0 && (
              <span className="flex h-2.5 w-2.5 rounded-full bg-amber-500 animate-pulse"></span>
            )}
          </h3>
        </div>
      </div>

      <div className="medical-card overflow-hidden">
        
        {/* Table Content */}
        {activeTab === 'users' && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">ID</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Email</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Full Name</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Role</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">License No.</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map(u => (
                  <tr key={u.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-6 text-sm text-slate-600 font-mono">#{u.id}</td>
                    <td className="py-3 px-6 text-sm font-semibold text-slate-800">{u.email}</td>
                    <td className="py-3 px-6 text-sm text-slate-600">{u.full_name}</td>
                    <td className="py-3 px-6">
                      <span className={`inline-flex px-2.5 py-1 rounded-md text-xs font-bold ${
                        u.role === 'admin' ? 'bg-slate-800 text-white' :
                        u.role === 'doctor' ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      }`}>
                        {u.role.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-6 text-sm text-slate-500 font-mono">{u.license_number || '-'}</td>
                    <td className="py-3 px-6 text-right">
                      {u.role !== 'admin' && (
                        <button
                          onClick={() => handleDeleteUser(u.id)}
                          className="text-slate-400 hover:text-red-600 p-1.5 rounded-lg hover:bg-red-50 transition-colors inline-flex"
                          title="Delete User"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'records' && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Record ID</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Patient ID</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Doctor ID</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Type</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Blockchain TX</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {records.map(r => (
                  <tr key={r.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-6 text-sm text-slate-600 font-mono">#{r.id}</td>
                    <td className="py-3 px-6 text-sm font-semibold text-slate-700">Patient #{r.patient_id}</td>
                    <td className="py-3 px-6 text-sm font-semibold text-slate-700">Dr. #{r.doctor_id}</td>
                    <td className="py-3 px-6 text-sm text-slate-800 font-semibold">{r.file_type}</td>
                    <td className="py-3 px-6 text-xs font-mono text-slate-500 max-w-[200px] truncate">
                      {r.blockchain_tx_hash ? (
                        <a href={`https://sepolia.etherscan.io/tx/${r.blockchain_tx_hash}`} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
                          {r.blockchain_tx_hash}
                        </a>
                      ) : 'Pending'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'consents' && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Consent ID</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Patient ID</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Doctor ID</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Status</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Granted At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {consents.map(c => (
                  <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-6 text-sm text-slate-600 font-mono">#{c.id}</td>
                    <td className="py-3 px-6 text-sm font-semibold text-slate-700">Patient #{c.patient_id}</td>
                    <td className="py-3 px-6 text-sm font-semibold text-slate-700">Dr. #{c.doctor_id}</td>
                    <td className="py-3 px-6">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold ${
                        c.status === 'active' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'
                      }`}>
                        {c.status === 'active' ? <CheckCircle2 className="w-3 h-3" /> : <ShieldAlert className="w-3 h-3" />}
                        {c.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-6 text-sm text-slate-500">{new Date(c.granted_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'verification' && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Doctor ID</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Email</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">Full Name</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider">License No.</th>
                  <th className="py-3 px-6 text-slate-500 font-bold text-xs uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pendingDoctors.map(d => (
                  <tr key={d.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-6 text-sm text-slate-600 font-mono">#{d.id}</td>
                    <td className="py-3 px-6 text-sm font-semibold text-slate-800">{d.email}</td>
                    <td className="py-3 px-6 text-sm text-slate-600">{d.full_name}</td>
                    <td className="py-3 px-6 text-sm text-slate-800 font-semibold font-mono">{d.license_number}</td>
                    <td className="py-3 px-6 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleVerifyDoctor(d.id, 'verified')}
                          className="px-3 py-1.5 bg-emerald-600 text-white hover:bg-emerald-700 font-semibold rounded text-xs transition-colors shadow-sm"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleVerifyDoctor(d.id, 'rejected')}
                          className="px-3 py-1.5 bg-white border border-slate-300 text-slate-600 hover:text-red-600 hover:border-red-200 hover:bg-red-50 font-semibold rounded text-xs transition-colors shadow-sm"
                        >
                          Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {pendingDoctors.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-12 text-center">
                      <div className="flex flex-col items-center justify-center">
                        <Shield className="w-10 h-10 text-slate-300 mb-2" />
                        <p className="text-slate-500 font-medium">No pending doctor verifications.</p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Change Password Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 modal-overlay z-[60] flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <KeyRound className="w-5 h-5 text-slate-400" /> System Password
              </h3>
              <button onClick={() => setShowPasswordModal(false)} className="text-slate-400 hover:text-slate-600 p-1 rounded-md hover:bg-slate-100">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Current Password</label>
                <input 
                  type="password" 
                  className="input-field"
                  value={currentPassword}
                  onChange={e => setCurrentPassword(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">New Password</label>
                <input 
                  type="password" 
                  className="input-field"
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                />
              </div>
              <button 
                onClick={changePassword} 
                disabled={passwordLoading || !currentPassword || !newPassword} 
                className="btn-primary w-full py-2.5 mt-4 flex items-center justify-center gap-2"
              >
                {passwordLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                {passwordLoading ? 'Updating...' : 'Update Password'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
