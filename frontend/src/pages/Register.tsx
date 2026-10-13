import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { fetchApi } from '../lib/api';
import { Activity, Loader2, AlertCircle, User, Stethoscope } from 'lucide-react';

export default function Register() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: '',
    full_name: '',
    password: '',
    role: 'patient',
    license_number: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await fetchApi('/users/register', {
        method: 'POST',
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          full_name: formData.full_name,
          role: formData.role,
          license_number: formData.role === 'doctor' ? formData.license_number : undefined
        })
      });

      // Automatically login after successful registration
      const loginData = new URLSearchParams();
      loginData.append('username', formData.email);
      loginData.append('password', formData.password);

      const data = await fetchApi('/users/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: loginData
      });

      localStorage.setItem('access_token', data.access_token);
      
      if (formData.role === 'doctor') {
        navigate('/doctor');
      } else {
        navigate('/patient');
      }
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-white">
      {/* Left Side - Branding (Hidden on mobile) */}
      <div className="hidden lg:flex lg:w-1/2 bg-slate-50 relative flex-col justify-between overflow-hidden border-r border-slate-200">
        <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-[0.03]"></div>
        
        <div className="p-12 relative z-10 flex flex-col h-full justify-between">
          <div>
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
                Join the secure healthcare network.
              </h2>
              <p className="text-lg text-slate-600 mb-12">
                Create your identity to manage medical records with uncompromising privacy and enterprise-grade security.
              </p>
              
              <div className="space-y-6">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                    <User className="w-5 h-5 text-blue-700" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-800">For Patients</h3>
                    <p className="text-sm text-slate-600">Take complete control over your health records and decide who can access them.</p>
                  </div>
                </div>
                
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                    <Stethoscope className="w-5 h-5 text-blue-700" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-800">For Medical Professionals</h3>
                    <p className="text-sm text-slate-600">Securely access patient records with verified cryptographic consent.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div className="text-sm text-slate-500 font-medium mt-12">
            &copy; {new Date().getFullYear()} DPRMS Health Systems. Secure Portal.
          </div>
        </div>
      </div>
      
      {/* Right Side - Registration Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-12 bg-white relative overflow-y-auto">
        <div className="w-full max-w-md py-8">
          
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
            <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Create Identity</h2>
            <p className="text-slate-500 mt-2">Join the Decentralized Patient Record System.</p>
          </div>
          
          {error && (
            <div className="bg-red-50 text-red-700 p-4 rounded-xl text-sm mb-6 border border-red-200 flex items-start gap-3 shadow-sm">
              <AlertCircle className="w-5 h-5 shrink-0 text-red-500" />
              <div className="pt-0.5">{error}</div>
            </div>
          )}

          <form onSubmit={handleRegister} className="space-y-5">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Email or Username</label>
              <input 
                type="text" 
                name="email" 
                value={formData.email} 
                onChange={handleChange} 
                required 
                className="input-field" 
                placeholder="user@example.com" 
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Full Name</label>
              <input 
                type="text" 
                name="full_name" 
                value={formData.full_name} 
                onChange={handleChange} 
                required 
                className="input-field" 
                placeholder="John Doe" 
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Password</label>
              <input 
                type="password" 
                name="password" 
                value={formData.password} 
                onChange={handleChange} 
                required 
                className="input-field" 
                placeholder="••••••••" 
                minLength={6} 
              />
            </div>
            
            <div className="pt-2">
              <label className="block text-sm font-semibold text-slate-700 mb-3">I am registering as a...</label>
              <div className="grid grid-cols-2 gap-4">
                <label className={`border-2 rounded-xl p-4 flex flex-col items-center cursor-pointer transition-all ${formData.role === 'patient' ? 'border-blue-600 bg-blue-50/50 text-blue-700' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'}`}>
                  <input type="radio" name="role" value="patient" checked={formData.role === 'patient'} onChange={handleChange} className="sr-only" />
                  <User className={`w-6 h-6 mb-2 ${formData.role === 'patient' ? 'text-blue-600' : 'text-slate-400'}`} />
                  <span className="font-semibold text-sm">Patient</span>
                </label>
                <label className={`border-2 rounded-xl p-4 flex flex-col items-center cursor-pointer transition-all ${formData.role === 'doctor' ? 'border-blue-600 bg-blue-50/50 text-blue-700' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'}`}>
                  <input type="radio" name="role" value="doctor" checked={formData.role === 'doctor'} onChange={handleChange} className="sr-only" />
                  <Stethoscope className={`w-6 h-6 mb-2 ${formData.role === 'doctor' ? 'text-blue-600' : 'text-slate-400'}`} />
                  <span className="font-semibold text-sm">Doctor</span>
                </label>
              </div>
            </div>

            {formData.role === 'doctor' && (
              <div className="animate-in fade-in slide-in-from-top-2 duration-300">
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Medical License Number</label>
                <input 
                  type="text" 
                  name="license_number" 
                  value={formData.license_number} 
                  onChange={handleChange} 
                  required 
                  className="input-field" 
                  placeholder="e.g. MD1234567" 
                />
              </div>
            )}
            
            <button type="submit" disabled={loading} className="w-full btn-primary py-3 text-base flex items-center justify-center gap-2 mt-6">
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" /> Creating Identity...
                </>
              ) : 'Register'}
            </button>
          </form>
          
          <div className="mt-8 text-center">
            <p className="text-sm text-slate-600">
              Already have an identity?{' '}
              <Link to="/login" className="text-blue-600 font-semibold hover:text-blue-700 hover:underline transition-colors">
                Sign In
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
