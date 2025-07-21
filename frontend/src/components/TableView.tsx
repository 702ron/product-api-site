import React from 'react';
import { 
  Copy, 
  CheckCircle, 
  DollarSign, 
  Star, 
  Package, 
  Truck,
  Tag,
  Hash,
  ExternalLink,
  Image as ImageIcon,
  FileText,
  Ruler
} from 'lucide-react';
import type { ProductData } from './DataVisualizationTabs';

interface TableViewProps {
  productData: ProductData;
  onCopy: (text: string, field: string) => Promise<void>;
  copiedField: string | null;
}

export const TableView: React.FC<TableViewProps> = React.memo(({ 
  productData, 
  onCopy, 
  copiedField 
}) => {
  const formatValue = (value: any): string => {
    if (Array.isArray(value)) {
      return value.join(', ');
    }
    if (typeof value === 'object' && value !== null) {
      return JSON.stringify(value);
    }
    if (value === null || value === undefined) {
      return 'N/A';
    }
    return String(value);
  };

  const getFieldIcon = (key: string) => {
    const iconMap: Record<string, any> = {
      price: DollarSign,
      rating: Star,
      availability: Truck,
      brand: Tag,
      category: Tag,
      main_image: ImageIcon,
      images: ImageIcon,
      description: FileText,
      features: FileText,
      asin: Hash,
      title: FileText,
      in_stock: Truck,
      marketplace: Tag,
      data_source: Package,
      last_updated: FileText
    };
    const Icon = iconMap[key] || Hash;
    return <Icon className="h-4 w-4 text-gray-400" />;
  };

  const getFieldDisplayName = (key: string): string => {
    const displayNames: Record<string, string> = {
      asin: 'ASIN',
      title: 'Product Title',
      price: 'Price',
      rating: 'Rating',
      availability: 'Availability',
      brand: 'Brand',
      category: 'Category',
      main_image: 'Main Image',
      images: 'Product Images',
      features: 'Features',
      description: 'Description',
      in_stock: 'In Stock',
      marketplace: 'Marketplace',
      data_source: 'Data Source',
      last_updated: 'Last Updated'
    };
    return displayNames[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const isUrl = (value: string): boolean => {
    try {
      new URL(value);
      return true;
    } catch {
      return false;
    }
  };

  const renderValue = (key: string, value: any) => {
    const formattedValue = formatValue(value);
    
    if (key === 'image_url' && isUrl(formattedValue)) {
      return (
        <div className="flex items-center space-x-2">
          <img 
            src={formattedValue} 
            alt="Product" 
            className="w-8 h-8 object-cover rounded border"
            onError={(e) => {
              e.currentTarget.style.display = 'none';
            }}
          />
          <span className="text-sm text-gray-600 truncate">{formattedValue}</span>
        </div>
      );
    }
    
    if ((key === 'product_url' || key === 'image_url') && isUrl(formattedValue)) {
      return (
        <a 
          href={formattedValue} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-indigo-600 hover:text-indigo-500 text-sm truncate flex items-center"
        >
          <span className="truncate">{formattedValue}</span>
          <ExternalLink className="h-3 w-3 ml-1 flex-shrink-0" />
        </a>
      );
    }

    if (key === 'price' && typeof value === 'object' && value?.formatted) {
      return (
        <span className="text-sm text-gray-600">
          {value.formatted} ({value.currency})
        </span>
      );
    }

    if (key === 'rating' && typeof value === 'object' && value?.value) {
      return (
        <span className="text-sm text-gray-600">
          {value.value}/5 ({value.total_reviews} reviews)
        </span>
      );
    }

    if (key === 'main_image' && isUrl(formattedValue)) {
      return (
        <div className="flex items-center space-x-2">
          <img 
            src={formattedValue} 
            alt="Product" 
            className="w-8 h-8 object-cover rounded border"
            onError={(e) => {
              e.currentTarget.style.display = 'none';
            }}
          />
          <span className="text-sm text-gray-600 truncate">{formattedValue}</span>
        </div>
      );
    }

    if (key === 'estimated_sales_rank' && value) {
      return (
        <span className="text-sm text-gray-600">
          #{parseInt(formattedValue).toLocaleString()}
        </span>
      );
    }

    return (
      <span className="text-sm text-gray-600 break-words">
        {formattedValue.length > 100 
          ? `${formattedValue.substring(0, 100)}...` 
          : formattedValue
        }
      </span>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-gray-900">Product Data Table</h3>
        <span className="text-sm text-gray-500">
          {Object.keys(productData).length} fields
        </span>
      </div>
      
      <div className="space-y-1 max-h-96 overflow-y-auto">
        {Object.entries(productData).map(([key, value]) => (
          <div 
            key={key} 
            className="group flex items-center justify-between py-3 px-4 hover:bg-gray-50 rounded-lg border border-transparent hover:border-gray-200 transition-colors"
          >
            <div className="flex items-center space-x-3 min-w-0 flex-1">
              {getFieldIcon(key)}
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900">
                  {getFieldDisplayName(key)}
                </p>
                <div className="mt-1">
                  {renderValue(key, value)}
                </div>
              </div>
            </div>
            
            <button
              onClick={() => onCopy(formatValue(value), key)}
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-200 transition-opacity focus:opacity-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              title="Copy value"
              aria-label={`Copy ${getFieldDisplayName(key)}`}
            >
              {copiedField === key ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : (
                <Copy className="h-4 w-4 text-gray-400" />
              )}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
});