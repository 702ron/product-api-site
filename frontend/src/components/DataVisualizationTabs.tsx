import React, { useState } from 'react';
import { Tab } from '@headlessui/react';
import { 
  Table, 
  Code, 
  FileText
} from 'lucide-react';
import { TableView } from './TableView';
import { JsonView } from './JsonView';
import { SchemaView } from './SchemaView';

export interface ProductData {
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

interface DataVisualizationTabsProps {
  productData: ProductData;
  loading: boolean;
}

export const DataVisualizationTabs: React.FC<DataVisualizationTabsProps> = React.memo(({ 
  productData, 
  loading 
}) => {
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const tabs = [
    { id: 'table', name: 'Table', icon: Table },
    { id: 'json', name: 'JSON', icon: Code },
    { id: 'schema', name: 'Schema', icon: FileText }
  ];

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="animate-pulse space-y-4">
          <div className="flex space-x-4 border-b">
            {tabs.map((tab) => (
              <div key={tab.id} className="h-10 w-20 bg-gray-200 rounded"></div>
            ))}
          </div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <Tab.Group>
        <Tab.List className="flex border-b border-gray-200 bg-gray-50">
          {tabs.map((tab) => (
            <Tab
              key={tab.id}
              className={({ selected }) =>
                `relative min-w-0 flex-1 overflow-hidden py-4 px-6 text-sm font-medium text-center focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500 transition-colors ${
                  selected
                    ? 'text-indigo-600 bg-white border-b-2 border-indigo-600'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                }`
              }
            >
              <div className="flex items-center justify-center space-x-2">
                <tab.icon className="h-4 w-4" />
                <span>{tab.name}</span>
              </div>
            </Tab>
          ))}
        </Tab.List>
        
        <Tab.Panels>
          {/* Table Panel */}
          <Tab.Panel className="p-6">
            <TableView 
              productData={productData} 
              onCopy={copyToClipboard} 
              copiedField={copiedField} 
            />
          </Tab.Panel>
          
          {/* JSON Panel */}
          <Tab.Panel className="p-6">
            <JsonView 
              productData={productData} 
              onCopy={copyToClipboard} 
            />
          </Tab.Panel>
          
          {/* Schema Panel */}
          <Tab.Panel className="p-6">
            <SchemaView productData={productData} />
          </Tab.Panel>
        </Tab.Panels>
      </Tab.Group>
    </div>
  );
});