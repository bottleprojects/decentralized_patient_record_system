import { useState, useEffect } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { Shield, Activity, Users, FileText, LogOut, Clock, Loader2, KeyRound, Menu, X } from 'lucide-react';
import { fetchApi } from '../lib/api';

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState<any>(null);
  
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    loadUser();
    setMobileMenuOpen(false); // Close menu on route change
  }, [location.pathname]);

  const loadUser = async () => {
    try {
      const data = await fetchApi('/users/me');
      setUser(data);
    } catch (err) {
      console.error("Failed to load user info:", err);
    }
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

  const isDoctor = user ? user.role === 'doctor' : location.pathname.includes('/doctor');
  const isAdmin = user ? user.role === 'admin' : location.pathname.includes('/admin');

  // New Hospital-Grade Sidebar Navigation
  const renderNavLinks = () => {
    if (isAdmin) {
      return (
        <Link to="/admin" className={`flex items-center gap-3 px-4 py-3 font-semibold rounded-lg transition-all ${location.pathname === '/admin' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-50 hover:text-blue-600'}`}>
          <Shield className="w-5 h-5" /> Admin Console
        </Link>
      );
    }
    
    if (isDoctor) {
      return (
        <Link to="/doctor" className={`flex items-center gap-3 px-4 py-3 font-semibold rounded-lg transition-all ${location.pathname === '/doctor' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-50 hover:text-blue-600'}`}>
          <Users className="w-5 h-5" /> Patient Access
        </Link>
      );
    }
    
    return (
      <>
        <Link to="/patient" className={`flex items-center gap-3 px-4 py-3 font-semibold rounded-lg transition-all ${location.pathname === '/patient' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-50 hover:text-blue-600'}`}>
          <FileText className="w-5 h-5" /> Medical Records
        </Link>
        <Link to="/patient/consent" className={`flex items-center gap-3 px-4 py-3 font-semibold rounded-lg transition-all ${location.pathname === '/patient/consent' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-50 hover:text-blue-600'}`}>
          <Shield className="w-5 h-5" /> Consent & Access
        </Link>
        <Link to="/patient/audit" className={`flex items-center gap-3 px-4 py-3 font-semibold rounded-lg transition-all ${location.pathname === '/patient/audit' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-50 hover:text-blue-600'}`}>
          <Clock className="w-5 h-5" /> Audit Trail
        </Link>
      </>
    );
  };

  const getPageTitle = () => {
    if (location.pathname === '/patient') return 'Patient Dashboard';
    if (location.pathname === '/patient/consent') return 'Consent & Access';
    if (location.pathname === '/patient/audit') return 'Security & Activity History';
    if (location.pathname === '/doctor') return 'Clinical Workspace';
    if (location.pathname.includes('/doctor/patient')) return 'Patient Electronic Record';
    if (location.pathname === '/admin') return 'Administration Console';
    return 'DPRMS Portal';
  };

  return (
    <div className="min-h-screen flex bg-[#F7F9FC]">
      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-40 bg-slate-900/50 md:hidden" onClick={() => setMobileMenuOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-slate-200 flex flex-col transition-transform duration-300 md:relative md:translate-x-0 ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        
        {/* Hospital Branding Logo */}
        <div className="h-16 flex items-center px-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-700 rounded flex items-center justify-center">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-slate-800 leading-none tracking-tight">DPRMS</h1>
              <span className="text-[10px] uppercase font-semibold tracking-wider text-slate-500">Secure Records</span>
            </div>
          </div>
        </div>
        
        {/* Navigation */}
        <div className="p-4 flex-1 overflow-y-auto space-y-1">
          <p className="px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 mt-4">Menu</p>
          {renderNavLinks()}
        </div>
        
        {/* Bottom User Area */}
        <div className="p-4 border-t border-slate-200 bg-slate-50/50">
          <div className="flex items-center gap-3 mb-4 px-2">
            <div className="w-10 h-10 bg-slate-200 rounded-full flex items-center justify-center shrink-0 border border-slate-300">
              <span className="text-sm font-bold text-slate-600">{user?.full_name ? user.full_name.substring(0,2).toUpperCase() : (isDoctor ? 'DR' : 'PT')}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-slate-800 truncate">{user?.full_name || (isDoctor ? 'Doctor User' : 'Patient User')}</p>
              <p className="text-xs text-slate-500 truncate capitalize">{user?.role || 'User'}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowPasswordModal(true)} className="flex-1 flex items-center justify-center gap-2 py-2 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
              <KeyRound className="w-3.5 h-3.5" /> Security
            </button>
            <button onClick={() => { localStorage.removeItem('access_token'); navigate('/login'); }} className="flex-1 flex items-center justify-center gap-2 py-2 text-xs font-semibold text-red-600 bg-white border border-slate-200 rounded-lg hover:bg-red-50 transition-colors">
              <LogOut className="w-3.5 h-3.5" /> Sign Out
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-4 sm:px-6 shrink-0 z-10">
          <div className="flex items-center gap-4">
            <button className="md:hidden p-2 text-slate-500 hover:bg-slate-100 rounded-lg" onClick={() => setMobileMenuOpen(true)}>
              <Menu className="w-5 h-5" />
            </button>
            <h2 className="text-lg font-bold text-slate-800 hidden sm:block">{getPageTitle()}</h2>
          </div>
          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-green-50 border border-green-200 rounded-full text-xs font-medium text-green-700">
              <Shield className="w-3.5 h-3.5" /> Secure Connection
            </div>
          </div>
        </header>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-6xl mx-auto pb-12">
            <Outlet />
          </div>
        </div>
      </main>

      {/* Change Password Modal (Refined) */}
      {showPasswordModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 modal-overlay backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-800">Security Settings</h3>
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
                className="btn-primary w-full py-2.5 mt-4"
              >
                {passwordLoading ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> : "Update Password"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
