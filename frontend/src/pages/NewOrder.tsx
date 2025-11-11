import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { FileText, Upload, Loader, CheckCircle } from 'lucide-react';

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

  const [formData, setFormData] = useState({
    store_id: 'STORE001',
    pages: 1,
    copies: 1,
    color_mode: 'bw',
    priority: 2,
    document_name: ''
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
    const store = stores.find(s => s.store_id === formData.store_id);
    if (!store) return;

    const pricePerPage = formData.color_mode === 'color' 
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
      const response = await axios.post(`${API_BASE_URL}/orders/submit`, formData);
      setSuccess(true);
      
      setTimeout(() => {
        navigate('/my-orders');
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit order');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-20 text-center">
        <CheckCircle className="h-16 w-16 text-green-600 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Order Submitted Successfully!</h2>
        <p className="text-gray-600">Redirecting to your orders...</p>
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
        <div className="mb-6 p-4 bg-red-100 text-red-700 rounded-lg">
          {error}
        </div>
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
              Document Name (Optional)
            </label>
            <input
              type="text"
              value={formData.document_name}
              onChange={(e) => setFormData({ ...formData, document_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="My Document"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Number of Pages
            </label>
            <input
              type="number"
              value={formData.pages}
              onChange={(e) => setFormData({ ...formData, pages: parseInt(e.target.value) })}
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
              onChange={(e) => setFormData({ ...formData, copies: parseInt(e.target.value) })}
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
              onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
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
            <span className="text-lg font-semibold text-gray-700">Estimated Price:</span>
            <span className="text-2xl font-bold text-blue-600">₹{estimatedPrice.toFixed(2)}</span>
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
                Submitting...
              </>
            ) : (
              <>
                <FileText className="h-5 w-5 mr-2" />
                Submit Order
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
    </div>
  );
};