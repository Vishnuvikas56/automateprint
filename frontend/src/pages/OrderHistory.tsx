import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

interface HistoryEvent {
  history_id: number;
  order_id: string;
  status: string;
  message: string;
  meta: any;
  created_at: string;
}

export const OrderHistory: React.FC = () => {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (orderId) {
      fetchHistory();
    }
  }, [orderId]);

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/orders/${orderId}/history`);
      setHistory(response.data.history);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch order history');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return <CheckCircle className="h-6 w-6 text-green-600" />;
      case 'failed':
        return <XCircle className="h-6 w-6 text-red-600" />;
      case 'processing':
        return <Clock className="h-6 w-6 text-blue-600 animate-pulse" />;
      case 'pending':
        return <AlertCircle className="h-6 w-6 text-yellow-600" />;
      default:
        return <Clock className="h-6 w-6 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 border-green-500';
      case 'failed':
        return 'bg-red-100 border-red-500';
      case 'processing':
        return 'bg-blue-100 border-blue-500';
      case 'pending':
        return 'bg-yellow-100 border-yellow-500';
      default:
        return 'bg-gray-100 border-gray-500';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-red-100 text-red-700 p-4 rounded-lg">
          {error}
        </div>
        <button
          onClick={() => navigate('/my-orders')}
          className="mt-4 text-blue-600 hover:underline"
        >
          ← Back to Orders
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <button
        onClick={() => navigate('/my-orders')}
        className="flex items-center space-x-2 text-blue-600 hover:text-blue-700 mb-6"
      >
        <ArrowLeft className="h-5 w-5" />
        <span>Back to My Orders</span>
      </button>

      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Order Timeline</h1>
        <p className="text-gray-600 mb-6">Order ID: {orderId}</p>

        {history.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No history available</p>
        ) : (
          <div className="space-y-4">
            {history.map((event, index) => (
              <div
                key={event.history_id}
                className={`border-l-4 p-4 rounded-r-lg ${getStatusColor(event.status)}`}
              >
                <div className="flex items-start space-x-4">
                  <div className="flex-shrink-0 mt-1">
                    {getStatusIcon(event.status)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-gray-900">
                        {event.status.charAt(0).toUpperCase() + event.status.slice(1)}
                      </h3>
                      <span className="text-sm text-gray-500">
                        {new Date(event.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-gray-700 mt-1">{event.message}</p>
                    
                    {event.meta && Object.keys(event.meta).length > 0 && (
                      <div className="mt-2 p-2 bg-white bg-opacity-50 rounded text-xs">
                        <details>
                          <summary className="cursor-pointer text-gray-600">
                            Additional Details
                          </summary>
                          <pre className="mt-2 text-gray-600 overflow-auto">
                            {JSON.stringify(event.meta, null, 2)}
                          </pre>
                        </details>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};