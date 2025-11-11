import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { MapPin, Phone, Mail, Clock, Printer } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

interface Store {
  store_id: string;
  store_name: string;
  address: string;
  contact_number?: string;
  email?: string;
  business_hours?: {
    open: string;
    close: string;
  };
  pricing_info?: {
    bw_per_page: number;
    color_per_page: number;
  };
  status: string;
}

export const StoresList: React.FC = () => {
  const [stores, setStores] = useState<Store[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStores();
  }, []);

  const fetchStores = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/stores`);
      setStores(response.data.stores);
    } catch (error) {
      console.error('Failed to fetch stores:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Print Stores</h1>
        <p className="text-gray-600 mt-2">Available print shops on campus</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {stores.map((store) => (
          <div key={store.store_id} className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-xl font-bold text-gray-900">{store.store_name}</h3>
                <span className={`inline-block px-2 py-1 text-xs font-semibold rounded-full mt-2 ${
                  store.status === 'open' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {store.status.toUpperCase()}
                </span>
              </div>
              <Printer className="h-8 w-8 text-blue-600" />
            </div>

            <div className="space-y-3">
              <div className="flex items-start space-x-3">
                <MapPin className="h-5 w-5 text-gray-400 mt-0.5" />
                <p className="text-sm text-gray-600">{store.address}</p>
              </div>

              {store.contact_number && (
                <div className="flex items-center space-x-3">
                  <Phone className="h-5 w-5 text-gray-400" />
                  <p className="text-sm text-gray-600">{store.contact_number}</p>
                </div>
              )}

              {store.email && (
                <div className="flex items-center space-x-3">
                  <Mail className="h-5 w-5 text-gray-400" />
                  <p className="text-sm text-gray-600">{store.email}</p>
                </div>
              )}

              {store.business_hours && (
                <div className="flex items-center space-x-3">
                  <Clock className="h-5 w-5 text-gray-400" />
                  <p className="text-sm text-gray-600">
                    {store.business_hours.open} - {store.business_hours.close}
                  </p>
                </div>
              )}

              {store.pricing_info && (
                <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm font-semibold text-gray-700 mb-2">Pricing</p>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">B&W:</span>
                    <span className="font-semibold">₹{store.pricing_info.bw_per_page}/page</span>
                  </div>
                  <div className="flex justify-between text-sm mt-1">
                    <span className="text-gray-600">Color:</span>
                    <span className="font-semibold">₹{store.pricing_info.color_per_page}/page</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};