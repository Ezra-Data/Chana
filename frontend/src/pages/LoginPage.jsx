import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Bot, Mail, Lock, Eye, EyeOff, ArrowRight, AlertCircle } from 'lucide-react';

export default function LoginPage() {
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
      switch (user.role) {
        case 'student': navigate('/dashboard'); break;
        case 'agent': navigate('/agent'); break;
        case 'admin': navigate('/admin'); break;
        default: navigate('/dashboard');
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(detail || 'Incorrect email/registration number or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-bg relative flex items-center justify-center min-h-screen p-4">
      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8 animate-fade-in">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-white/20 backdrop-blur-sm rounded-2xl mb-4 shadow-lg border border-white/30">
            <Bot className="w-9 h-9 text-white" />
          </div>
          <h1 className="font-display text-4xl font-bold text-white tracking-tight">Chana</h1>
          <p className="text-campus-100/90 mt-1 text-sm font-medium">Campus Chatbot & Navigation System</p>
        </div>

        {/* Login Card */}
        <div className="glass-card p-8 animate-slide-up shadow-2xl">
          <h2 className="font-display text-2xl font-bold text-campus-700 mb-1">Student Sign In</h2>
          <p className="text-gray-500 text-sm mb-6">Sign in with your university email or registration number</p>

          {error && (
            <div id="login-error-alert" className="bg-red-50 border-2 border-red-300 text-red-700 text-sm font-medium rounded-xl p-3.5 mb-5 flex items-start gap-2.5 animate-shake">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <span className="leading-snug">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" autoComplete="off">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Email or Student Reg Number
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  id="login-email"
                  type="text"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-field pl-10"
                  placeholder="you@campus.edu or CS/2024/001"
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
                  id="login-password"
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
              id="login-submit"
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

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-500">
              Don't have an account?{' '}
              <Link to="/register" className="text-campus-600 font-semibold hover:text-campus-500 transition-colors">
                Register here
              </Link>
            </p>
          </div>

          <div className="mt-4 pt-4 border-t border-cream-300">
            <Link
              to="/staff-login"
              className="flex items-center justify-center gap-2 text-sm text-campus-600/80 hover:text-campus-600 font-medium transition-colors"
            >
              Staff & Support Agent Portal <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
