import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useAdmin } from '../contexts/AdminContext';
import {
  Menu,
  X,
  Home,
  ShoppingCart,
  Package,
  TrendingUp,
  BarChart3,
  CreditCard,
  LogOut,
  User,
  Settings
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth();
  const { isAdmin } = useAdmin();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: Home },
    { name: 'Product Lookup', href: '/products', icon: ShoppingCart },
    { name: 'FNSKU Converter', href: '/fnsku', icon: Package },
    { name: 'Price Monitoring', href: '/monitoring', icon: TrendingUp },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
    { name: 'Credits', href: '/credits', icon: CreditCard },
    // Only show admin link for admin users
    ...(isAdmin ? [{ name: 'Admin', href: '/admin', icon: Settings }] : []),
  ];

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Desktop Sidebar */}
      <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0">
        <div className="flex-1 flex flex-col min-h-0 bg-amazon-navy">
          <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
            <div className="flex items-center flex-shrink-0 px-4">
              <h1 className="text-xl font-semibold text-white">Amazon Intelligence</h1>
            </div>
            <nav className="mt-5 flex-1 px-2 space-y-1">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`${
                    isActive(item.href)
                      ? 'bg-gray-900 text-white'
                      : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                  } group flex items-center px-2 py-2 text-sm font-medium rounded-md`}
                >
                  <item.icon
                    className={`${
                      isActive(item.href) ? 'text-gray-300' : 'text-gray-400 group-hover:text-gray-300'
                    } mr-3 flex-shrink-0 h-6 w-6`}
                  />
                  {item.name}
                </Link>
              ))}
            </nav>
          </div>
          <div className="flex-shrink-0 flex bg-gray-700 p-4">
            <div className="flex items-center w-full">
              <div className="flex-shrink-0">
                <User className="h-8 w-8 text-gray-300" />
              </div>
              <div className="ml-3 flex-1">
                <p className="text-sm font-medium text-white">{user?.full_name}</p>
                <p className="text-xs font-medium text-gray-300">{user?.credit_balance || 0} credits</p>
              </div>
              <button
                onClick={handleLogout}
                className="ml-3 flex-shrink-0 text-gray-400 hover:text-white"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile header */}
      <div className="md:hidden">
        <div className="fixed top-0 left-0 right-0 z-10 flex items-center justify-between bg-gray-800 px-4 py-3">
          <h1 className="text-lg font-semibold text-white">Amazon Intelligence</h1>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="text-gray-400 hover:text-white"
          >
            {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="fixed inset-0 z-40 md:hidden">
            <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setMobileMenuOpen(false)} />
            <nav className="fixed top-0 left-0 bottom-0 flex flex-col w-5/6 max-w-sm py-6 px-6 bg-gray-800 overflow-y-auto">
              <div className="flex items-center mb-8">
                <h1 className="text-xl font-semibold text-white">Amazon Intelligence</h1>
              </div>
              <div className="flex-1">
                {navigation.map((item) => (
                  <Link
                    key={item.name}
                    to={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`${
                      isActive(item.href)
                        ? 'bg-gray-900 text-white'
                        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                    } group flex items-center px-2 py-2 text-base font-medium rounded-md mb-2`}
                  >
                    <item.icon
                      className={`${
                        isActive(item.href) ? 'text-gray-300' : 'text-gray-400 group-hover:text-gray-300'
                      } mr-4 flex-shrink-0 h-6 w-6`}
                    />
                    {item.name}
                  </Link>
                ))}
              </div>
              <div className="pt-6 mt-6 border-t border-gray-700">
                <div className="flex items-center px-2 mb-4">
                  <User className="h-8 w-8 text-gray-300" />
                  <div className="ml-3">
                    <p className="text-base font-medium text-white">{user?.full_name}</p>
                    <p className="text-sm font-medium text-gray-300">{user?.credit_balance || 0} credits</p>
                  </div>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center w-full px-2 py-2 text-base font-medium text-gray-300 hover:bg-gray-700 hover:text-white rounded-md"
                >
                  <LogOut className="mr-4 h-6 w-6" />
                  Sign out
                </button>
              </div>
            </nav>
          </div>
        )}
      </div>

      {/* Main content */}
      <div className="md:pl-64 flex flex-col flex-1">
        <main className="flex-1">
          <div className="py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}