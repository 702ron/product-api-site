import React, { useState, useEffect, useRef } from 'react';
import { Users, Settings, Shield, Activity, FileText, AlertTriangle } from 'lucide-react';
import { api } from '../lib/api';
import { useAdmin } from '../contexts/AdminContext';

// Global cache for health data to persist across React Strict Mode remounts
const healthDataCache = {
  data: null as SystemHealth | null,
  timestamp: 0,
  isLoading: false, // Track if any component is currently loading
  CACHE_DURATION: 30 * 1000 // 30 seconds
};

interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  credit_balance: number;
  created_at: string;
  last_login_at?: string;
}

interface SystemHealth {
  status: string;
  uptime: number;
  memory_usage: number;
  cpu_usage: number;
  disk_usage: number;
  active_users: number;
  total_api_calls: number;
}

interface SecurityEvent {
  id: string;
  event_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  ip_address: string;
  created_at: string;
  resolved: boolean;
  details: any;
}

const AdminDashboard: React.FC = () => {
  const { isAdmin, isLoading: adminLoading } = useAdmin();
  const [activeTab, setActiveTab] = useState('overview');
  const [users, setUsers] = useState<User[]>([]);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [securityEvents, setSecurityEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(false); // Start with false, not true
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [creditAdjustment, setCreditAdjustment] = useState('');
  const [adjustmentReason, setAdjustmentReason] = useState('');
  const loadingRef = useRef(false); // Use ref to track loading across renders
  const hasLoadedRef = useRef(false); // Track if we've successfully loaded once

  useEffect(() => {
    // Only load data if user is confirmed admin and not still loading
    // Add a delay to prevent React Strict Mode double invocation from triggering rate limits
    if (isAdmin && !adminLoading && !hasLoadedRef.current) {
      const timeout = setTimeout(() => {
        loadAdminData();
      }, 100); // Small delay to prevent rapid consecutive calls
      
      return () => clearTimeout(timeout);
    }
  }, [isAdmin, adminLoading]);

  const loadAdminData = async () => {
    // Prevent multiple simultaneous calls using ref
    if (loadingRef.current) {
      console.log('Already loading admin data, skipping...');
      return;
    }
    
    let loadingTimeout: NodeJS.Timeout;
    
    try {
      loadingRef.current = true;
      setLoading(true);
      console.log('Loading admin data...');
      
      // Set a timeout to prevent infinite loading
      loadingTimeout = setTimeout(() => {
        console.warn('Admin data loading timed out after 10 seconds');
        loadingRef.current = false;
        setLoading(false);
        hasLoadedRef.current = true; // Mark as loaded even if failed
      }, 5000); // Reduced to 5 seconds
      
      // Load users with error handling
      try {
        const usersResponse = await api.get('/admin/users');
        setUsers(usersResponse.data.users || []);
      } catch (userError: any) {
        console.error('Failed to load users:', userError);
        // Set empty array if auth fails to allow UI to render
        setUsers([]);
      }

      // Skip automatic health loading due to rate limiting issues
      // Set default health data that indicates manual refresh is needed
      console.log('Skipping automatic health check due to rate limiting - manual refresh available');
      const defaultHealth = {
        status: 'rate_limited',
        uptime: 0,
        memory_usage: 0,
        cpu_usage: 0,
        disk_usage: 0,
        active_users: 0,
        total_api_calls: 0
      };
      setSystemHealth(defaultHealth);

      // Load security events (placeholder for now - no security events endpoint exists yet)
      setSecurityEvents([]);
      
    } catch (error) {
      console.error('Failed to load admin data:', error);
    } finally {
      if (loadingTimeout) {
        clearTimeout(loadingTimeout);
      }
      loadingRef.current = false;
      setLoading(false);
      hasLoadedRef.current = true; // Mark as loaded even if failed
      console.log('Admin data loading completed');
    }
  };

  const handleUserAction = async (userId: string, action: string) => {
    try {
      if (action === 'toggle_status') {
        // Get current user status first
        const user = users.find(u => u.id === userId);
        if (user) {
          await api.post(`/admin/users/${userId}/status`, {
            is_active: !user.is_active
          });
        }
      } else if (action === 'adjust_credits' && creditAdjustment) {
        // Send amount and reason as query parameters, not request body
        const params = new URLSearchParams({
          amount: creditAdjustment,
          reason: adjustmentReason
        });
        await api.post(`/admin/users/${userId}/credits?${params}`);
        setCreditAdjustment('');
        setAdjustmentReason('');
        setSelectedUser(null);
      }
      
      // Reload users data
      const usersResponse = await api.get('/admin/users');
      setUsers(usersResponse.data.users || []);
    } catch (error) {
      console.error('Failed to perform user action:', error);
    }
  };

  const refreshHealthData = async () => {
    try {
      console.log('Manual health refresh triggered');
      const healthResponse = await api.get('/admin/status');
      const healthData = healthResponse.data;
      
      // Update global cache
      healthDataCache.data = healthData;
      healthDataCache.timestamp = Date.now();
      setSystemHealth(healthData);
      console.log('Health data refreshed successfully');
    } catch (error) {
      console.error('Failed to refresh health data:', error);
      // Show rate limited status if still failing
      setSystemHealth(prev => prev || {
        status: 'error',
        uptime: 0,
        memory_usage: 0,
        cpu_usage: 0,
        disk_usage: 0,
        active_users: 0,
        total_api_calls: 0
      });
    }
  };

  const exportData = async (format: 'csv' | 'json') => {
    try {
      const response = await api.get(`/admin/export/users?format=${format}`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `users_export.${format}`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export data:', error);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-100';
      case 'high': return 'text-orange-600 bg-orange-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'low': return 'text-green-600 bg-green-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  // Emergency reset function - can be called from console if needed
  (window as any).resetAdminDashboard = () => {
    console.log('Emergency reset triggered');
    loadingRef.current = false;
    setLoading(false);
    hasLoadedRef.current = false;
    // Clear global health cache
    healthDataCache.data = null;
    healthDataCache.timestamp = 0;
  };

  // Global cache clear function
  (window as any).clearHealthCache = () => {
    console.log('Health cache cleared');
    healthDataCache.data = null;
    healthDataCache.timestamp = 0;
    healthDataCache.isLoading = false;
  };

  // Show loading while checking admin status or loading data
  if (adminLoading || loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <div className="ml-4">
          <p className="text-sm text-gray-600">Loading admin data...</p>
          <p className="text-xs text-gray-400 mt-1">
            If this takes too long, check the console or try refreshing
          </p>
        </div>
      </div>
    );
  }

  // Don't render anything if not admin (AdminRoute should handle this)
  if (!isAdmin) {
    return null;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="text-gray-600 mt-2">Manage users, monitor system health, and review security events</p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-8">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', name: 'Overview', icon: Activity },
            { id: 'users', name: 'User Management', icon: Users },
            { id: 'system', name: 'System Health', icon: Settings },
            { id: 'security', name: 'Security Events', icon: Shield },
            { id: 'exports', name: 'Data Exports', icon: FileText }
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2`}
              >
                <Icon className="h-5 w-5" />
                <span>{tab.name}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center">
                <Users className="h-8 w-8 text-blue-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Users</p>
                  <p className="text-2xl font-semibold text-gray-900">{users.length}</p>
                </div>
              </div>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center">
                <Activity className="h-8 w-8 text-green-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Active Users</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {systemHealth?.total_users || 0}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center">
                <AlertTriangle className="h-8 w-8 text-yellow-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Security Events</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {securityEvents.filter(e => !e.resolved).length}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center">
                <Settings className="h-8 w-8 text-purple-600" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">API Calls Today</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {systemHealth?.requests_last_hour || 0}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Recent Security Events */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Recent Security Events</h3>
            </div>
            <div className="divide-y divide-gray-200">
              {securityEvents.slice(0, 5).map((event) => (
                <div key={event.id} className="px-6 py-4 flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getSeverityColor(event.severity)}`}>
                      {event.severity}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{event.event_type}</p>
                      <p className="text-sm text-gray-500">{event.ip_address}</p>
                    </div>
                  </div>
                  <div className="text-sm text-gray-500">
                    {new Date(event.created_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">User Management</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Credits
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((user) => (
                  <tr key={user.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900">{user.full_name}</div>
                        <div className="text-sm text-gray-500">{user.email}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        user.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {user.credit_balance}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                      <button
                        onClick={() => handleUserAction(user.id, 'toggle_status')}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        {user.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                      <button
                        onClick={() => setSelectedUser(user)}
                        className="text-green-600 hover:text-green-900"
                      >
                        Adjust Credits
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* System Health Tab */}
      {activeTab === 'system' && (
        <div className="space-y-6">
          {/* Refresh Button */}
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium text-gray-900">System Health</h3>
            <button
              onClick={refreshHealthData}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh Health Data
            </button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-lg shadow">
              <h4 className="text-lg font-medium text-gray-900 mb-4">System Status</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">Status:</span>
                  <span className={`text-sm font-medium ${
                    systemHealth?.status === 'operational' ? 'text-green-600' : 
                    systemHealth?.status === 'rate_limited' ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    {systemHealth?.status === 'rate_limited' ? 'Rate Limited (Click Refresh)' : 
                     systemHealth?.status || 'Unknown'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">Database:</span>
                  <span className={`text-sm font-medium ${
                    systemHealth?.database_status === 'connected' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {systemHealth?.database_status || 'Unknown'}
                  </span>
                </div>
                {systemHealth?.status === 'rate_limited' && (
                  <div className="mt-2 p-2 bg-yellow-50 rounded text-xs text-yellow-700">
                    Health data disabled due to rate limiting. Use refresh button above.
                  </div>
                )}
              </div>
            </div>

            <div className="bg-white p-6 rounded-lg shadow">
              <h4 className="text-lg font-medium text-gray-900 mb-4">Resource Usage</h4>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Memory</span>
                    <span className="text-gray-900">{systemHealth?.memory_usage_percent || 0}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                    <div 
                      className="bg-blue-600 h-2 rounded-full" 
                      style={{ width: `${systemHealth?.memory_usage_percent || 0}%` }}
                    ></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">CPU</span>
                    <span className="text-gray-900">{systemHealth?.cpu_usage_percent || 0}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                    <div 
                      className="bg-green-600 h-2 rounded-full" 
                      style={{ width: `${systemHealth?.cpu_usage_percent || 0}%` }}
                    ></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Version</span>
                    <span className="text-gray-900">{systemHealth?.version || 'Unknown'}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white p-6 rounded-lg shadow">
              <h4 className="text-lg font-medium text-gray-900 mb-4">Activity</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">Total Users:</span>
                  <span className="text-sm text-gray-900">{systemHealth?.total_users || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">API Calls (Last Hour):</span>
                  <span className="text-sm text-gray-900">{systemHealth?.requests_last_hour || 0}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Security Events Tab */}
      {activeTab === 'security' && (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Security Events</h3>
          </div>
          <div className="p-6 text-center text-gray-500">
            <p>Security events monitoring is not yet implemented.</p>
            <p className="text-sm mt-2">This feature will be available in a future update.</p>
          </div>
        </div>
      )}

      {/* Data Exports Tab */}
      {activeTab === 'exports' && (
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Data Exports</h3>
          <div className="text-center text-gray-500">
            <p>Data export functionality is not yet implemented.</p>
            <p className="text-sm mt-2">This feature will be available in a future update.</p>
          </div>
        </div>
      )}

      {/* Credit Adjustment Modal */}
      {selectedUser && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Adjust Credits for {selectedUser.full_name}
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Credit Adjustment
                </label>
                <input
                  type="number"
                  value={creditAdjustment}
                  onChange={(e) => setCreditAdjustment(e.target.value)}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter positive or negative amount"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Reason
                </label>
                <textarea
                  value={adjustmentReason}
                  onChange={(e) => setAdjustmentReason(e.target.value)}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  rows={3}
                  placeholder="Reason for adjustment"
                />
              </div>
              <div className="flex justify-end space-x-2">
                <button
                  onClick={() => setSelectedUser(null)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 hover:bg-gray-50 rounded-md"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleUserAction(selectedUser.id, 'adjust_credits')}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md"
                >
                  Adjust Credits
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;