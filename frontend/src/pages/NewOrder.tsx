import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { FileText, Loader, CheckCircle, XCircle } from 'lucide-react';
import PaymentModal from '../components/PaymentModal';

const API_BASE_URL = 'http://localhost:8000';

interface Store {
  store_id: string;
  store_name: string;
  pricing_info: {
    bw_per_page: number;
    color_per_page: number;
  };
}

export const NewOrder: React.FC = () => {
  const navigate = useNavigate();
  const [stores, setStores] = useState<Store[]>([]);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  // Payment states
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentDetails, setPaymentDetails] = useState<any>(null);
  const [paymentError, setPaymentError] = useState('');
  const [showPaymentErrorModal, setShowPaymentErrorModal] = useState(false);

  const [formData, setFormData] = useState({
    store_id: 'STORE001',
    pages: 1,
    copies: 1,
    color_mode: 'bw',
    priority: 2,
  });

  const [estimatedPrice, setEstimatedPrice] = useState(0);

  useEffect(() => {
    fetchStores();
  }, []);

  useEffect(() => {
    calculatePrice();
  }, [formData.pages, formData.copies, formData.color_mode, formData.store_id, stores]);

  const fetchStores = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/stores`);
      setStores(response.data.stores);
    } catch (error) {
      console.error('Failed to fetch stores:', error);
    }
  };

  const calculatePrice = () => {
    const store = stores.find((s) => s.store_id === formData.store_id);
    if (!store) return;

    const pricePerPage =
      formData.color_mode === 'color'
        ? store.pricing_info.color_per_page
        : store.pricing_info.bw_per_page;

    const total = formData.pages * formData.copies * pricePerPage;
    setEstimatedPrice(total);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Step 1: Create order and payment
      const response = await axios.post(`${API_BASE_URL}/orders/create-payment`, formData);
      
      setPaymentDetails(response.data);
      setShowPaymentModal(true);
      
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create order');
    } finally {
      setLoading(false);
    }
  };

  const handlePaymentSuccess = async (paymentData: any) => {
    setShowPaymentModal(false);
    setLoading(true);

    try {
      // Step 2: Verify payment
      const response = await axios.post(`${API_BASE_URL}/orders/verify-payment`, {
        razorpay_order_id: paymentData.razorpay_order_id,
        razorpay_payment_id: paymentData.razorpay_payment_id,
        razorpay_signature: paymentData.razorpay_signature,
      });

      if (response.data.success) {
        setSuccess(true);
        setTimeout(() => {
          navigate('/my-orders');
        }, 2000);
      }
    } catch (err: any) {
      setPaymentError(err.response?.data?.detail || 'Payment verification failed');
      setShowPaymentErrorModal(true);
    } finally {
      setLoading(false);
    }
  };

  const handlePaymentFailure = (error: any) => {
    setShowPaymentModal(false);
    setPaymentError(error.error || 'Payment failed');
    setShowPaymentErrorModal(true);
  };

  if (success) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-20 text-center">
        <CheckCircle className="h-16 w-16 text-green-600 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Order Placed Successfully!
        </h2>
        <p className="text-gray-600">Your print job is being processed...</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Create Print Order</h1>
        <p className="text-gray-600 mt-2">Fill in the details for your print job</p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-100 text-red-700 rounded-lg">{error}</div>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Store Location
            </label>
            <select
              value={formData.store_id}
              onChange={(e) => setFormData({ ...formData, store_id: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              {stores.map((store) => (
                <option key={store.store_id} value={store.store_id}>
                  {store.store_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Number of Pages
            </label>
            <input
              type="number"
              value={formData.pages}
              onChange={(e) =>
                setFormData({ ...formData, pages: parseInt(e.target.value) })
              }
              min="1"
              max="1000"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Number of Copies
            </label>
            <input
              type="number"
              value={formData.copies}
              onChange={(e) =>
                setFormData({ ...formData, copies: parseInt(e.target.value) })
              }
              min="1"
              max="100"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Print Mode
            </label>
            <select
              value={formData.color_mode}
              onChange={(e) => setFormData({ ...formData, color_mode: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="bw">Black & White</option>
              <option value="color">Color</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Priority
            </label>
            <select
              value={formData.priority}
              onChange={(e) =>
                setFormData({ ...formData, priority: parseInt(e.target.value) })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="1">Urgent</option>
              <option value="2">Normal</option>
              <option value="3">Low</option>
            </select>
          </div>
        </div>

        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <div className="flex justify-between items-center">
            <span className="text-lg font-semibold text-gray-700">Total Amount:</span>
            <span className="text-2xl font-bold text-blue-600">
              ₹{estimatedPrice.toFixed(2)}
            </span>
          </div>
          <p className="text-sm text-gray-600 mt-2">
            {formData.pages} pages × {formData.copies} copies × ₹
            {formData.color_mode === 'color' ? '10' : '2'}/page
          </p>
        </div>

        <div className="mt-6 flex space-x-4">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 py-3 bg-blue-600 text-white rounded-md font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center"
          >
            {loading ? (
              <>
                <Loader className="animate-spin h-5 w-5 mr-2" />
                Processing...
              </>
            ) : (
              <>
                <FileText className="h-5 w-5 mr-2" />
                Proceed to Payment
              </>
            )}
          </button>

          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="px-6 py-3 bg-gray-200 text-gray-700 rounded-md font-semibold hover:bg-gray-300"
          >
            Cancel
          </button>
        </div>
      </form>

      {/* Payment Modal */}
      <PaymentModal
        isOpen={showPaymentModal}
        onClose={() => setShowPaymentModal(false)}
        orderDetails={paymentDetails}
        onPaymentSuccess={handlePaymentSuccess}
        onPaymentFailure={handlePaymentFailure}
      />

      {/* Payment Error Modal */}
      {showPaymentErrorModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4">
            <div className="text-center">
              <XCircle className="h-16 w-16 text-red-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Payment Failed
              </h2>
              <p className="text-gray-600 mb-6">{paymentError}</p>
              <button
                onClick={() => {
                  setShowPaymentErrorModal(false);
                  setPaymentError('');
                }}
                className="w-full py-3 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};