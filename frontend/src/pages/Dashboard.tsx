import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api';
import { Link } from 'react-router-dom';
import { 
  CreditCard, 
  Package, 
  TrendingUp, 
  Search,
  DollarSign,
  Activity,
  ShoppingCart,
  BarChart3,
  Loader2
} from 'lucide-react';

interface DashboardStats {
  total_credits: number;
  credits_used_today: number;
  total_queries: number;
  queries_today: number;
  total_conversions: number;
  conversions_today: number;
}

export function Dashboard() {
  const { user, refreshUser } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [statsResponse] = await Promise.all([
        api.get('/users/me/stats'),
        refreshUser(),
      ]);
      
      setStats(statsResponse.data);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Welcome back, {user?.full_name}!
          </h1>
          <p className="mt-2 text-gray-600">
            Here's an overview of your Amazon Product Intelligence Platform usage
          </p>
        </div>

        {/* Credit Balance Card */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center">
                <CreditCard className="h-8 w-8 text-indigo-600 mr-3" />
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">
                    {user?.credits || 0} Credits
                  </h2>
                  <p className="text-gray-600">Available balance</p>
                </div>
              </div>
            </div>
            <Link
              to="/credits"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              <DollarSign className="h-4 w-4 mr-2" />
              Buy Credits
            </Link>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Activity className="h-6 w-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Credits Used Today</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {stats?.credits_used_today || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Search className="h-6 w-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Queries</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {stats?.total_queries || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Package className="h-6 w-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">FNSKU Conversions</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {stats?.total_conversions || 0}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Link
              to="/products"
              className="flex items-center justify-center px-4 py-3 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              <ShoppingCart className="h-5 w-5 mr-2" />
              Product Lookup
            </Link>
            
            <Link
              to="/fnsku"
              className="flex items-center justify-center px-4 py-3 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              <Package className="h-5 w-5 mr-2" />
              FNSKU Converter
            </Link>
            
            <Link
              to="/monitoring"
              className="flex items-center justify-center px-4 py-3 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              <TrendingUp className="h-5 w-5 mr-2" />
              Price Monitoring
            </Link>
            
            <Link
              to="/analytics"
              className="flex items-center justify-center px-4 py-3 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              <BarChart3 className="h-5 w-5 mr-2" />
              Analytics
            </Link>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="mt-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Today's Activity</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <div className="flex items-center">
                <Search className="h-5 w-5 text-gray-400 mr-3" />
                <span className="text-sm text-gray-600">Product queries</span>
              </div>
              <span className="text-sm font-medium text-gray-900">
                {stats?.queries_today || 0}
              </span>
            </div>
            
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <div className="flex items-center">
                <Package className="h-5 w-5 text-gray-400 mr-3" />
                <span className="text-sm text-gray-600">FNSKU conversions</span>
              </div>
              <span className="text-sm font-medium text-gray-900">
                {stats?.conversions_today || 0}
              </span>
            </div>
            
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center">
                <CreditCard className="h-5 w-5 text-gray-400 mr-3" />
                <span className="text-sm text-gray-600">Credits consumed</span>
              </div>
              <span className="text-sm font-medium text-gray-900">
                {stats?.credits_used_today || 0}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}