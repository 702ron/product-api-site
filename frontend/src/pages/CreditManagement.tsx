import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api';
import { 
  CreditCard, 
  DollarSign, 
  Calendar, 
  TrendingUp,
  Package,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  Receipt
} from 'lucide-react';

interface CreditTransaction {
  id: string;
  amount: number;
  transaction_type: 'purchase' | 'usage' | 'refund';
  description: string;
  created_at: string;
  stripe_payment_intent_id?: string;
}

interface CreditStats {
  total_purchased: number;
  total_used: number;
  current_balance: number;
  transactions_count: number;
}

const CREDIT_PACKAGES = [
  {
    id: 'starter',
    name: 'Starter Pack',
    credits: 100,
    price: 9.99,
    popular: false,
    description: 'Perfect for trying out our platform',
  },
  {
    id: 'professional',
    name: 'Professional',
    credits: 500,
    price: 39.99,
    popular: true,
    description: 'Best value for regular users',
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    credits: 1000,
    price: 69.99,
    popular: false,
    description: 'For high-volume operations',
  },
  {
    id: 'bulk',
    name: 'Bulk Package',
    credits: 2500,
    price: 149.99,
    popular: false,
    description: 'Maximum value for enterprises',
  },
];

export function CreditManagement() {
  const { user, refreshUser } = useAuth();
  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
  const [stats, setStats] = useState<CreditStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [purchaseLoading, setPurchaseLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchCreditData();
  }, []);

  const fetchCreditData = async () => {
    try {
      const [transactionsResponse, statsResponse] = await Promise.all([
        api.get('/credits/transactions'),
        api.get('/credits/stats'),
      ]);

      setTransactions(transactionsResponse.data.transactions || []);
      setStats(statsResponse.data);
      await refreshUser();
    } catch (error) {
      console.error('Failed to fetch credit data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePurchase = async (packageId: string) => {
    setPurchaseLoading(packageId);
    
    try {
      const selectedPackage = CREDIT_PACKAGES.find(p => p.id === packageId);
      if (!selectedPackage) return;

      const response = await api.post('/payments/create-payment-intent', {
        amount: selectedPackage.price * 100, // Convert to cents
        currency: 'usd',
        credits: selectedPackage.credits,
        package_type: packageId,
      });

      // In a real implementation, you would integrate with Stripe Elements here
      // For now, we'll simulate a successful payment
      console.log('Payment intent created:', response.data);
      
      // Simulate successful payment (remove this in production)
      setTimeout(async () => {
        await fetchCreditData();
        setPurchaseLoading(null);
      }, 2000);

    } catch (error: any) {
      console.error('Purchase failed:', error);
      setPurchaseLoading(null);
      // Handle error (show notification, etc.)
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getTransactionIcon = (type: string) => {
    switch (type) {
      case 'purchase':
        return <DollarSign className="h-5 w-5 text-green-600" />;
      case 'usage':
        return <Package className="h-5 w-5 text-blue-600" />;
      case 'refund':
        return <Receipt className="h-5 w-5 text-orange-600" />;
      default:
        return <Clock className="h-5 w-5 text-gray-600" />;
    }
  };

  const getTransactionColor = (type: string) => {
    switch (type) {
      case 'purchase':
        return 'text-green-600';
      case 'usage':
        return 'text-red-600';
      case 'refund':
        return 'text-orange-600';
      default:
        return 'text-gray-600';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Credit Management</h1>
          <p className="mt-2 text-gray-600">
            Manage your credits, view transaction history, and purchase additional credits
          </p>
        </div>

        {/* Current Balance */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <CreditCard className="h-12 w-12 text-indigo-600 mr-4" />
              <div>
                <h2 className="text-3xl font-bold text-gray-900">
                  {user?.credit_balance || 0} Credits
                </h2>
                <p className="text-gray-600">Current balance</p>
              </div>
            </div>
            
            {stats && (
              <div className="text-right">
                <p className="text-sm text-gray-600">Total purchased</p>
                <p className="text-xl font-semibold text-gray-900">{stats.total_purchased}</p>
              </div>
            )}
          </div>
        </div>

        {/* Stats Grid */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center">
                <TrendingUp className="h-6 w-6 text-green-600 mr-3" />
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Purchased</p>
                  <p className="text-2xl font-semibold text-gray-900">{stats.total_purchased}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center">
                <Package className="h-6 w-6 text-blue-600 mr-3" />
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Used</p>
                  <p className="text-2xl font-semibold text-gray-900">{stats.total_used}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center">
                <Receipt className="h-6 w-6 text-purple-600 mr-3" />
                <div>
                  <p className="text-sm font-medium text-gray-600">Transactions</p>
                  <p className="text-2xl font-semibold text-gray-900">{stats.transactions_count}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Credit Packages */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Purchase Credits</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {CREDIT_PACKAGES.map((pkg) => (
              <div
                key={pkg.id}
                className={`relative border-2 rounded-lg p-6 ${
                  pkg.popular
                    ? 'border-indigo-500 bg-indigo-50'
                    : 'border-gray-200 bg-white'
                }`}
              >
                {pkg.popular && (
                  <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                    <span className="bg-indigo-500 text-white px-3 py-1 rounded-full text-xs font-medium">
                      Most Popular
                    </span>
                  </div>
                )}

                <div className="text-center">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">{pkg.name}</h3>
                  <div className="mb-4">
                    <span className="text-3xl font-bold text-gray-900">${pkg.price}</span>
                    <p className="text-sm text-gray-600 mt-1">{pkg.credits} credits</p>
                  </div>
                  <p className="text-sm text-gray-600 mb-6">{pkg.description}</p>
                  
                  <button
                    onClick={() => handlePurchase(pkg.id)}
                    disabled={purchaseLoading === pkg.id}
                    className={`w-full px-4 py-2 rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                      pkg.popular
                        ? 'bg-indigo-600 text-white hover:bg-indigo-700 focus:ring-indigo-500'
                        : 'bg-gray-900 text-white hover:bg-gray-800 focus:ring-gray-500'
                    } disabled:opacity-50`}
                  >
                    {purchaseLoading === pkg.id ? (
                      <Loader2 className="h-4 w-4 animate-spin mx-auto" />
                    ) : (
                      'Purchase'
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Transaction History */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Transaction History</h2>
          </div>

          <div className="divide-y divide-gray-200">
            {transactions.length === 0 ? (
              <div className="px-6 py-8 text-center">
                <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">No transactions yet</p>
                <p className="text-sm text-gray-500 mt-1">
                  Your credit purchases and usage will appear here
                </p>
              </div>
            ) : (
              transactions.map((transaction) => (
                <div key={transaction.id} className="px-6 py-4 flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="mr-4">
                      {getTransactionIcon(transaction.transaction_type)}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {transaction.description}
                      </p>
                      <p className="text-sm text-gray-500">
                        {formatDate(transaction.created_at)}
                      </p>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <p className={`text-sm font-medium ${getTransactionColor(transaction.transaction_type)}`}>
                      {transaction.transaction_type === 'usage' ? '-' : '+'}
                      {Math.abs(transaction.amount)} credits
                    </p>
                    {transaction.stripe_payment_intent_id && (
                      <p className="text-xs text-gray-500">
                        ID: {transaction.stripe_payment_intent_id.substring(0, 12)}...
                      </p>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}