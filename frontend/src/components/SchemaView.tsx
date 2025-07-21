import React from 'react';
import { Hash, Info } from 'lucide-react';
import type { ProductData } from './DataVisualizationTabs';

interface SchemaViewProps {
  productData: ProductData;
}

export const SchemaView: React.FC<SchemaViewProps> = React.memo(({ productData }) => {
  const getDataType = (value: any): string => {
    if (value === null || value === undefined) return 'null';
    if (Array.isArray(value)) return 'array';
    return typeof value;
  };

  const getArrayElementType = (array: any[]): string => {
    if (array.length === 0) return 'unknown';
    const firstElement = array[0];
    return getDataType(firstElement);
  };

  const getTypeColor = (type: string): string => {
    const colorMap: Record<string, string> = {
      string: 'text-blue-600 bg-blue-50',
      number: 'text-green-600 bg-green-50',
      boolean: 'text-purple-600 bg-purple-50',
      array: 'text-orange-600 bg-orange-50',
      object: 'text-indigo-600 bg-indigo-50',
      null: 'text-gray-600 bg-gray-50'
    };
    return colorMap[type] || 'text-gray-600 bg-gray-50';
  };

  const getFieldDescription = (key: string): string => {
    const descriptions: Record<string, string> = {
      asin: 'Amazon Standard Identification Number - unique product identifier',
      title: 'Product name/title as shown on Amazon',
      price: 'Current product price in the specified currency',
      currency: 'Currency code (USD, EUR, GBP, etc.)',
      rating: 'Average customer rating (1-5 stars)',
      review_count: 'Total number of customer reviews',
      availability: 'Product availability status (In Stock, Out of Stock, etc.)',
      brand: 'Product brand/manufacturer name',
      category: 'Primary product category classification',
      image_url: 'URL to product main image',
      product_url: 'Direct link to product page on Amazon',
      estimated_sales_rank: 'Estimated sales ranking in category',
      dimensions: 'Product physical dimensions',
      weight: 'Product weight specification',
      features: 'Array of key product features and benefits',
      description: 'Detailed product description text'
    };
    return descriptions[key] || 'Product data field';
  };

  const getFieldRequirements = (key: string): { required: boolean; nullable: boolean } => {
    const requirements: Record<string, { required: boolean; nullable: boolean }> = {
      asin: { required: true, nullable: false },
      title: { required: true, nullable: false },
      price: { required: false, nullable: true },
      currency: { required: false, nullable: true },
      rating: { required: false, nullable: true },
      review_count: { required: false, nullable: true },
      availability: { required: false, nullable: true },
      brand: { required: false, nullable: true },
      category: { required: false, nullable: true },
      image_url: { required: false, nullable: true },
      product_url: { required: false, nullable: true },
      estimated_sales_rank: { required: false, nullable: true },
      dimensions: { required: false, nullable: true },
      weight: { required: false, nullable: true },
      features: { required: false, nullable: true },
      description: { required: false, nullable: true }
    };
    return requirements[key] || { required: false, nullable: true };
  };

  const getValueExample = (key: string, value: any): string => {
    const type = getDataType(value);
    if (type === 'null') return 'null';
    
    const examples: Record<string, string> = {
      asin: 'B08N5WRWNW',
      title: 'Example Product Name',
      price: '29.99',
      currency: 'USD',
      rating: '4.5',
      review_count: '1,234',
      availability: 'In Stock',
      brand: 'Example Brand',
      category: 'Electronics > Computers',
      estimated_sales_rank: '1,234'
    };

    if (Array.isArray(value)) {
      return `[${value.length} items]`;
    }
    
    if (typeof value === 'string' && value.length > 50) {
      return `"${value.substring(0, 47)}..."`;
    }

    return examples[key] || String(value);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Data Schema</h3>
        <div className="flex items-center text-sm text-gray-500">
          <Info className="h-4 w-4 mr-1" />
          {Object.keys(productData).length} fields defined
        </div>
      </div>
      
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
        <p className="text-sm text-blue-800">
          <strong>Schema Overview:</strong> This shows the structure and data types of the product data. 
          Required fields are marked with a red asterisk (*).
        </p>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {Object.entries(productData).map(([key, value]) => {
          const dataType = getDataType(value);
          const typeColor = getTypeColor(dataType);
          const { required, nullable } = getFieldRequirements(key);
          const description = getFieldDescription(key);
          const example = getValueExample(key, value);
          
          return (
            <div 
              key={key} 
              className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-3">
                  <Hash className="h-4 w-4 text-gray-400" />
                  <div className="flex items-center space-x-2">
                    <code className="text-sm font-mono font-medium text-gray-900">
                      {key}
                      {required && <span className="text-red-500 ml-1">*</span>}
                    </code>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${typeColor}`}>
                      {dataType}
                      {Array.isArray(value) && value.length > 0 && (
                        <span className="ml-1">of {getArrayElementType(value)}</span>
                      )}
                    </span>
                  </div>
                </div>
                
                <div className="flex space-x-2">
                  {required && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium text-red-700 bg-red-100">
                      Required
                    </span>
                  )}
                  {nullable && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium text-gray-700 bg-gray-100">
                      Nullable
                    </span>
                  )}
                </div>
              </div>
              
              <p className="text-sm text-gray-600 mb-2">
                {description}
              </p>
              
              {Array.isArray(value) && value.length > 0 && (
                <div className="text-xs text-gray-500 mb-2">
                  <strong>Array Info:</strong> Contains {value.length} items of type {getArrayElementType(value)}
                </div>
              )}
              
              <div className="bg-gray-50 rounded p-2">
                <div className="text-xs text-gray-500 mb-1">Current Value:</div>
                <code className="text-xs font-mono text-gray-700 break-all">
                  {example}
                </code>
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-gray-50 rounded-lg p-4 mt-6">
        <h4 className="text-sm font-medium text-gray-900 mb-2">Type Definitions:</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
          <div className="flex items-center space-x-2">
            <span className="inline-block w-3 h-3 bg-blue-100 border border-blue-300 rounded"></span>
            <span className="text-gray-600">string - Text data</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="inline-block w-3 h-3 bg-green-100 border border-green-300 rounded"></span>
            <span className="text-gray-600">number - Numeric data</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="inline-block w-3 h-3 bg-orange-100 border border-orange-300 rounded"></span>
            <span className="text-gray-600">array - List of items</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="inline-block w-3 h-3 bg-purple-100 border border-purple-300 rounded"></span>
            <span className="text-gray-600">boolean - True/false</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="inline-block w-3 h-3 bg-indigo-100 border border-indigo-300 rounded"></span>
            <span className="text-gray-600">object - Nested data</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="inline-block w-3 h-3 bg-gray-100 border border-gray-300 rounded"></span>
            <span className="text-gray-600">null - No value</span>
          </div>
        </div>
      </div>
    </div>
  );
});