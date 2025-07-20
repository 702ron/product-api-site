//
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { api } from '../lib/api';

const trialSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email address'),
  company: z.string().min(1, 'Company is required'),
  useCase: z.string().min(1, 'Please select a use case'),
});

type TrialFormData = z.infer<typeof trialSchema>;

interface TrialSignupFormProps {
  onSuccess?: () => void;
  onError?: (error: string) => void;
}

export const TrialSignupForm: React.FC<TrialSignupFormProps> = ({ 
  onSuccess, 
  onError 
}) => {
  const navigate = useNavigate();
  
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<TrialFormData>({
    resolver: zodResolver(trialSchema),
  });

  const onSubmit = async (data: TrialFormData) => {
    try {
      await api.post('/auth/trial-signup', data);
      
      if (onSuccess) {
        onSuccess();
      } else {
        // Default behavior: redirect to dashboard
        navigate('/dashboard');
      }
    } catch (error: unknown) {
      const errorMessage = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to start trial. Please try again.';
      
      if (onError) {
        onError(errorMessage);
      } else {
        // Default error handling - could be enhanced with toast notifications
        console.error('Trial signup error:', errorMessage);
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <input
          {...register('name')}
          placeholder="Full Name"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
        />
        {errors.name && (
          <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
        )}
      </div>
      
      <div>
        <input
          {...register('email')}
          type="email"
          placeholder="Business Email"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
        />
        {errors.email && (
          <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
        )}
      </div>

      <div>
        <input
          {...register('company')}
          placeholder="Company Name"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
        />
        {errors.company && (
          <p className="mt-1 text-sm text-red-600">{errors.company.message}</p>
        )}
      </div>

      <div>
        <select
          {...register('useCase')}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
        >
          <option value="">Select your primary use case</option>
          <option value="product-research">Product Research</option>
          <option value="price-monitoring">Price Monitoring</option>
          <option value="inventory-management">Inventory Management</option>
          <option value="competitor-analysis">Competitor Analysis</option>
          <option value="other">Other</option>
        </select>
        {errors.useCase && (
          <p className="mt-1 text-sm text-red-600">{errors.useCase.message}</p>
        )}
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full py-3 px-6 border border-transparent text-lg font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isSubmitting ? (
          <span className="flex items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />
            Starting Trial...
          </span>
        ) : (
          'Start Free Trial'
        )}
      </button>
      
      <p className="text-sm text-gray-500 text-center">
        No credit card required. 1000 free API calls included.
      </p>
    </form>
  );
};