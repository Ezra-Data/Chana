import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Shield, Mail, Lock, Eye, EyeOff, ArrowRight, ArrowLeft, AlertCircle } from 'lucide-react';

export default function StaffLoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await login(email, password);
      if (user.role === 'student') {
        setError('This portal is restricted to staff & agents. Please use the student login.');
        return;
      }
      switch (user.role) {
        case 'agent': navigate('/agent'); break;
        case 'admin': navigate('/admin'); break;
        default: navigate('/login');
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(detail || 'Incorrect staff email or password. Please verify and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-bg relative flex items-center justify-center min-h-screen p-4">
      <div className="relative z-10 w-full max-w-md">
        <div className="text-center mb-8 animate-fade-in">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-white/20 backdrop-blur-sm rounded-2xl mb-4 shadow-lg border border-white/30">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="font-display text-3xl font-bold text-white tracking-tight">Chana Staff Portal</h1>
          <p className="text-campus-100/90 mt-1 text-sm">Support Agent & System Administrator Access</p>
        </div>

        <div className="glass-card p-8 animate-slide-up shadow-2xl">
          <h2 className="font-display text-2xl font-bold text-campus-700 mb-1">Staff Sign In</h2>
          <p className="text-gray-500 text-sm mb-6">Sign in with your administrative credentials</p>

          {error && (
            <div id="staff-login-error-alert" className="bg-red-50 border-2 border-red-300 text-red-700 text-sm font-medium rounded-xl p-3.5 mb-5 flex items-start gap-2.5 animate-shake">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <span className="leading-snug">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" autoComplete="off">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Staff Email</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  id="staff-login-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-field pl-10"
                  placeholder="staff@campus.edu"
                  autoComplete="off"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  id="staff-login-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field pl-10 pr-10"
                  placeholder="••••••••"
                  autoComplete="new-password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              id="staff-login-submit"
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2 mt-2 py-3"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>Sign In <ArrowRight className="w-4 h-4" /></>
              )}
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-cream-300">
            <Link
              to="/login"
              className="flex items-center justify-center gap-2 text-sm text-campus-600/80 hover:text-campus-600 font-medium transition-colors"
            >
              <ArrowLeft className="w-3 h-3" /> Back to Student Login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
