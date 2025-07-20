import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  className?: string;
}

export const LoadingSpinner = ({ 
  size = 'md', 
  text = 'Loading...', 
  className = '' 
}: LoadingSpinnerProps) => {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8', 
    lg: 'h-12 w-12'
  };

  const textSizeClasses = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg'
  };

  return (
    <div className={`flex flex-col items-center justify-center space-y-2 ${className}`} role="status" aria-live="polite">
      <Loader2 className={`animate-spin text-indigo-600 ${sizeClasses[size]}`} aria-hidden="true" />
      {text && (
        <span className={`text-gray-600 ${textSizeClasses[size]}`}>
          {text}
        </span>
      )}
      <span className="sr-only">Loading content, please wait...</span>
    </div>
  );
};

interface PageLoadingProps {
  text?: string;
}

export const PageLoading = ({ text = 'Loading page...' }: PageLoadingProps) => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <LoadingSpinner size="lg" text={text} />
  </div>
);

interface InlineLoadingProps {
  text?: string;
  className?: string;
}

export const InlineLoading = ({ text = 'Loading...', className = '' }: InlineLoadingProps) => (
  <LoadingSpinner size="sm" text={text} className={`py-4 ${className}`} />
);