import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { fetchApi } from '../lib/api';
import { Activity, ShieldCheck, FileText, Lock, Loader2, AlertCircle } from 'lucide-react';

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [healthStatus, setHealthStatus] = useState<{neon_active?: boolean, supabase_active?: boolean} | null>(null);

  useEffect(() => {
    fetchApi('/health').then(setHealthStatus).catch(console.error);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const data = await fetchApi('/users/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
      });

      localStorage.setItem('access_token', data.access_token);
      
      // Decode JWT slightly to find role for routing
      const payload = JSON.parse(atob(data.access_token.split('.')[1]));
      
      if (payload.role === 'admin') {
        navigate('/admin');
      } else if (payload.role === 'doctor') {
        navigate('/doctor');
      } else {
        navigate('/patient');
      }
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-white">
      {/* Left Side - Branding (Hidden on mobile) */}
      <div className="hidden lg:flex lg:w-1/2 bg-slate-50 relative flex-col justify-between overflow-hidden border-r border-slate-200">
        <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-[0.03]"></div>
        
        <div className="p-12 relative z-10">
          <div className="flex items-center gap-3 mb-16">
            <div className="w-10 h-10 bg-blue-700 rounded-lg flex items-center justify-center">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-800 tracking-tight leading-none">DPRMS</h1>
              <span className="text-xs uppercase font-semibold text-slate-500 tracking-wider">Health Systems</span>
            </div>
          </div>
          
          <div className="max-w-md">
            <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight leading-tight mb-6">
              Secure access to your medical records.
            </h2>
            <p className="text-lg text-slate-600 mb-12">
              The Decentralized Patient Record Management System provides hospital-grade security and complete privacy for your sensitive health information.
            </p>
            
            <div className="space-y-6">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                  <ShieldCheck className="w-5 h-5 text-blue-700" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-800">Advanced Security</h3>
                  <p className="text-sm text-slate-600">Enterprise-level encryption ensures your data remains confidential.</p>
                </div>
              </div>
              
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                  <Lock className="w-5 h-5 text-blue-700" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-800">Access Control</h3>
                  <p className="text-sm text-slate-600">You decide which healthcare professionals can view your records.</p>
                </div>
              </div>
              
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5 text-blue-700" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-800">Immutable Integrity</h3>
                  <p className="text-sm text-slate-600">Blockchain verification guarantees your records cannot be tampered with.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div className="p-12 relative z-10 text-sm text-slate-500 font-medium">
          &copy; {new Date().getFullYear()} DPRMS Health Systems. Secure Portal.
        </div>
      </div>
      
      {/* Right Side - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-12 bg-white relative">
        <div className="w-full max-w-md">
          
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-10">
            <div className="w-10 h-10 bg-blue-700 rounded-lg flex items-center justify-center">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-800 tracking-tight leading-none">DPRMS</h1>
            </div>
          </div>
          
          <div className="mb-10 text-center lg:text-left">
            <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Welcome back</h2>
            <p className="text-slate-500 mt-2">Please enter your details to sign in.</p>
          </div>
          
          {healthStatus && (healthStatus.neon_active === false || healthStatus.supabase_active === false) && (
            <div className="bg-amber-50 text-amber-800 p-4 rounded-xl text-sm mb-6 border border-amber-200 shadow-sm flex gap-3">
              <AlertCircle className="w-5 h-5 shrink-0 text-amber-600" />
              <div>
                <p className="font-bold mb-1">Service Maintenance</p>
                <p>
                  {!healthStatus.neon_active && !healthStatus.supabase_active 
                    ? "Database systems are currently inactive." 
                    : !healthStatus.neon_active 
                      ? "Primary database is currently inactive." 
                      : "Storage system is currently inactive."}
                </p>
                <p className="mt-1 opacity-80 text-xs">Login attempts may experience delays.</p>
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 text-red-700 p-4 rounded-xl text-sm mb-6 border border-red-200 flex items-start gap-3 shadow-sm">
              <AlertCircle className="w-5 h-5 shrink-0 text-red-500" />
              <div className="pt-0.5">{error}</div>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Email or Username</label>
              <input 
                type="text" 
                value={email} 
                onChange={e => setEmail(e.target.value)} 
                required 
                className="input-field" 
                placeholder="Enter your email" 
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-sm font-semibold text-slate-700">Password</label>
              </div>
              <input 
                type="password" 
                value={password} 
                onChange={e => setPassword(e.target.value)} 
                required 
                className="input-field" 
                placeholder="••••••••" 
              />
            </div>
            <button type="submit" disabled={loading} className="w-full btn-primary py-3 text-base flex items-center justify-center gap-2 mt-4">
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" /> Authenticating...
                </>
              ) : 'Sign In'}
            </button>
          </form>
          
          <div className="mt-8 text-center">
            <p className="text-sm text-slate-600">
              Don't have an identity yet?{' '}
              <Link to="/register" className="text-blue-600 font-semibold hover:text-blue-700 hover:underline transition-colors">
                Create an account
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
