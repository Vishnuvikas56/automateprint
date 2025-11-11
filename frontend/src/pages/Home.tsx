import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { X, Loader, Printer, CheckCircle, Zap, Clock } from 'lucide-react';

const Home: React.FC = () => {
  const { isAuthenticated, signin, signup } = useAuth();
  const navigate = useNavigate();
  
  const [showSignIn, setShowSignIn] = useState(false);
  const [showSignUp, setShowSignUp] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Sign In Form State
  const [signInData, setSignInData] = useState({
    username: '',
    password: '',
  });

  // Sign Up Form State
  const [signUpData, setSignUpData] = useState({
    email: '',
    username: '',
    password: '',
    full_name: '',
  });

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await signin(signInData.username, signInData.password);
      setShowSignIn(false);
      navigate('/dashboard');
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
      await signup(
        signUpData.email,
        signUpData.username,
        signUpData.password,
        signUpData.full_name
      );
      setShowSignUp(false);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center">
          <h1 className="text-5xl font-extrabold text-gray-900 mb-6">
            Smart Print Automation System
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            AI-powered print scheduling for campus print shops. Submit orders online,
            track in real-time, and get prints delivered faster than ever.
          </p>
          
          <div className="flex justify-center space-x-4">
            <button
              onClick={() => setShowSignIn(true)}
              className="px-8 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition"
            >
              Sign In
            </button>
            <button
              onClick={() => setShowSignUp(true)}
              className="px-8 py-3 bg-white text-blue-600 border-2 border-blue-600 rounded-lg font-semibold hover:bg-blue-50 transition"
            >
              Sign Up
            </button>
          </div>
        </div>

        {/* Features */}
        <div className="mt-20 grid md:grid-cols-3 gap-8">
          <div className="bg-white p-6 rounded-xl shadow-lg">
            <Zap className="h-12 w-12 text-blue-600 mb-4" />
            <h3 className="text-xl font-bold mb-2">Smart Scheduling</h3>
            <p className="text-gray-600">
              AI algorithm automatically assigns your print jobs to the fastest available printer
            </p>
          </div>
          
          <div className="bg-white p-6 rounded-xl shadow-lg">
            <Clock className="h-12 w-12 text-blue-600 mb-4" />
            <h3 className="text-xl font-bold mb-2">Real-Time Tracking</h3>
            <p className="text-gray-600">
              Monitor your print jobs live with accurate time estimates and progress updates
            </p>
          </div>
          
          <div className="bg-white p-6 rounded-xl shadow-lg">
            <CheckCircle className="h-12 w-12 text-blue-600 mb-4" />
            <h3 className="text-xl font-bold mb-2">Multiple Locations</h3>
            <p className="text-gray-600">
              Access print shops across campus with 6 printers supporting both BW and color
            </p>
          </div>
        </div>
      </div>

      {/* Sign In Modal */}
      {showSignIn && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4 relative">
            <button
              onClick={() => setShowSignIn(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
            >
              <X className="h-6 w-6" />
            </button>

            <h2 className="text-2xl font-bold mb-6">Sign In</h2>

            {error && (
              <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-md">
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
                className="w-full py-3 bg-blue-600 text-white rounded-md font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center"
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
                className="text-blue-600 hover:underline"
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
          <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4 relative">
            <button
              onClick={() => setShowSignUp(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
            >
              <X className="h-6 w-6" />
            </button>

            <h2 className="text-2xl font-bold mb-6">Sign Up</h2>

            {error && (
              <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-md">
                {error}
              </div>
            )}

            <form onSubmit={handleSignUp}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email
                </label>
                <input
                  type="email"
                  value={signUpData.email}
                  onChange={(e) => setSignUpData({ ...signUpData, email: e.target.value })}
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
                  value={signUpData.username}
                  onChange={(e) => setSignUpData({ ...signUpData, username: e.target.value })}
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
                  value={signUpData.full_name}
                  onChange={(e) => setSignUpData({ ...signUpData, full_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Password
                </label>
                <input
                  type="password"
                  value={signUpData.password}
                  onChange={(e) => setSignUpData({ ...signUpData, password: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-blue-600 text-white rounded-md font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center"
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
                className="text-blue-600 hover:underline"
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