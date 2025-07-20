import React, { useState, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { api } from '../lib/api';
import { 
  Package, 
  Upload, 
  Download, 
  Trash2, 
  Copy,
  CheckCircle,
  AlertCircle,
  Loader2,
  Plus,
  FileText,
  Zap
} from 'lucide-react';

const singleConversionSchema = z.object({
  asin: z.string()
    .min(10, 'ASIN must be at least 10 characters')
    .max(10, 'ASIN must be exactly 10 characters')
    .regex(/^[A-Z0-9]+$/, 'ASIN must contain only uppercase letters and numbers'),
  marketplace: z.enum(['US', 'UK', 'DE', 'FR', 'IT', 'ES', 'CA', 'JP', 'AU']),
});

type SingleConversionForm = z.infer<typeof singleConversionSchema>;

interface ConversionResult {
  asin: string;
  fnsku: string;
  confidence: number;
  method: string;
  marketplace: string;
  error?: string;
}

interface BulkConversionJob {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_items: number;
  completed_items: number;
  failed_items: number;
  results?: ConversionResult[];
  error?: string;
}

export function FNSKUConverter() {
  const [singleResult, setSingleResult] = useState<ConversionResult | null>(null);
  const [bulkFile, setBulkFile] = useState<File | null>(null);
  const [bulkJob, setBulkJob] = useState<BulkConversionJob | null>(null);
  const [bulkResults, setBulkResults] = useState<ConversionResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'single' | 'bulk'>('single');

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<SingleConversionForm>({
    resolver: zodResolver(singleConversionSchema),
    defaultValues: {
      marketplace: 'US',
    },
  });

  const onSingleSubmit = async (data: SingleConversionForm) => {
    setLoading(true);
    setError(null);
    setSingleResult(null);

    try {
      const response = await api.post('/conversion/asin-to-fnsku', data);
      setSingleResult(response.data);
    } catch (error: any) {
      console.error('Conversion failed:', error);
      setError(
        error.response?.data?.detail || 
        'Failed to convert ASIN to FNSKU. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (file.type !== 'text/csv') {
        setError('Please upload a CSV file');
        return;
      }
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        setError('File size must be less than 5MB');
        return;
      }
      setBulkFile(file);
      setError(null);
    }
  }, []);

  const handleBulkSubmit = async () => {
    if (!bulkFile) {
      setError('Please select a CSV file');
      return;
    }

    setBulkLoading(true);
    setError(null);
    setBulkJob(null);
    setBulkResults([]);

    try {
      const formData = new FormData();
      formData.append('file', bulkFile);

      const response = await api.post('/conversion/bulk-asin-to-fnsku', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setBulkJob(response.data);
      
      // Poll for job status
      const jobId = response.data.job_id;
      pollJobStatus(jobId);

    } catch (error: any) {
      console.error('Bulk conversion failed:', error);
      setError(
        error.response?.data?.detail || 
        'Failed to start bulk conversion. Please try again.'
      );
      setBulkLoading(false);
    }
  };

  const pollJobStatus = async (jobId: string) => {
    try {
      const response = await api.get(`/jobs/${jobId}/status`);
      const job = response.data;
      setBulkJob(job);

      if (job.status === 'completed') {
        setBulkResults(job.results || []);
        setBulkLoading(false);
      } else if (job.status === 'failed') {
        setError(job.error || 'Bulk conversion failed');
        setBulkLoading(false);
      } else {
        // Continue polling
        setTimeout(() => pollJobStatus(jobId), 2000);
      }
    } catch (error) {
      console.error('Failed to get job status:', error);
      setBulkLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const downloadResults = () => {
    if (bulkResults.length === 0) return;

    const csvContent = [
      'ASIN,FNSKU,Confidence,Method,Marketplace,Error',
      ...bulkResults.map(result => 
        `${result.asin},${result.fnsku || ''},${result.confidence || ''},${result.method || ''},${result.marketplace},${result.error || ''}`
      )
    ].join('\\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'fnsku_conversion_results.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const downloadTemplate = () => {
    const csvContent = [
      'asin,marketplace',
      'B08N5WRWNW,US',
      'B0123456789,UK',
      'B9876543210,DE'
    ].join('\\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'bulk_conversion_template.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const clearResults = () => {
    setSingleResult(null);
    setBulkResults([]);
    setBulkJob(null);
    setBulkFile(null);
    setError(null);
    reset();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">FNSKU Converter</h1>
          <p className="mt-2 text-gray-600">
            Convert Amazon ASINs to FNSKUs for inventory management and tracking
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-8">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6">
              <button
                onClick={() => setActiveTab('single')}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'single'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <Zap className="h-4 w-4 inline mr-2" />
                Single Conversion
              </button>
              <button
                onClick={() => setActiveTab('bulk')}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'bulk'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <Upload className="h-4 w-4 inline mr-2" />
                Bulk Conversion
              </button>
            </nav>
          </div>

          <div className="p-6">
            {activeTab === 'single' && (
              <div className="space-y-6">
                <form onSubmit={handleSubmit(onSingleSubmit)} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="md:col-span-2">
                      <label htmlFor="asin" className="block text-sm font-medium text-gray-700 mb-1">
                        ASIN
                      </label>
                      <input
                        {...register('asin')}
                        type="text"
                        placeholder="e.g., B08N5WRWNW"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                      />
                      {errors.asin && (
                        <p className="mt-1 text-sm text-red-600">{errors.asin.message}</p>
                      )}
                    </div>

                    <div>
                      <label htmlFor="marketplace" className="block text-sm font-medium text-gray-700 mb-1">
                        Marketplace
                      </label>
                      <select
                        {...register('marketplace')}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                      >
                        <option value="US">United States</option>
                        <option value="UK">United Kingdom</option>
                        <option value="DE">Germany</option>
                        <option value="FR">France</option>
                        <option value="IT">Italy</option>
                        <option value="ES">Spain</option>
                        <option value="CA">Canada</option>
                        <option value="JP">Japan</option>
                        <option value="AU">Australia</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex items-center space-x-4">
                    <button
                      type="submit"
                      disabled={loading}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                    >
                      {loading ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Package className="h-4 w-4 mr-2" />
                      )}
                      {loading ? 'Converting...' : 'Convert to FNSKU'}
                    </button>

                    {singleResult && (
                      <button
                        type="button"
                        onClick={clearResults}
                        className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Clear
                      </button>
                    )}
                  </div>
                </form>

                {/* Single Result */}
                {singleResult && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
                        <div>
                          <p className="font-medium text-green-800">Conversion Successful</p>
                          <p className="text-sm text-green-600">
                            ASIN: {singleResult.asin} → FNSKU: {singleResult.fnsku}
                          </p>
                          <p className="text-xs text-green-600">
                            Confidence: {singleResult.confidence}% • Method: {singleResult.method}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => copyToClipboard(singleResult.fnsku)}
                        className="inline-flex items-center px-3 py-1 border border-green-300 text-sm font-medium rounded-md text-green-700 bg-white hover:bg-green-50"
                      >
                        <Copy className="h-4 w-4 mr-1" />
                        Copy FNSKU
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'bulk' && (
              <div className="space-y-6">
                {/* File Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Upload CSV File
                  </label>
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                    <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <div className="space-y-2">
                      <p className="text-sm text-gray-600">
                        Drop your CSV file here, or{' '}
                        <label className="text-indigo-600 hover:text-indigo-500 cursor-pointer">
                          browse
                          <input
                            type="file"
                            accept=".csv"
                            onChange={handleFileUpload}
                            className="hidden"
                          />
                        </label>
                      </p>
                      <p className="text-xs text-gray-500">
                        CSV format: asin,marketplace (max 5MB)
                      </p>
                    </div>
                  </div>

                  {bulkFile && (
                    <div className="mt-4 flex items-center justify-between bg-gray-50 rounded-lg p-3">
                      <div className="flex items-center">
                        <FileText className="h-5 w-5 text-gray-400 mr-2" />
                        <span className="text-sm text-gray-900">{bulkFile.name}</span>
                        <span className="ml-2 text-xs text-gray-500">
                          ({(bulkFile.size / 1024).toFixed(1)} KB)
                        </span>
                      </div>
                      <button
                        onClick={() => setBulkFile(null)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center space-x-4">
                  <button
                    onClick={handleBulkSubmit}
                    disabled={!bulkFile || bulkLoading}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                  >
                    {bulkLoading ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Upload className="h-4 w-4 mr-2" />
                    )}
                    {bulkLoading ? 'Processing...' : 'Start Bulk Conversion'}
                  </button>

                  <button
                    onClick={downloadTemplate}
                    className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download Template
                  </button>
                </div>

                {/* Job Status */}
                {bulkJob && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-blue-800">
                          Job Status: {bulkJob.status.charAt(0).toUpperCase() + bulkJob.status.slice(1)}
                        </p>
                        <p className="text-sm text-blue-600">
                          Progress: {bulkJob.completed_items}/{bulkJob.total_items} items
                          {bulkJob.failed_items > 0 && ` (${bulkJob.failed_items} failed)`}
                        </p>
                      </div>
                      {bulkJob.status === 'completed' && (
                        <button
                          onClick={downloadResults}
                          className="inline-flex items-center px-3 py-1 border border-blue-300 text-sm font-medium rounded-md text-blue-700 bg-white hover:bg-blue-50"
                        >
                          <Download className="h-4 w-4 mr-1" />
                          Download Results
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* Bulk Results Preview */}
                {bulkResults.length > 0 && (
                  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                    <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                      <h3 className="text-sm font-medium text-gray-900">
                        Conversion Results ({bulkResults.length} items)
                      </h3>
                    </div>
                    <div className="max-h-64 overflow-y-auto">
                      {bulkResults.slice(0, 10).map((result, index) => (
                        <div key={index} className="px-4 py-3 border-b border-gray-100 last:border-b-0">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm font-medium text-gray-900">
                                {result.asin} → {result.fnsku || 'Failed'}
                              </p>
                              <p className="text-xs text-gray-500">
                                {result.error || `${result.confidence}% confidence, ${result.method}`}
                              </p>
                            </div>
                            {result.fnsku ? (
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            ) : (
                              <AlertCircle className="h-4 w-4 text-red-500" />
                            )}
                          </div>
                        </div>
                      ))}
                      {bulkResults.length > 10 && (
                        <div className="px-4 py-3 text-center text-sm text-gray-500">
                          ... and {bulkResults.length - 10} more results
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-8">
            <div className="flex items-center">
              <AlertCircle className="h-5 w-5 text-red-400 mr-2" />
              <span className="text-red-700">{error}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}