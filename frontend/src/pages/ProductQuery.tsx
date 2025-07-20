import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { api } from '../lib/api';
import { 
  Search, 
  Package, 
  DollarSign, 
  Star, 
  Truck, 
  Calendar,
  ExternalLink,
  Loader2,
  AlertCircle,
  CheckCircle
} from 'lucide-react';

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
  price: number;
  currency: string;
  rating: number;
  review_count: number;
  availability: string;
  brand: string;
  category: string;
  image_url: string;
  product_url: string;
  estimated_sales_rank: number;
  dimensions: string;
  weight: string;
  features: string[];
  description: string;
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
      setProductData(response.data.product);
    } catch (error: any) {
      console.error('Product query failed:', error);
      setError(
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

        {/* Query Form */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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
                  <Search className="h-4 w-4 mr-2" />
                )}
                {loading ? 'Searching...' : 'Search Product'}
              </button>

              {productData && (
                <button
                  type="button"
                  onClick={handleNewQuery}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  New Search
                </button>
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

        {/* Product Data Display */}
        {productData && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center">
                <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
                <h2 className="text-lg font-semibold text-gray-900">Product Information</h2>
              </div>
            </div>

            <div className="p-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Product Image and Basic Info */}
                <div>
                  <div className="aspect-square w-full max-w-md mx-auto bg-gray-100 rounded-lg overflow-hidden mb-4">
                    <img
                      src={productData.image_url}
                      alt={productData.title}
                      className="w-full h-full object-contain"
                      onError={(e) => {
                        e.currentTarget.src = '/placeholder-product.png';
                      }}
                    />
                  </div>
                  
                  <div className="text-center space-y-2">
                    <p className="text-sm text-gray-600">ASIN: {productData.asin}</p>
                    <a
                      href={productData.product_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center text-indigo-600 hover:text-indigo-500"
                    >
                      View on Amazon
                      <ExternalLink className="h-4 w-4 ml-1" />
                    </a>
                  </div>
                </div>

                {/* Product Details */}
                <div className="space-y-6">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">{productData.title}</h3>
                    <p className="text-gray-600 mb-4">{productData.brand}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center">
                        <DollarSign className="h-5 w-5 text-green-600 mr-2" />
                        <div>
                          <p className="text-sm text-gray-600">Price</p>
                          <p className="text-lg font-semibold text-gray-900">
                            {productData.currency} {productData.price}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center">
                        <Star className="h-5 w-5 text-yellow-500 mr-2" />
                        <div>
                          <p className="text-sm text-gray-600">Rating</p>
                          <p className="text-lg font-semibold text-gray-900">
                            {productData.rating}/5 ({productData.review_count} reviews)
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center">
                        <Truck className="h-5 w-5 text-blue-600 mr-2" />
                        <div>
                          <p className="text-sm text-gray-600">Availability</p>
                          <p className="text-lg font-semibold text-gray-900">{productData.availability}</p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center">
                        <Package className="h-5 w-5 text-purple-600 mr-2" />
                        <div>
                          <p className="text-sm text-gray-600">Sales Rank</p>
                          <p className="text-lg font-semibold text-gray-900">
                            #{productData.estimated_sales_rank?.toLocaleString() || 'N/A'}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Additional Details */}
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-medium text-gray-900 mb-2">Category</h4>
                      <p className="text-gray-600">{productData.category}</p>
                    </div>

                    <div>
                      <h4 className="font-medium text-gray-900 mb-2">Dimensions & Weight</h4>
                      <p className="text-gray-600">
                        {productData.dimensions} • {productData.weight}
                      </p>
                    </div>

                    {productData.features && productData.features.length > 0 && (
                      <div>
                        <h4 className="font-medium text-gray-900 mb-2">Key Features</h4>
                        <ul className="list-disc list-inside space-y-1 text-gray-600">
                          {productData.features.slice(0, 5).map((feature, index) => (
                            <li key={index}>{feature}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {productData.description && (
                      <div>
                        <h4 className="font-medium text-gray-900 mb-2">Description</h4>
                        <p className="text-gray-600 text-sm leading-relaxed">
                          {productData.description.length > 300
                            ? `${productData.description.substring(0, 300)}...`
                            : productData.description
                          }
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}