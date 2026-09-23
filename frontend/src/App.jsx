import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import { SocketProvider } from './contexts/SocketContext';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import StaffLoginPage from './pages/StaffLoginPage';
import StudentDashboard from './pages/StudentDashboard';
import AgentDashboard from './pages/AgentDashboard';
import AdminDashboard from './pages/AdminDashboard';

function ProtectedRoute({ children, allowedRoles }) {
  const { user, isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-cream-100">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-campus-200 border-t-campus-600 rounded-full animate-spin" />
          <p className="text-campus-600 font-medium">Loading...</p>
        </div>
      </div>
    );
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    // Redirect to appropriate dashboard
    if (user?.role === 'student') return <Navigate to="/dashboard" replace />;
    if (user?.role === 'agent') return <Navigate to="/agent" replace />;
    if (user?.role === 'admin') return <Navigate to="/admin" replace />;
    return <Navigate to="/login" replace />;
  }
  
  return children;
}

function AppRoutes() {
  const { user, isAuthenticated } = useAuth();

  // Redirect authenticated users to their dashboard
  const getDefaultRoute = () => {
    if (!isAuthenticated) return '/login';
    switch (user?.role) {
      case 'student': return '/dashboard';
      case 'agent': return '/agent';
      case 'admin': return '/admin';
      default: return '/login';
    }
  };

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={
        isAuthenticated ? <Navigate to={getDefaultRoute()} replace /> : <LoginPage />
      } />
      <Route path="/register" element={
        isAuthenticated ? <Navigate to={getDefaultRoute()} replace /> : <RegisterPage />
      } />
      <Route path="/staff-login" element={
        isAuthenticated ? <Navigate to={getDefaultRoute()} replace /> : <StaffLoginPage />
      } />

      {/* Protected routes */}
      <Route path="/dashboard/*" element={
        <ProtectedRoute allowedRoles={['student']}>
          <StudentDashboard />
        </ProtectedRoute>
      } />
      <Route path="/agent/*" element={
        <ProtectedRoute allowedRoles={['agent']}>
          <AgentDashboard />
        </ProtectedRoute>
      } />
      <Route path="/admin/*" element={
        <ProtectedRoute allowedRoles={['admin']}>
          <AdminDashboard />
        </ProtectedRoute>
      } />

      {/* Default redirect */}
      <Route path="/" element={<Navigate to={getDefaultRoute()} replace />} />
      <Route path="*" element={<Navigate to={getDefaultRoute()} replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <SocketProvider>
      <AppRoutes />
    </SocketProvider>
  );
}
