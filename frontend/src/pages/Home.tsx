import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { X, Loader, Users, Shield } from 'lucide-react';

const Home: React.FC = () => {
  const { isAuthenticated, signin, signup, userRole } = useAuth();
  const navigate = useNavigate();
  
  const [selectedRole, setSelectedRole] = useState<'customer' | 'supervisor' | null>(null);
  const [showSignIn, setShowSignIn] = useState(false);
  const [showSignUp, setShowSignUp] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  // Sign In Form State
  const [signInData, setSignInData] = useState({
    username: '',
    password: '',
  });

  // Customer Sign Up Form State
  const [customerSignUpData, setCustomerSignUpData] = useState({
    email: '',
    username: '',
    password: '',
    full_name: '',
  });

  // Supervisor Sign Up Form State
  const [supervisorSignUpData, setSupervisorSignUpData] = useState({
    email: '',
    username: '',
    password: '',
    store_id: '',
    contact_number: '',
    address: '',
  });

  React.useEffect(() => {
    if (isAuthenticated) {
      // Redirect based on user role
      if (userRole === 'supervisor') {
        navigate('/supervisor/dashboard');
      } else {
        navigate('/dashboard');
      }
    }
  }, [isAuthenticated, userRole, navigate]);

  const handleRoleClick = (role: 'customer' | 'supervisor') => {
    setSelectedRole(role);
    setShowSignIn(true);
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
  
    try {
      await signin(signInData.username, signInData.password, selectedRole!);
      setShowSignIn(false);
      // Navigation is now handled by the useEffect above
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
  
    try {
      if (selectedRole === 'supervisor') {
        await signup(
          supervisorSignUpData.email,
          supervisorSignUpData.username,
          supervisorSignUpData.password,
          'supervisor',
          {
            store_id: supervisorSignUpData.store_id,
            contact_number: supervisorSignUpData.contact_number,
            address: supervisorSignUpData.address,
          }
        );
      } else {
        await signup(
          customerSignUpData.email,
          customerSignUpData.username,
          customerSignUpData.password,
          'customer',
          {
            full_name: customerSignUpData.full_name,
          }
        );
      }
      setShowSignUp(false);
      // Navigation is now handled by the useEffect above
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const resetModals = () => {
    setShowSignIn(false);
    setShowSignUp(false);
    setSelectedRole(null);
    setError('');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="max-w-4xl w-full">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-extrabold text-gray-900 mb-4">
            Smart Print Automation System
          </h1>
        </div>

        {/* Role Selection Buttons */}
        <div className="grid md:grid-cols-2 gap-6 max-w-2xl mx-auto">
          <button
            onClick={() => handleRoleClick('customer')}
            className="p-8 bg-white rounded-xl shadow-lg hover:shadow-xl transition border-2 border-transparent hover:border-blue-500 group"
          >
            <div className="flex flex-col items-center">
              <div className="bg-blue-100 p-4 rounded-full mb-4 group-hover:bg-blue-200 transition">
                <Users className="h-12 w-12 text-blue-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Customer</h2>
              <p className="text-gray-600">Submit and track print orders</p>
            </div>
          </button>

          <button
            onClick={() => handleRoleClick('supervisor')}
            className="p-8 bg-white rounded-xl shadow-lg hover:shadow-xl transition border-2 border-transparent hover:border-indigo-500 group"
          >
            <div className="flex flex-col items-center">
              <div className="bg-indigo-100 p-4 rounded-full mb-4 group-hover:bg-indigo-200 transition">
                <Shield className="h-12 w-12 text-indigo-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Supervisor</h2>
              <p className="text-gray-600">Manage orders and printers</p>
            </div>
          </button>
        </div>
      </div>

      {/* Sign In Modal */}
      {showSignIn && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4 relative">
            <button
              onClick={resetModals}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
            >
              <X className="h-6 w-6" />
            </button>

            <div className="flex items-center justify-center mb-6">
              {selectedRole === 'supervisor' ? (
                <div className="bg-indigo-100 p-3 rounded-lg">
                  <Shield className="h-8 w-8 text-indigo-600" />
                </div>
              ) : (
                <div className="bg-blue-100 p-3 rounded-lg">
                  <Users className="h-8 w-8 text-blue-600" />
                </div>
              )}
            </div>

            <h2 className="text-2xl font-bold mb-2 text-center">
              {selectedRole === 'supervisor' ? 'Supervisor' : 'Customer'} Sign In
            </h2>

            {error && (
              <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-md text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleSignIn}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={signInData.username}
                  onChange={(e) => setSignInData({ ...signInData, username: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Password
                </label>
                <input
                  type="password"
                  value={signInData.password}
                  onChange={(e) => setSignInData({ ...signInData, password: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className={`w-full py-3 ${selectedRole === 'supervisor' ? 'bg-indigo-600 hover:bg-indigo-700' : 'bg-blue-600 hover:bg-blue-700'} text-white rounded-md font-semibold disabled:opacity-50 flex items-center justify-center transition`}
              >
                {loading ? (
                  <>
                    <Loader className="animate-spin h-5 w-5 mr-2" />
                    Signing in...
                  </>
                ) : (
                  'Sign In'
                )}
              </button>
            </form>

            <p className="mt-4 text-center text-sm text-gray-600">
              Don't have an account?{' '}
              <button
                onClick={() => {
                  setShowSignIn(false);
                  setShowSignUp(true);
                }}
                className={`${selectedRole === 'supervisor' ? 'text-indigo-600' : 'text-blue-600'} hover:underline font-medium`}
              >
                Sign Up
              </button>
            </p>
          </div>
        </div>
      )}

      {/* Sign Up Modal */}
      {showSignUp && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4 relative max-h-[90vh] overflow-y-auto">
            <button
              onClick={resetModals}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
            >
              <X className="h-6 w-6" />
            </button>

            <div className="flex items-center justify-center mb-6">
              {selectedRole === 'supervisor' ? (
                <div className="bg-indigo-100 p-3 rounded-lg">
                  <Shield className="h-8 w-8 text-indigo-600" />
                </div>
              ) : (
                <div className="bg-blue-100 p-3 rounded-lg">
                  <Users className="h-8 w-8 text-blue-600" />
                </div>
              )}
            </div>

            <h2 className="text-2xl font-bold mb-2 text-center">
              {selectedRole === 'supervisor' ? 'Supervisor' : 'Customer'} Sign Up
            </h2>

            {error && (
              <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-md text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleSignUp}>
              {selectedRole === 'customer' ? (
                <>
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Email
                    </label>
                    <input
                      type="email"
                      value={customerSignUpData.email}
                      onChange={(e) => setCustomerSignUpData({ ...customerSignUpData, email: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>

                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Username
                    </label>
                    <input
                      type="text"
                      value={customerSignUpData.username}
                      onChange={(e) => setCustomerSignUpData({ ...customerSignUpData, username: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>

                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Full Name
                    </label>
                    <input
                      type="text"
                      value={customerSignUpData.full_name}
                      onChange={(e) => setCustomerSignUpData({ ...customerSignUpData, full_name: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Password
                    </label>
                    <input
                      type="password"
                      value={customerSignUpData.password}
                      onChange={(e) => setCustomerSignUpData({ ...customerSignUpData, password: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                </>
              ) : (
                <>
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Email
                    </label>
                    <input
                      type="email"
                      value={supervisorSignUpData.email}
                      onChange={(e) => setSupervisorSignUpData({ ...supervisorSignUpData, email: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      required
                    />
                  </div>

                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Username
                    </label>
                    <input
                      type="text"
                      value={supervisorSignUpData.username}
                      onChange={(e) => setSupervisorSignUpData({ ...supervisorSignUpData, username: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      required
                    />
                  </div>

                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Password
                    </label>
                    <input
                      type="password"
                      value={supervisorSignUpData.password}
                      onChange={(e) => setSupervisorSignUpData({ ...supervisorSignUpData, password: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      required
                    />
                  </div>

                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Store ID
                    </label>
                    <input
                      type="text"
                      value={supervisorSignUpData.store_id}
                      onChange={(e) => setSupervisorSignUpData({ ...supervisorSignUpData, store_id: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      required
                    />
                  </div>

                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Contact Number
                    </label>
                    <input
                      type="tel"
                      value={supervisorSignUpData.contact_number}
                      onChange={(e) => setSupervisorSignUpData({ ...supervisorSignUpData, contact_number: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>

                  <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Address
                    </label>
                    <textarea
                      value={supervisorSignUpData.address}
                      onChange={(e) => setSupervisorSignUpData({ ...supervisorSignUpData, address: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      rows={2}
                    />
                  </div>
                </>
              )}

              <button
                type="submit"
                disabled={loading}
                className={`w-full py-3 ${selectedRole === 'supervisor' ? 'bg-indigo-600 hover:bg-indigo-700' : 'bg-blue-600 hover:bg-blue-700'} text-white rounded-md font-semibold disabled:opacity-50 flex items-center justify-center transition`}
              >
                {loading ? (
                  <>
                    <Loader className="animate-spin h-5 w-5 mr-2" />
                    Creating account...
                  </>
                ) : (
                  'Sign Up'
                )}
              </button>
            </form>

            <p className="mt-4 text-center text-sm text-gray-600">
              Already have an account?{' '}
              <button
                onClick={() => {
                  setShowSignUp(false);
                  setShowSignIn(true);
                }}
                className={`${selectedRole === 'supervisor' ? 'text-indigo-600' : 'text-blue-600'} hover:underline font-medium`}
              >
                Sign In
              </button>
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default Home;