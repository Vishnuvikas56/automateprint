import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { FileText, Loader, CheckCircle, XCircle, Upload, X, Plus } from 'lucide-react';
import PaymentModal from '../components/PaymentModal';

const API_BASE_URL = 'http://localhost:8000';

interface Store {
  store_id: string;
  store_name: string;
  pricing_info: { bw_per_page: number; color_per_page: number };
}

interface UploadedFile {
  filename: string;
  file_url: string;
  size_mb: number;
}

export const BulkOrder: React.FC = () => {
  const navigate = useNavigate();
  const [stores, setStores] = useState<Store[]>([]);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [uploadingFiles, setUploadingFiles] = useState(false);
  const [uploadError, setUploadError] = useState('');

  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentDetails, setPaymentDetails] = useState<any>(null);
  const [paymentError, setPaymentError] = useState('');
  const [showPaymentErrorModal, setShowPaymentErrorModal] = useState(false);

  const [formData, setFormData] = useState({
    store_id: 'STORE001',
    pages: 10,
    copies: 1,
    color_mode: 'bw',
    priority: 2,
  });

  const [totalPrice, setTotalPrice] = useState(0);

  useEffect(() => {
    fetchStores();
  }, []);

  useEffect(() => {
    calculateTotalPrice();
  }, [formData, uploadedFiles, stores]);

  const fetchStores = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/stores`);
      setStores(response.data.stores);
    } catch (error) {
      console.error('Failed to fetch stores:', error);
    }
  };

  const calculateTotalPrice = () => {
    if (uploadedFiles.length === 0) return;

    const store = stores.find((s) => s.store_id === formData.store_id);
    if (!store) return;

    const pricePerPage =
      formData.color_mode === 'color'
        ? store.pricing_info.color_per_page
        : store.pricing_info.bw_per_page;

    const total = formData.pages * formData.copies * uploadedFiles.length * pricePerPage;
    setTotalPrice(total);
  };

  const handleFilesSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);

    if (files.length === 0) return;
    if (files.length > 10) {
      setUploadError('Maximum 10 files allowed');
      return;
    }

    // Validate all files first
    for (const file of files) {
      if (file.type !== 'application/pdf') {
        setUploadError(`${file.name} is not a PDF file`);
        return;
      }
      const fileSizeMB = file.size / (1024 * 1024);
      if (fileSizeMB > 25) {
        setUploadError(`${file.name} is too large (${fileSizeMB.toFixed(2)}MB, max 25MB)`);
        return;
      }
    }

    setUploadingFiles(true);
    setUploadError('');

    try {
      const formData = new FormData();
      files.forEach((file) => formData.append('files', file));

      const response = await axios.post(`${API_BASE_URL}/orders/upload-bulk-files`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setUploadedFiles(response.data.files);
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Bulk upload failed');
    } finally {
      setUploadingFiles(false);
    }
  };

  const handleRemoveFile = (index: number) => {
    setUploadedFiles(uploadedFiles.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (uploadedFiles.length === 0) {
      setError('Please upload at least one PDF file');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Create multiple orders, one per file
      const orderPromises = uploadedFiles.map((file) =>
        axios.post(`${API_BASE_URL}/orders/create-payment`, {
          ...formData,
          file_url: file.file_url,
        })
      );

      const responses = await Promise.all(orderPromises);

      // For simplicity, use first order's payment details
      // In production, consider bulk payment or single combined payment
      setPaymentDetails(responses[0].data);
      setShowPaymentModal(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create orders');
    } finally {
      setLoading(false);
    }
  };

  const handlePaymentSuccess = async (paymentData: any) => {
    setShowPaymentModal(false);
    setLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/orders/verify-payment`, {
        razorpay_order_id: paymentData.razorpay_order_id,
        razorpay_payment_id: paymentData.razorpay_payment_id,
        razorpay_signature: paymentData.razorpay_signature,
      });

      if (response.data.success) {
        setSuccess(true);
        setTimeout(() => navigate('/my-orders'), 2000);
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
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Bulk Orders Placed Successfully!</h2>
        <p className="text-gray-600">{uploadedFiles.length} print jobs are being processed...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Bulk Print Order</h1>
        <p className="text-gray-600 mt-2">Upload multiple PDFs (max 10 files, 25MB each)</p>
      </div>

      {error && <div className="mb-6 p-4 bg-red-100 text-red-700 rounded-lg">{error}</div>}

      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6">
        {/* File Upload Section */}
        <div className="mb-6 p-4 border-2 border-dashed border-gray-300 rounded-lg">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Upload PDFs (Max 10 files, 25MB each)
          </label>

          {uploadedFiles.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <label className="cursor-pointer flex flex-col items-center space-y-2">
                <Plus className="h-12 w-12 text-gray-400" />
                <span className="text-sm text-gray-600">Click to select multiple PDFs</span>
                <input
                  type="file"
                  accept="application/pdf"
                  multiple
                  onChange={handleFilesSelect}
                  className="hidden"
                  disabled={uploadingFiles}
                />
              </label>
            </div>
          ) : (
            <div className="space-y-2">
              {uploadedFiles.map((file, index) => (
                <div key={index} className="flex items-center justify-between bg-green-50 p-3 rounded">
                  <div className="flex items-center space-x-3">
                    <FileText className="h-6 w-6 text-green-600" />
                    <div>
                      <p className="font-medium text-gray-900">{file.filename}</p>
                      <p className="text-xs text-gray-600">{file.size_mb} MB</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveFile(index)}
                    className="text-red-600 hover:text-red-800"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              ))}
              <label className="cursor-pointer block text-center py-2 text-blue-600 hover:text-blue-800">
                <Plus className="h-5 w-5 inline mr-2" />
                Add more files
                <input
                  type="file"
                  accept="application/pdf"
                  multiple
                  onChange={handleFilesSelect}
                  className="hidden"
                  disabled={uploadingFiles}
                />
              </label>
            </div>
          )}

          {uploadingFiles && (
            <div className="mt-2 text-center">
              <Loader className="animate-spin h-6 w-6 mx-auto text-blue-600" />
              <p className="text-sm text-gray-600 mt-2">Uploading files...</p>
            </div>
          )}

          {uploadError && (
            <div className="mt-2 p-2 bg-red-100 text-red-700 text-sm rounded">{uploadError}</div>
          )}
        </div>

        {/* Form Fields */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Store Location</label>
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
              Pages per Document
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
            <label className="block text-sm font-medium text-gray-700 mb-2">Copies per Document</label>
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
            <label className="block text-sm font-medium text-gray-700 mb-2">Print Mode</label>
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
        </div>

        {uploadedFiles.length > 0 && (
          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <div className="flex justify-between items-center">
              <span className="text-lg font-semibold text-gray-700">Total Amount:</span>
              <span className="text-2xl font-bold text-blue-600">₹{totalPrice.toFixed(2)}</span>
            </div>
            <p className="text-sm text-gray-600 mt-2">
              {uploadedFiles.length} documents × {formData.pages} pages × {formData.copies} copies × ₹
              {formData.color_mode === 'color' ? '10' : '2'}/page
            </p>
          </div>
        )}

        <div className="mt-6 flex space-x-4">
          <button
            type="submit"
            disabled={loading || uploadingFiles || uploadedFiles.length === 0}
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

      <PaymentModal
        isOpen={showPaymentModal}
        onClose={() => setShowPaymentModal(false)}
        orderDetails={paymentDetails}
        onPaymentSuccess={handlePaymentSuccess}
        onPaymentFailure={handlePaymentFailure}
      />

      {showPaymentErrorModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4">
            <div className="text-center">
              <XCircle className="h-16 w-16 text-red-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Payment Failed</h2>
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