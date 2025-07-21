import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { api } from '../lib/api';
import { 
  Search, 
  Loader2,
  AlertCircle
} from 'lucide-react';
import { DataVisualizationTabs } from '../components/DataVisualizationTabs';

const productQuerySchema = z.object({
  asin: z.string()
    .min(10, 'ASIN must be at least 10 characters')
    .max(10, 'ASIN must be exactly 10 characters')
    .regex(/^[A-Z0-9]+$/, 'ASIN must contain only uppercase letters and numbers'),
  marketplace: z.enum(['US', 'UK', 'DE', 'FR', 'IT', 'ES', 'CA', 'JP', 'AU']),
});

type ProductQueryForm = z.infer<typeof productQuerySchema>;

interface ProductData {
  asin: string;
  title: string;
  brand: string;
  price: {
    currency: string;
    amount: number;
    formatted: string;
  };
  rating: {
    value: number;
    total_reviews: number;
  };
  images: {
    url: string;
    variant: string;
  }[];
  main_image: string;
  description: string;
  features: string[];
  category: string;
  availability: string;
  in_stock: boolean;
  marketplace: string;
  data_source: string;
  last_updated: string;
}

export function ProductQuery() {
  const [productData, setProductData] = useState<ProductData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ProductQueryForm>({
    resolver: zodResolver(productQuerySchema),
    defaultValues: {
      marketplace: 'US',
    },
  });

  const onSubmit = async (data: ProductQueryForm) => {
    setLoading(true);
    setError(null);
    setProductData(null);

    try {
      const response = await api.post('/products/asin', data);
      setProductData(response.data.data);
    } catch (error: any) {
      console.error('Product query failed:', error);
      setError(
        error.response?.data?.error?.message ||
        error.response?.data?.detail || 
        'Failed to fetch product data. Please check your ASIN and try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleNewQuery = () => {
    setProductData(null);
    setError(null);
    reset();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Product Lookup</h1>
          <p className="mt-2 text-gray-600">
            Search for Amazon products using ASIN to get detailed information and market data
          </p>
        </div>

        {/* Enhanced Query Form */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Product Lookup</h2>
          
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="md:col-span-2">
                <label htmlFor="asin" className="block text-sm font-medium text-gray-700 mb-2">
                  Amazon ASIN
                </label>
                <div className="relative">
                  <input
                    {...register('asin')}
                    type="text"
                    placeholder="Enter 10-character ASIN (e.g., B08N5WRWNW)"
                    className={`w-full px-4 py-3 border rounded-lg shadow-sm text-sm transition-colors ${
                      errors.asin 
                        ? 'border-red-300 focus:border-red-500 focus:ring-red-500' 
                        : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'
                    } focus:outline-none focus:ring-2 focus:ring-offset-0`}
                  />
                  {errors.asin && (
                    <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                      <AlertCircle className="h-5 w-5 text-red-400" />
                    </div>
                  )}
                </div>
                {errors.asin && (
                  <p className="mt-2 text-sm text-red-600" role="alert">
                    {errors.asin.message}
                  </p>
                )}
              </div>

              <div>
                <label htmlFor="marketplace" className="block text-sm font-medium text-gray-700 mb-2">
                  Marketplace
                </label>
                <select
                  {...register('marketplace')}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm bg-white"
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

            <div className="flex justify-between items-center">
              <div className="flex items-center space-x-4">
                <button
                  type="submit"
                  disabled={loading}
                  className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                      Searching...
                    </>
                  ) : (
                    <>
                      <Search className="h-5 w-5 mr-2" />
                      Search Product
                    </>
                  )}
                </button>

                {productData && (
                  <button
                    type="button"
                    onClick={handleNewQuery}
                    className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-lg shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
                  >
                    New Search
                  </button>
                )}
              </div>
              
              {productData && (
                <div className="text-sm text-gray-500">
                  Found: {productData.title ? productData.title.substring(0, 50) + '...' : 'Product data'}
                </div>
              )}
            </div>
          </form>
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

        {/* Enhanced Product Data Display with Tabs */}
        {productData && (
          <DataVisualizationTabs 
            productData={productData} 
            loading={loading}
          />
        )}
      </div>
    </div>
  );
}