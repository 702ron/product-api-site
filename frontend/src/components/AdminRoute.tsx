import React, { useState, useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api';
import { Loader2, ShieldX } from 'lucide-react';

interface AdminRouteProps {
  children: React.ReactNode;
}

export function AdminRoute({ children }: AdminRouteProps) {
  const { user, loading: authLoading } = useAuth();
  const location = useLocation();
  const [adminLoading, setAdminLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [adminError, setAdminError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const checkAdminAccess = async () => {
      if (!user || authLoading) {
        return;
      }

      try {
        setAdminLoading(true);
        setAdminError(null);
        
        // Try to access an admin endpoint to verify admin status
        await api.get('/admin/users?limit=1');
        
        if (isMounted) {
          setIsAdmin(true);
        }
      } catch (error: any) {
        if (isMounted) {
          setIsAdmin(false);
          
          if (error.response?.status === 403) {
            setAdminError('Admin access required. You do not have permission to access this area.');
          } else if (error.response?.status === 401) {
            setAdminError('Authentication failed. Please login again.');
          } else if (error.response?.status === 500 && 
                     error.response?.data?.details?.error_type === 'JWTError') {
            setAdminError('Invalid authentication token. Please login again.');
            // Clear invalid tokens
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
          } else {
            setAdminError('Unable to verify admin access. Please try again.');
          }
        }
      } finally {
        if (isMounted) {
          setAdminLoading(false);
        }
      }
    };

    checkAdminAccess();

    return () => {
      isMounted = false;
    };
  }, [user, authLoading]);

  // Still loading authentication
  if (authLoading || adminLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600 mx-auto" />
          <p className="mt-2 text-sm text-gray-600">Verifying access...</p>
        </div>
      </div>
    );
  }

  // Not authenticated at all
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Not an admin user
  if (!isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full text-center p-6">
          <ShieldX className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h1>
          <p className="text-gray-600 mb-6">
            {adminError || 'You do not have permission to access the admin dashboard.'}
          </p>
          <div className="space-y-3">
            <button
              onClick={() => window.history.back()}
              className="w-full px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Go Back
            </button>
            <Navigate to="/dashboard" replace />
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}