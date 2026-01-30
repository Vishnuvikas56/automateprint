import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Printer, LogOut, User, FileText, Home, Store } from 'lucide-react';

const Navbar: React.FC = () => {
  const { isAuthenticated, user, signout } = useAuth();

  return (
    <nav className="bg-white shadow-lg border-b fixed top-0 left-0 right-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="flex items-center space-x-2">
              <Printer className="h-8 w-8 text-blue-600" />
              <span className="text-xl font-bold text-gray-900">SmartPrint</span>
            </Link>
            
            {isAuthenticated && (
              <div className="ml-10 flex items-baseline space-x-4">
                <Link
                  to="/dashboard"
                  className="flex items-center space-x-1 px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-blue-600 hover:bg-gray-50"
                >
                  <Home className="h-4 w-4" />
                  <span>Dashboard</span>
                </Link>
                <Link
                  to="/new-order"
                  className="flex items-center space-x-1 px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-blue-600 hover:bg-gray-50"
                >
                  <FileText className="h-4 w-4" />
                  <span>New Order</span>
                </Link>
                <Link
                  to="/my-orders"
                  className="flex items-center space-x-1 px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-blue-600 hover:bg-gray-50"
                >
                  <FileText className="h-4 w-4" />
                  <span>My Orders</span>
                </Link>
                <Link
                  to="/stores"
                  className="flex items-center space-x-1 px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-blue-600 hover:bg-gray-50"
                >
                  <Store className="h-4 w-4" />
                  <span>Stores</span>
                </Link>
              </div>
            )}
          </div>

          <div className="flex items-center">
            {isAuthenticated ? (
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2 text-sm text-gray-700">
                  <User className="h-5 w-5" />
                  <span>{user?.username}</span>
                  {user?.balance !== undefined && (
                    <span className="ml-2 px-2 py-1 bg-green-100 text-green-800 rounded-md font-medium">
                      ₹{user.balance.toFixed(2)}
                    </span>
                  )}
                </div>
                <button
                  onClick={signout}
                  className="flex items-center space-x-1 px-4 py-2 rounded-md text-sm font-medium text-white bg-red-600 hover:bg-red-700"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Logout</span>
                </button>
              </div>
            ) : (
              <div className="text-sm text-gray-500">
                Welcome! Please sign in to continue
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;