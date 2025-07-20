import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

const monitorSchema = z.object({
  asin: z.string().length(10, 'ASIN must be exactly 10 characters'),
  marketplace: z.string().min(1, 'Marketplace is required'),
  target_price: z.number().min(0.01, 'Target price must be greater than 0'),
  alert_threshold: z.number().min(1, 'Alert threshold must be at least 1%').max(100, 'Alert threshold cannot exceed 100%'),
  notification_email: z.string().email('Invalid email address').optional(),
  webhook_url: z.string().url('Invalid webhook URL').optional(),
});

type MonitorFormData = z.infer<typeof monitorSchema>;

interface PriceMonitor {
  id: string;
  asin: string;
  marketplace: string;
  current_price: number;
  target_price: number;
  alert_threshold: number;
  is_active: boolean;
  created_at: string;
  last_checked: string;
  notification_email?: string;
  webhook_url?: string;
}

interface PriceHistory {
  id: string;
  monitor_id: string;
  price: number;
  recorded_at: string;
  price_change_percentage?: number;
}

export default function PriceMonitoring() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [selectedMonitor, setSelectedMonitor] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<MonitorFormData>({
    resolver: zodResolver(monitorSchema),
    defaultValues: {
      marketplace: 'US',
      alert_threshold: 5,
    },
  });

  // Fetch price monitors
  const { data: monitors, isLoading: monitorsLoading } = useQuery({
    queryKey: ['price-monitors'],
    queryFn: async () => {
      const response = await api.get('/monitoring/monitors');
      return response.data.monitors as PriceMonitor[];
    },
    enabled: !!user,
  });

  // Fetch price history for selected monitor
  const { data: priceHistory, isLoading: historyLoading } = useQuery({
    queryKey: ['price-history', selectedMonitor],
    queryFn: async () => {
      if (!selectedMonitor) return [];
      const response = await api.get(`/monitoring/monitors/${selectedMonitor}/history`);
      return response.data as PriceHistory[];
    },
    enabled: !!selectedMonitor,
  });

  // Create price monitor mutation
  const createMonitorMutation = useMutation({
    mutationFn: async (data: MonitorFormData) => {
      const response = await api.post('/monitoring/monitors', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['price-monitors'] });
      reset();
    },
  });

  // Toggle monitor status mutation
  const toggleMonitorMutation = useMutation({
    mutationFn: async ({ id, is_active }: { id: string; is_active: boolean }) => {
      const response = await api.patch(`/monitoring/monitors/${id}`, { is_active });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['price-monitors'] });
    },
  });

  // Delete monitor mutation
  const deleteMonitorMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/monitoring/monitors/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['price-monitors'] });
      if (selectedMonitor) {
        setSelectedMonitor(null);
      }
    },
  });

  const onSubmit = (data: MonitorFormData) => {
    createMonitorMutation.mutate(data);
  };

  const handleToggleMonitor = (monitor: PriceMonitor) => {
    toggleMonitorMutation.mutate({
      id: monitor.id,
      is_active: !monitor.is_active,
    });
  };

  const handleDeleteMonitor = (id: string) => {
    if (window.confirm('Are you sure you want to delete this price monitor?')) {
      deleteMonitorMutation.mutate(id);
    }
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(price);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getPriceChangeColor = (change?: number) => {
    if (!change) return 'text-gray-600';
    return change > 0 ? 'text-red-600' : 'text-green-600';
  };

  const getPriceChangeIcon = (change?: number) => {
    if (!change) return null;
    return change > 0 ? '↗' : '↘';
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Price Monitoring</h1>
        <p className="mt-2 text-gray-600">
          Track Amazon product prices and get alerts when they change
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Create Monitor Form */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Create Price Monitor</h2>
          
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label htmlFor="asin" className="block text-sm font-medium text-gray-700">
                ASIN
              </label>
              <input
                {...register('asin')}
                type="text"
                placeholder="B08N5WRWNW"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
              {errors.asin && (
                <p className="mt-1 text-sm text-red-600">{errors.asin.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="marketplace" className="block text-sm font-medium text-gray-700">
                Marketplace
              </label>
              <select
                {...register('marketplace')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="US">United States</option>
                <option value="CA">Canada</option>
                <option value="GB">United Kingdom</option>
                <option value="DE">Germany</option>
                <option value="FR">France</option>
                <option value="IT">Italy</option>
                <option value="ES">Spain</option>
                <option value="JP">Japan</option>
              </select>
            </div>

            <div>
              <label htmlFor="target_price" className="block text-sm font-medium text-gray-700">
                Target Price ($)
              </label>
              <input
                {...register('target_price', { valueAsNumber: true })}
                type="number"
                step="0.01"
                placeholder="29.99"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
              {errors.target_price && (
                <p className="mt-1 text-sm text-red-600">{errors.target_price.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="alert_threshold" className="block text-sm font-medium text-gray-700">
                Alert Threshold (%)
              </label>
              <input
                {...register('alert_threshold', { valueAsNumber: true })}
                type="number"
                min="1"
                max="100"
                placeholder="5"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
              {errors.alert_threshold && (
                <p className="mt-1 text-sm text-red-600">{errors.alert_threshold.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="notification_email" className="block text-sm font-medium text-gray-700">
                Notification Email (Optional)
              </label>
              <input
                {...register('notification_email')}
                type="email"
                placeholder="alerts@yourcompany.com"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
              {errors.notification_email && (
                <p className="mt-1 text-sm text-red-600">{errors.notification_email.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="webhook_url" className="block text-sm font-medium text-gray-700">
                Webhook URL (Optional)
              </label>
              <input
                {...register('webhook_url')}
                type="url"
                placeholder="https://your-app.com/webhooks/price-alerts"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
              {errors.webhook_url && (
                <p className="mt-1 text-sm text-red-600">{errors.webhook_url.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {isSubmitting ? 'Creating...' : 'Create Monitor'}
            </button>
          </form>

          {createMonitorMutation.error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">
                Failed to create monitor: {createMonitorMutation.error instanceof Error ? createMonitorMutation.error.message : 'Unknown error'}
              </p>
            </div>
          )}
        </div>

        {/* Active Monitors */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Active Monitors</h2>
          
          {monitorsLoading ? (
            <div className="text-center py-4">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
            </div>
          ) : monitors && monitors.length > 0 ? (
            <div className="space-y-4">
              {monitors.map((monitor) => (
                <div
                  key={monitor.id}
                  className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                    selectedMonitor === monitor.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setSelectedMonitor(monitor.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-medium text-gray-900">{monitor.asin}</span>
                        <span className="text-sm text-gray-500">({monitor.marketplace})</span>
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            monitor.is_active
                              ? 'bg-green-100 text-green-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {monitor.is_active ? 'Active' : 'Paused'}
                        </span>
                      </div>
                      <div className="mt-1 text-sm text-gray-600">
                        Current: {formatPrice(monitor.current_price)} | Target: {formatPrice(monitor.target_price)}
                      </div>
                      <div className="mt-1 text-xs text-gray-500">
                        Last checked: {formatDate(monitor.last_checked)}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleMonitor(monitor);
                        }}
                        className={`text-sm px-3 py-1 rounded ${
                          monitor.is_active
                            ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200'
                            : 'bg-green-100 text-green-800 hover:bg-green-200'
                        }`}
                      >
                        {monitor.is_active ? 'Pause' : 'Resume'}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteMonitor(monitor.id);
                        }}
                        className="text-sm px-3 py-1 rounded bg-red-100 text-red-800 hover:bg-red-200"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-4">
              No price monitors yet. Create one to get started!
            </p>
          )}
        </div>
      </div>

      {/* Price History */}
      {selectedMonitor && (
        <div className="mt-8 bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Price History</h2>
          
          {historyLoading ? (
            <div className="text-center py-4">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
            </div>
          ) : priceHistory && priceHistory.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Price
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Change
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {priceHistory.map((entry) => (
                    <tr key={entry.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatDate(entry.recorded_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatPrice(entry.price)}
                      </td>
                      <td className={`px-6 py-4 whitespace-nowrap text-sm ${getPriceChangeColor(entry.price_change_percentage)}`}>
                        {entry.price_change_percentage ? (
                          <span>
                            {getPriceChangeIcon(entry.price_change_percentage)} {Math.abs(entry.price_change_percentage).toFixed(2)}%
                          </span>
                        ) : (
                          '-'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500 text-center py-4">
              No price history available for this monitor.
            </p>
          )}
        </div>
      )}
    </div>
  );
}