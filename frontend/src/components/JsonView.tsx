import React, { useState } from 'react';
import { Copy, CheckCircle, ChevronDown, ChevronRight } from 'lucide-react';
import type { ProductData } from './DataVisualizationTabs';

interface JsonViewProps {
  productData: ProductData;
  onCopy: (text: string, field: string) => Promise<void>;
}

interface JsonNodeProps {
  data: any;
  keyName?: string;
  depth?: number;
  isLast?: boolean;
}

const JsonNode: React.FC<JsonNodeProps> = ({ data, keyName, depth = 0 }) => {
  const [isCollapsed, setIsCollapsed] = useState(depth > 1);

  const getValueType = (value: any): string => {
    if (value === null) return 'null';
    if (Array.isArray(value)) return 'array';
    return typeof value;
  };

  const getValueColor = (type: string): string => {
    const colors = {
      string: 'text-green-600',
      number: 'text-blue-600',
      boolean: 'text-purple-600',
      null: 'text-gray-500',
      array: 'text-orange-600',
      object: 'text-indigo-600'
    };
    return colors[type as keyof typeof colors] || 'text-gray-700';
  };

  const formatValue = (value: any): string => {
    if (typeof value === 'string') {
      return `"${value}"`;
    }
    if (value === null) {
      return 'null';
    }
    return String(value);
  };

  const isExpandable = (value: any): boolean => {
    return (Array.isArray(value) && value.length > 0) || 
           (typeof value === 'object' && value !== null && Object.keys(value).length > 0);
  };

  const indent = depth * 20;

  if (Array.isArray(data)) {
    return (
      <div style={{ marginLeft: `${indent}px` }}>
        {keyName && (
          <div className="flex items-center mb-1">
            {isExpandable(data) && (
              <button
                onClick={() => setIsCollapsed(!isCollapsed)}
                className="flex items-center justify-center w-4 h-4 mr-1 hover:bg-gray-200 rounded"
                aria-label={isCollapsed ? 'Expand array' : 'Collapse array'}
              >
                {isCollapsed ? (
                  <ChevronRight className="w-3 h-3" />
                ) : (
                  <ChevronDown className="w-3 h-3" />
                )}
              </button>
            )}
            <span className="font-medium text-gray-700">"{keyName}":</span>
            <span className="ml-2 text-orange-600">[{data.length} items]</span>
          </div>
        )}
        
        {!isCollapsed && (
          <div className="border-l border-gray-200 ml-2">
            {data.map((item, index) => (
              <JsonNode
                key={index}
                data={item}
                keyName={index.toString()}
                depth={depth + 1}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  if (typeof data === 'object' && data !== null) {
    const entries = Object.entries(data);
    
    return (
      <div style={{ marginLeft: `${indent}px` }}>
        {keyName && (
          <div className="flex items-center mb-1">
            {isExpandable(data) && (
              <button
                onClick={() => setIsCollapsed(!isCollapsed)}
                className="flex items-center justify-center w-4 h-4 mr-1 hover:bg-gray-200 rounded"
                aria-label={isCollapsed ? 'Expand object' : 'Collapse object'}
              >
                {isCollapsed ? (
                  <ChevronRight className="w-3 h-3" />
                ) : (
                  <ChevronDown className="w-3 h-3" />
                )}
              </button>
            )}
            <span className="font-medium text-gray-700">"{keyName}":</span>
            <span className="ml-2 text-indigo-600">{`{${entries.length} properties}`}</span>
          </div>
        )}
        
        {!isCollapsed && (
          <div className="border-l border-gray-200 ml-2">
            {entries.map(([key, value]) => (
              <JsonNode
                key={key}
                data={value}
                keyName={key}
                depth={depth + 1}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  // Primitive values
  const type = getValueType(data);
  const colorClass = getValueColor(type);

  return (
    <div 
      style={{ marginLeft: `${indent}px` }} 
      className="flex items-center py-0.5 group"
    >
      <div className="flex items-center flex-1 min-w-0">
        {keyName && (
          <>
            <span className="font-medium text-gray-700 mr-1">"{keyName}":</span>
          </>
        )}
        <span className={`${colorClass} break-all`}>
          {formatValue(data)}
        </span>
        {type !== 'string' && (
          <span className="ml-2 text-xs text-gray-400 bg-gray-100 px-1 py-0.5 rounded">
            {type}
          </span>
        )}
      </div>
    </div>
  );
};

export const JsonView: React.FC<JsonViewProps> = React.memo(({ productData, onCopy }) => {
  const [copiedAction, setCopiedAction] = useState<string | null>(null);


  const handleCopyFormatted = async () => {
    const jsonString = JSON.stringify(productData, null, 2);
    await onCopy(jsonString, 'formatted-json');
    setCopiedAction('formatted');
    setTimeout(() => setCopiedAction(null), 2000);
  };

  const handleCopyMinified = async () => {
    const jsonString = JSON.stringify(productData);
    await onCopy(jsonString, 'minified-json');
    setCopiedAction('minified');
    setTimeout(() => setCopiedAction(null), 2000);
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-gray-900">Raw JSON Data</h3>
        <div className="flex space-x-2">
          <button
            onClick={handleCopyMinified}
            className="inline-flex items-center px-2 py-1 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {copiedAction === 'minified' ? (
              <CheckCircle className="h-3 w-3 mr-1 text-green-500" />
            ) : (
              <Copy className="h-3 w-3 mr-1" />
            )}
            Copy Minified
          </button>
          <button
            onClick={handleCopyFormatted}
            className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {copiedAction === 'formatted' ? (
              <CheckCircle className="h-3 w-3 mr-1 text-green-500" />
            ) : (
              <Copy className="h-3 w-3 mr-1" />
            )}
            Copy Formatted
          </button>
        </div>
      </div>
      
      <div className="border border-gray-200 rounded-lg bg-gray-50 p-4 max-h-96 overflow-auto">
        <div className="font-mono text-sm">
          <div className="text-gray-600 mb-2">{`{`}</div>
          <JsonNode data={productData} depth={1} />
          <div className="text-gray-600">{`}`}</div>
        </div>
      </div>

      <div className="text-xs text-gray-500 bg-gray-50 rounded p-2">
        <p><strong>Tip:</strong> Click the arrows to expand/collapse nested objects and arrays. 
        Use "Copy Formatted" for readable JSON or "Copy Minified" for compact JSON.</p>
      </div>
    </div>
  );
});