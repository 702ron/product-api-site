import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { api } from '../lib/api';
import { 
  Search, 
  Loader2,
  AlertCircle,
  Package,
  Barcode,
  Hash,
  Info,
  ChevronRight,
  Star
} from 'lucide-react';
import { DataVisualizationTabs } from '../components/DataVisualizationTabs';

// Multi-input lookup schema
const multiLookupSchema = z.object({
  input_value: z.string()
    .min(1, 'Input is required')
    .max(50, 'Input too long'),
  marketplace: z.enum(['US', 'UK', 'DE', 'FR', 'IT', 'ES', 'CA', 'JP', 'AU']),
  manual_type: z.enum(['asin', 'fnsku', 'gtin_upc']).optional(),
});

// Product search schema
const productSearchSchema = z.object({
  search_term: z.string()
    .min(3, 'Search term must be at least 3 characters')
    .max(200, 'Search term too long'),
  marketplace: z.enum(['US', 'UK', 'DE', 'FR', 'IT', 'ES', 'CA', 'JP', 'AU']),
  max_page: z.number().min(1).max(5),
});

type MultiLookupForm = z.infer<typeof multiLookupSchema>;
type ProductSearchForm = z.infer<typeof productSearchSchema>;

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

interface SearchResult {
  asin: string;
  title: string;
  image?: string;
  price?: {
    amount: number;
    currency: string;
    formatted: string;
  };
  rating?: {
    value: number;
    total_reviews: number;
  };
  availability: string;
  sponsored: boolean;
}

interface InputTypeDetection {
  type: 'asin' | 'fnsku' | 'gtin_upc';
  confidence: number;
  cost: number;
}

export function ProductQuery() {
  const [activeTab, setActiveTab] = useState<'lookup' | 'search'>('lookup');
  const [productData, setProductData] = useState<ProductData | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchPagination, setSearchPagination] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detectedType, setDetectedType] = useState<InputTypeDetection | null>(null);
  const [creditsUsed, setCreditsUsed] = useState<number>(0);

  // Multi-input lookup form
  const multiLookupForm = useForm<MultiLookupForm>({
    resolver: zodResolver(multiLookupSchema),
    defaultValues: {
      marketplace: 'US',
    },
  });

  // Product search form
  const searchForm = useForm<ProductSearchForm>({
    resolver: zodResolver(productSearchSchema),
    defaultValues: {
      marketplace: 'US',
      max_page: 1,
      search_term: '',
    },
  });

  // Input type detection logic
  const detectInputType = (value: string): InputTypeDetection | null => {
    const trimmed = value.trim().toUpperCase();
    
    if (/^B[0-9A-Z]{9}$/.test(trimmed) || /^[0-9]{10}$/.test(trimmed)) {
      return { type: 'asin', confidence: 1.0, cost: 1 };
    } else if (/^[A-Z0-9]{10}$/.test(trimmed) && !trimmed.startsWith('B')) {
      return { type: 'fnsku', confidence: 0.95, cost: 10 };
    } else if (/^[0-9]{8}$|^[0-9]{12,14}$/.test(trimmed)) {
      return { type: 'gtin_upc', confidence: 1.0, cost: 1 };
    }
    
    return null;
  };

  // Handle multi-input lookup
  const handleMultiLookup = async (data: MultiLookupForm) => {
    setLoading(true);
    setError(null);
    setProductData(null);
    setSearchResults([]);

    try {
      const response = await api.post('/products/multi-lookup', data);
      setProductData(response.data.product as ProductData);
      setCreditsUsed(response.data.credits_used as number);
    } catch (error: any) {
      console.error('Multi-lookup failed:', error);
      setError(
        error.response?.data?.detail || 
        'Failed to fetch product data. Please check your input and try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  // Handle product search
  const handleProductSearch = async (data: ProductSearchForm) => {
    setLoading(true);
    setError(null);
    setProductData(null);
    setSearchResults([]);

    try {
      const response = await api.post('/products/search', data);
      setSearchResults(response.data.results as SearchResult[]);
      setSearchPagination(response.data.pagination);
      setCreditsUsed(response.data.credits_used as number);
    } catch (error: any) {
      console.error('Product search failed:', error);
      setError(
        error.response?.data?.detail || 
        'Failed to search products. Please try a different search term.'
      );
    } finally {
      setLoading(false);
    }
  };

  // Handle selecting a search result to get full product details
  const handleSelectSearchResult = async (asin: string, marketplace: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.post('/products/asin', { asin, marketplace });
      setProductData(response.data.data as ProductData);
      // Don't reset search results - keep them visible
    } catch (error: any) {
      console.error('ASIN lookup failed:', error);
      setError(
        error.response?.data?.detail || 
        'Failed to fetch full product details.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleNewQuery = () => {
    setProductData(null);
    setSearchResults([]);
    setSearchPagination(null);
    setError(null);
    setDetectedType(null);
    setCreditsUsed(0);
    multiLookupForm.reset();
    searchForm.reset();
  };

  // Watch input changes for type detection
  const inputValue = multiLookupForm.watch('input_value');
  useEffect(() => {
    if (inputValue) {
      const detected = detectInputType(inputValue);
      setDetectedType(detected);
    } else {
      setDetectedType(null);
    }
  }, [inputValue]);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Product Lookup & Search</h1>
          <p className="mt-2 text-gray-600">
            Find Amazon products using ASIN, FNSKU, GTIN/UPC, or search by product name
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="mb-8">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('lookup')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'lookup'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Package className="w-5 h-5 inline mr-2" />
                Direct Lookup
              </button>
              <button
                onClick={() => setActiveTab('search')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'search'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Search className="w-5 h-5 inline mr-2" />
                Product Search
              </button>
            </nav>
          </div>
        </div>

        {/* Multi-Input Lookup Tab */}
        {activeTab === 'lookup' && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Multi-Input Product Lookup</h2>
            
            <form onSubmit={multiLookupForm.handleSubmit(handleMultiLookup)} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Product Identifier
                  </label>
                  <div className="relative">
                    <input
                      {...multiLookupForm.register('input_value')}
                      type="text"
                      placeholder="Enter ASIN (B08N5WRWNW), FNSKU (X001ABC123), or GTIN/UPC (123456789012)"
                      className={`w-full px-4 py-3 border rounded-lg shadow-sm text-sm transition-colors ${
                        multiLookupForm.formState.errors.input_value
                          ? 'border-red-300 focus:border-red-500 focus:ring-red-500' 
                          : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'
                      } focus:outline-none focus:ring-2 focus:ring-offset-0`}
                    />
                    {multiLookupForm.formState.errors.input_value && (
                      <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                        <AlertCircle className="h-5 w-5 text-red-400" />
                      </div>
                    )}
                  </div>
                  {multiLookupForm.formState.errors.input_value && (
                    <p className="mt-2 text-sm text-red-600">
                      {multiLookupForm.formState.errors.input_value.message}
                    </p>
                  )}
                  
                  {/* Input Type Detection Display */}
                  {detectedType && (
                    <div className="mt-2 flex items-center space-x-2 text-sm">
                      <div className={`flex items-center space-x-1 px-2 py-1 rounded-full ${
                        detectedType.type === 'asin' ? 'bg-blue-100 text-blue-800' :
                        detectedType.type === 'fnsku' ? 'bg-purple-100 text-purple-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {detectedType.type === 'asin' && <Hash className="w-4 h-4" />}
                        {detectedType.type === 'fnsku' && <Package className="w-4 h-4" />}
                        {detectedType.type === 'gtin_upc' && <Barcode className="w-4 h-4" />}
                        <span className="uppercase font-medium">{detectedType.type.replace('_', '/')}</span>
                      </div>
                      <span className="text-gray-500">•</span>
                      <span className="text-gray-600">{detectedType.cost} credit{detectedType.cost > 1 ? 's' : ''}</span>
                      {detectedType.confidence < 1 && (
                        <span className="text-amber-600">({Math.round(detectedType.confidence * 100)}% confidence)</span>
                      )}
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Marketplace
                  </label>
                  <select
                    {...multiLookupForm.register('marketplace')}
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

              {/* Manual Type Override */}
              <div className="border-t pt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Manual Type Override (Optional)
                </label>
                <select
                  {...multiLookupForm.register('manual_type')}
                  className="w-full md:w-auto px-4 py-2 border border-gray-300 rounded-lg text-sm bg-white"
                >
                  <option value="">Auto-detect</option>
                  <option value="asin">ASIN (1 credit)</option>
                  <option value="fnsku">FNSKU (10 credits)</option>
                  <option value="gtin_upc">GTIN/UPC (1 credit)</option>
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  Leave on "Auto-detect" unless the detection is incorrect
                </p>
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
                        Looking up...
                      </>
                    ) : (
                      <>
                        <Search className="h-5 w-5 mr-2" />
                        Lookup Product
                      </>
                    )}
                  </button>

                  {(productData || searchResults.length > 0) && (
                    <button
                      type="button"
                      onClick={handleNewQuery}
                      className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-lg shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
                    >
                      New Search
                    </button>
                  )}
                </div>
                
                {creditsUsed > 0 && (
                  <div className="text-sm text-gray-500">
                    Credits used: {creditsUsed}
                  </div>
                )}
              </div>
            </form>
          </div>
        )}

        {/* Product Search Tab */}
        {activeTab === 'search' && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Product Name Search</h2>
            
            <form onSubmit={searchForm.handleSubmit(handleProductSearch)} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Search Term
                  </label>
                  <input
                    {...searchForm.register('search_term')}
                    type="text"
                    placeholder="e.g., wireless mouse, bluetooth headphones"
                    className={`w-full px-4 py-3 border rounded-lg shadow-sm text-sm transition-colors ${
                      searchForm.formState.errors.search_term
                        ? 'border-red-300 focus:border-red-500 focus:ring-red-500' 
                        : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'
                    } focus:outline-none focus:ring-2 focus:ring-offset-0`}
                  />
                  {searchForm.formState.errors.search_term && (
                    <p className="mt-2 text-sm text-red-600">
                      {searchForm.formState.errors.search_term.message}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Max Pages
                  </label>
                  <select
                    {...searchForm.register('max_page', { valueAsNumber: true })}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg shadow-sm text-sm bg-white"
                  >
                    <option value={1}>1 page (1 credit)</option>
                    <option value={2}>2 pages (2 credits)</option>
                    <option value={3}>3 pages (3 credits)</option>
                    <option value={4}>4 pages (4 credits)</option>
                    <option value={5}>5 pages (5 credits)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Marketplace
                  </label>
                  <select
                    {...searchForm.register('marketplace')}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg shadow-sm text-sm bg-white"
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
                        Search Products
                      </>
                    )}
                  </button>

                  {(productData || searchResults.length > 0) && (
                    <button
                      type="button"
                      onClick={handleNewQuery}
                      className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-lg shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
                    >
                      New Search
                    </button>
                  )}
                </div>
                
                {creditsUsed > 0 && (
                  <div className="text-sm text-gray-500">
                    Credits used: {creditsUsed}
                  </div>
                )}
              </div>
            </form>
          </div>
        )}

        {/* Search Results Display */}
        {searchResults.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-semibold text-gray-900">Search Results</h3>
              {searchPagination && (
                <div className="text-sm text-gray-600">
                  Page {searchPagination.current_page} of {searchPagination.total_pages} 
                  ({searchResults.length} results)
                </div>
              )}
            </div>
            
            <div className="grid gap-4">
              {searchResults.map((result, index) => (
                <div 
                  key={`${result.asin}-${index}`}
                  className="flex items-center space-x-4 p-4 border border-gray-200 rounded-lg hover:border-indigo-300 hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => handleSelectSearchResult(result.asin, searchForm.getValues('marketplace'))}
                >
                  {/* Product Image */}
                  {result.image && (
                    <div className="flex-shrink-0 w-16 h-16">
                      <img
                        src={result.image}
                        alt={result.title}
                        className="w-full h-full object-contain rounded"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none';
                        }}
                      />
                    </div>
                  )}
                  
                  {/* Product Info */}
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-gray-900 truncate">
                      {result.title}
                    </h4>
                    <div className="mt-1 flex items-center space-x-4 text-sm text-gray-500">
                      <span>ASIN: {result.asin}</span>
                      {result.price && (
                        <span>• {result.price.formatted}</span>
                      )}
                      {result.rating && (
                        <div className="flex items-center">
                          <span>•</span>
                          <Star className="w-4 h-4 text-yellow-400 ml-1" />
                          <span className="ml-1">{result.rating.value}</span>
                          <span className="ml-1">({result.rating.total_reviews})</span>
                        </div>
                      )}
                    </div>
                    <div className="mt-1 flex items-center space-x-2">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        result.availability === 'in_stock' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {result.availability.replace('_', ' ')}
                      </span>
                      {result.sponsored && (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          Sponsored
                        </span>
                      )}
                    </div>
                  </div>
                  
                  {/* Action Icon */}
                  <div className="flex-shrink-0">
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  </div>
                </div>
              ))}
            </div>
            
            <div className="mt-4 text-center">
              <p className="text-sm text-gray-600">
                Click on any product to view full details
              </p>
            </div>
          </div>
        )}

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