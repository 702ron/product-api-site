import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '../lib/api';
import { useAuth } from './AuthContext';

interface AdminContextType {
  isAdmin: boolean;
  isLoading: boolean;
  checkAdminStatus: () => Promise<void>;
  clearAdminStatus: () => void;
}

const AdminContext = createContext<AdminContextType | undefined>(undefined);

interface AdminProviderProps {
  children: ReactNode;
}

export function AdminProvider({ children }: AdminProviderProps) {
  const { user } = useAuth();
  const [isAdmin, setIsAdmin] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [lastCheck, setLastCheck] = useState<number>(0);
  
  // Cache admin status for 30 seconds to prevent rapid re-checks
  const CACHE_DURATION = 30 * 1000; // 30 seconds

  const checkAdminStatus = async () => {
    if (!user) {
      setIsAdmin(false);
      setIsLoading(false);
      return;
    }

    // Check if we have a recent result in cache
    const now = Date.now();
    if (now - lastCheck < CACHE_DURATION) {
      return; // Use cached result
    }

    // Prevent multiple simultaneous checks
    if (isLoading) {
      return;
    }

    setIsLoading(true);
    
    try {
      // Test admin access by trying to access admin users endpoint with minimal data
      await api.get('/admin/users?limit=1');
      setIsAdmin(true);
      setLastCheck(now);
    } catch (error: any) {
      // If we get a 403 or 401, user is not an admin
      if (error.response?.status === 403 || error.response?.status === 401) {
        setIsAdmin(false);
        setLastCheck(now);
      } else if (error.response?.status === 429) {
        // Rate limited - keep current status and try again later
        console.warn('Admin status check rate limited, keeping current status');
      } else {
        // For other errors (500, network issues), assume not admin to be safe
        setIsAdmin(false);
        setLastCheck(now);
        console.warn('Admin status check failed:', error.message);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const clearAdminStatus = () => {
    setIsAdmin(false);
    setLastCheck(0);
    setIsLoading(false);
  };

  // Check admin status when user changes, but debounce it
  useEffect(() => {
    if (user) {
      checkAdminStatus();
    } else {
      clearAdminStatus();
    }
  }, [user]);

  const value: AdminContextType = {
    isAdmin,
    isLoading,
    checkAdminStatus,
    clearAdminStatus,
  };

  return (
    <AdminContext.Provider value={value}>
      {children}
    </AdminContext.Provider>
  );
}

export function useAdmin(): AdminContextType {
  const context = useContext(AdminContext);
  if (context === undefined) {
    throw new Error('useAdmin must be used within an AdminProvider');
  }
  return context;
}