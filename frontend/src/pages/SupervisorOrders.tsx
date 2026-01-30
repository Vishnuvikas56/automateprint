import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Search, 
  Filter, 
  Printer, 
  User, 
  FileText, 
  Clock,
  CheckCircle,
  Package,
  X,
  Check,
  History,
  Info,
  Play,
  XCircle,
  AlertTriangle
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

interface ActiveJob {
  order_id: string;
  user_id: string;
  username: string;
  full_name: string;
  printer_id: string;
  binding_required: boolean;
  binding_done: boolean;
  ready_for_delivery: boolean;
  pages_count: number;
  copies: number;
  time_elapsed_minutes: number;
  status: string;
  order_date: string;
  actual_start_time: string | null;
  estimated_end_time: string | null;
  location: string;
  print_type: any;
  paper_type: any;
  is_delivered: boolean;
  base_price: number;
  binding_cost: number;
  total_price: number;
}

interface HistoryOrder {
  order_id: string;
  user_id: string;
  username: string;
  full_name: string;
  printer_id: string;
  binding_required: boolean;
  pages_count: number;
  copies: number;
  status: string;
  order_date: string;
  completion_date: string | null;
  print_type: any;
  paper_type: any;
  price: number;
  is_delivered: boolean;
}

interface PrintBreakdownItem {
  type: string;
  pages: number;
  price_per_page: number;
  copies: number;
  subtotal: number;
}

interface OrderDetails {
  order_id: string;
  pages_count: number;
  total_pdf_pages: number;
  copies: number;
  print_breakdown: PrintBreakdownItem[];
  total_print_cost: number;
  binding_cost: number;
  total_cost: number;
  binding_required: boolean;
  duplex: boolean;
  collate: boolean;
}

const SupervisorOrders: React.FC = () => {
  const navigate = useNavigate();
  const [activeJobs, setActiveJobs] = useState<ActiveJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [dateFilter, setDateFilter] = useState('2days');
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [showOrderDetails, setShowOrderDetails] = useState(false);
  const [selectedOrderDetails, setSelectedOrderDetails] = useState<OrderDetails | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  
  // History modal state
  const [historyOrders, setHistoryOrders] = useState<{
    pending_orders: { total: number; orders: HistoryOrder[] };
    completed_orders: { total: number; orders: HistoryOrder[] };
    failed_orders: { total: number; orders: HistoryOrder[] };
  } | null>(null);
  const [historySearch, setHistorySearch] = useState('');
  const [historyDateFilter, setHistoryDateFilter] = useState('week');
  const [historyStatusFilter, setHistoryStatusFilter] = useState('all');
  const [historyActiveTab, setHistoryActiveTab] = useState<'pending' | 'completed' | 'failed'>('completed');
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    fetchActiveJobs();
    
    const interval = setInterval(() => {
      fetchActiveJobs();
    }, 30000);

    return () => clearInterval(interval);
  }, [dateFilter]);

  const fetchActiveJobs = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_BASE_URL}/supervisor/orders/active-jobs`, {
        headers: { Authorization: `Bearer ${token}` },
        params: {
          search: searchTerm || undefined,
          date: getDateFilterValue()
        }
      });
      setActiveJobs(response.data.active_jobs);
    } catch (error) {
      console.error('Failed to fetch active jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchOrderHistory = async () => {
    setLoadingHistory(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_BASE_URL}/supervisor/orders/history`, {
        headers: { Authorization: `Bearer ${token}` },
        params: {
          search: historySearch || undefined,
          date: getHistoryDateFilterValue(),
          status: historyStatusFilter === 'all' ? undefined : historyStatusFilter
        }
      });
      setHistoryOrders(response.data);
    } catch (error) {
      console.error('Failed to fetch order history:', error);
    } finally {
      setLoadingHistory(false);
    }
  };

  const fetchOrderDetails = async (orderId: string) => {
    setLoadingDetails(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_BASE_URL}/supervisor/orders/${orderId}/details`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSelectedOrderDetails(response.data);
      setShowOrderDetails(true);
    } catch (error: any) {
      console.error('Failed to fetch order details:', error);
      alert(error.response?.data?.detail || 'Failed to load order details');
    } finally {
      setLoadingDetails(false);
    }
  };

  const getDateFilterValue = (): string | undefined => {
    const now = new Date();
    switch (dateFilter) {
      case 'today':
        return now.toISOString().split('T')[0];
      case '2days':
        const twoDaysAgo = new Date(now);
        twoDaysAgo.setDate(now.getDate() - 2);
        return twoDaysAgo.toISOString().split('T')[0];
      case 'week':
        const weekAgo = new Date(now);
        weekAgo.setDate(now.getDate() - 7);
        return weekAgo.toISOString().split('T')[0];
      case 'month':
        const monthAgo = new Date(now);
        monthAgo.setMonth(now.getMonth() - 1);
        return monthAgo.toISOString().split('T')[0];
      default:
        return undefined;
    }
  };

  const getHistoryDateFilterValue = (): string | undefined => {
    const now = new Date();
    switch (historyDateFilter) {
      case 'today':
        return now.toISOString().split('T')[0];
      case 'week':
        const weekAgo = new Date(now);
        weekAgo.setDate(now.getDate() - 7);
        return weekAgo.toISOString().split('T')[0];
      case 'month':
        const monthAgo = new Date(now);
        monthAgo.setMonth(now.getMonth() - 1);
        return monthAgo.toISOString().split('T')[0];
      default:
        return undefined;
    }
  };

  const markDelivered = async (orderId: string) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API_BASE_URL}/supervisor/orders/${orderId}/mark-delivered`,
        { notes: "Delivered to customer" },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchActiveJobs();
      alert('Order marked as delivered successfully!');
    } catch (error: any) {
      console.error('Failed to mark as delivered:', error);
      alert(error.response?.data?.detail || 'Failed to mark as delivered');
    }
  };

  const markBindingCompleted = async (orderId: string) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API_BASE_URL}/supervisor/orders/${orderId}/mark-binding-completed`,
        { notes: "Binding completed" },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchActiveJobs();
      alert('Binding completed - Order ready for delivery!');
    } catch (error: any) {
      console.error('Failed to mark binding completed:', error);
      alert(error.response?.data?.detail || 'Failed to mark binding completed');
    }
  };

  const formatTimeElapsed = (minutes: number): string => {
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatDeliveryTime = (dateString: string | null) => {
    if (!dateString) return 'Calculating...';
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'processing':
        return 'bg-indigo-100 text-indigo-700';
  
      case 'ready for delivery':
        return 'bg-orange-100 text-orange-700';
  
      case 'printed':
        return 'bg-teal-100 text-teal-700'; // mint green
  
      case 'delivered':
        return 'bg-emerald-200 text-emerald-800'; // darker emerald
  
      case 'pending':
        return 'bg-amber-100 text-amber-700';
  
      case 'failed':
        return 'bg-rose-100 text-rose-700';
  
      case 'cancelled':
        return 'bg-slate-200 text-slate-700';
  
      default:
        return 'bg-slate-200 text-slate-700';
    }
  };

  const getPrintTypeLabel = (type: string) => {
    const labels: any = {
      'bw': 'B&W',
      'color': 'Color',
      'glossy': 'Glossy',
      'thick': 'Thick',
      'poster': 'Poster'
    };
    return labels[type] || type.toUpperCase();
  };

  const getHistoryOrders = () => {
    if (!historyOrders) return [];
    
    switch (historyActiveTab) {
      case 'pending':
        return historyOrders.pending_orders.orders;
      case 'completed':
        return historyOrders.completed_orders.orders;
      case 'failed':
        return historyOrders.failed_orders.orders;
      default:
        return [];
    }
  };

  const getHistoryCount = (tab: 'pending' | 'completed' | 'failed') => {
    if (!historyOrders) return 0;
    
    switch (tab) {
      case 'pending':
        return historyOrders.pending_orders.total;
      case 'completed':
        return historyOrders.completed_orders.total;
      case 'failed':
        return historyOrders.failed_orders.total;
      default:
        return 0;
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
      {/* Header */}
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Active Print Jobs</h1>
          <p className="text-gray-600 mt-2">Currently processing orders</p>
        </div>
        <button
          onClick={() => {
            setShowHistoryModal(true);
            fetchOrderHistory();
          }}
          className="flex items-center space-x-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
        >
          <History className="h-5 w-5" />
          <span>History</span>
        </button>
      </div>

      {/* Filters and Search */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
              <input
                type="text"
                placeholder="Search by Order ID, User, or Printer..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && fetchActiveJobs()}
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-4">
            <select
              className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
            >
              <option value="2days">Last 2 Days</option>
              <option value="today">Today</option>
              <option value="week">Last Week</option>
              <option value="month">Last Month</option>
              <option value="all">All Time</option>
            </select>

            <button
              onClick={fetchActiveJobs}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              <Filter className="h-4 w-4" />
              <span>Apply Filters</span>
            </button>
          </div>
        </div>
      </div>

      {/* Active Jobs Grid */}
      <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
        {activeJobs.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-500">No active print jobs</p>
            <p className="text-sm text-gray-400 mt-1">All caught up!</p>
          </div>
        ) : (
          <div className="grid gap-4 p-6">
            {activeJobs.map((job) => (
              <div 
                key={job.order_id}
                className="border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow"
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  {/* Job Info */}
                  <div className="flex-1 space-y-3">
                    <div className="flex items-center space-x-3">
                      <h3 className="font-bold text-lg text-gray-900">{job.order_id}</h3>
                      <span className={`px-3 py-1 text-xs font-semibold rounded-full ${getStatusColor(job.status)}`}>
                        {job.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
                      <div className="flex items-center space-x-2">
                        <User className="h-4 w-4 text-gray-400" />
                        <span className="font-medium">{job.username}</span>
                        {job.full_name && (
                          <span className="text-gray-500">({job.full_name})</span>
                        )}
                      </div>

                      <div className="flex items-center space-x-2">
                        <Printer className="h-4 w-4 text-gray-400" />
                        <span>Printer: <span className="font-medium">{job.printer_id}</span></span>
                      </div>

                      <div className="flex items-center space-x-2">
                        <Package className="h-4 w-4 text-gray-400" />
                        <span>
                          Binding: <span className={`font-medium ${job.binding_required ? 'text-orange-600' : 'text-gray-600'}`}>
                            {job.binding_required ? 'Yes' : 'No'}
                          </span>
                        </span>
                      </div>

                      <div className="flex items-center space-x-2">
                        <Clock className="h-4 w-4 text-gray-400" />
                        <span>Started <span className="font-medium">{formatTimeElapsed(job.time_elapsed_minutes)}</span></span>
                      </div>

                      <div className="flex items-center space-x-2">
                        <Clock className="h-4 w-4 text-gray-400" />
                        <span>Delivery: <span className="font-medium text-blue-600">{formatDeliveryTime(job.estimated_end_time)}</span></span>
                      </div>

                      <div>
                        <span className="text-gray-600">Location: </span>
                        <span className="font-bold text-blue-600 text-lg">{job.location}</span>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col space-y-2 lg:items-end">
                    {/* Order Details Button */}
                    <button
                      onClick={() => fetchOrderDetails(job.order_id)}
                      disabled={loadingDetails}
                      className="flex items-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition text-sm font-medium disabled:opacity-50"
                    >
                      <Info className="h-4 w-4" />
                      <span>Order Details</span>
                    </button>

                    {/* Binding Completed Button - Only show if completed, binding required, and not done */}
                    {job.status.toLowerCase() === 'printed' && job.binding_required && !job.binding_done && (
                      <button
                        onClick={() => markBindingCompleted(job.order_id)}
                        className="flex items-center space-x-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition text-sm font-medium"
                      >
                        <Package className="h-4 w-4" />
                        <span>Mark Binding Completed</span>
                      </button>
                    )}

                    {/* Binding Done Status */}
                    {job.binding_done && (
                      <div className="flex items-center space-x-2 px-4 py-2 bg-green-100 text-green-700 rounded-lg border border-green-200">
                        <Check className="h-4 w-4" />
                        <span className="font-medium text-sm">Binding Completed</span>
                      </div>
                    )}

                    {/* Mark Delivered Button */}
                    {job.ready_for_delivery && (
                      <button
                        onClick={() => markDelivered(job.order_id)}
                        className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition font-medium"
>
<CheckCircle className="h-4 w-4" />
<span>Mark Delivered</span>
</button>
)}
</div>
</div>
</div>
))}
</div>
)}
</div>
  {/* Order Details Modal */}
  {showOrderDetails && selectedOrderDetails && (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900">Order Details</h2>
          <button
            onClick={() => setShowOrderDetails(false)}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="space-y-4">
          <div className="border-b pb-3">
            <h3 className="font-semibold text-gray-700 mb-2">Order ID</h3>
            <p className="text-gray-900 font-mono">{selectedOrderDetails.order_id}</p>
          </div>

          <div className="border-b pb-3">
            <h3 className="font-semibold text-gray-700 mb-2">Document Info</h3>
            <div className="space-y-1 text-sm">
              <p><span className="text-gray-600">Total Pages:</span> <span className="font-medium">{selectedOrderDetails.total_pdf_pages}</span></p>
              <p><span className="text-gray-600">Copies:</span> <span className="font-medium">{selectedOrderDetails.copies}</span></p>
              <p><span className="text-gray-600">Duplex:</span> <span className="font-medium">{selectedOrderDetails.duplex ? 'Yes' : 'No'}</span></p>
              <p><span className="text-gray-600">Collate:</span> <span className="font-medium">{selectedOrderDetails.collate ? 'Yes' : 'No'}</span></p>
              <p><span className="text-gray-600">Binding:</span> <span className="font-medium">{selectedOrderDetails.binding_required ? 'Yes' : 'No'}</span></p>
            </div>
          </div>

          <div className="border-b pb-3">
            <h3 className="font-semibold text-gray-700 mb-3">Print Breakdown</h3>
            <div className="space-y-2">
              {selectedOrderDetails.print_breakdown.map((item, index) => (
                <div key={index} className="bg-gray-50 p-3 rounded">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium text-gray-900">{getPrintTypeLabel(item.type)}</span>
                    <span className="font-semibold text-gray-900">₹{item.subtotal.toFixed(2)}</span>
                  </div>
                  <div className="text-xs text-gray-600 space-y-0.5">
                    <p>{item.pages} pages × ₹{item.price_per_page} per page × {item.copies} {item.copies > 1 ? 'copies' : 'copy'}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="font-semibold text-gray-700 mb-3">Price Summary</h3>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Total Print Cost:</span>
                <span className="font-medium">₹{selectedOrderDetails.total_print_cost.toFixed(2)}</span>
              </div>
              {selectedOrderDetails.binding_cost > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Binding Cost:</span>
                  <span className="font-medium text-orange-600">₹{selectedOrderDetails.binding_cost.toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between text-lg font-bold border-t pt-2 mt-2">
                <span>Total:</span>
                <span className="text-blue-600">₹{selectedOrderDetails.total_cost.toFixed(2)}</span>
              </div>
            </div>
          </div>
        </div>

        <button
          onClick={() => setShowOrderDetails(false)}
          className="w-full mt-6 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          Close
        </button>
      </div>
    </div>
  )}

  {/* History Modal */}
  {showHistoryModal && (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-white rounded-lg w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-2xl font-bold text-gray-900">Order History</h2>
          <button
            onClick={() => setShowHistoryModal(false)}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Filters */}
        <div className="p-6 border-b bg-gray-50">
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
                <input
                  type="text"
                  placeholder="Search orders..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  value={historySearch}
                  onChange={(e) => setHistorySearch(e.target.value)}
                />
              </div>
            </div>

            <div className="flex gap-4">
              <select
                className="border border-gray-300 rounded-lg px-3 py-2"
                value={historyDateFilter}
                onChange={(e) => setHistoryDateFilter(e.target.value)}
              >
                <option value="today">Today</option>
                <option value="week">Last Week</option>
                <option value="month">Last Month</option>
                <option value="all">All Time</option>
              </select>

              <button
                onClick={fetchOrderHistory}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                Apply
              </button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b">
          <nav className="flex -mb-px">
            <button
              onClick={() => setHistoryActiveTab('pending')}
              className={`flex items-center space-x-2 py-4 px-6 border-b-2 font-medium text-sm ${
                historyActiveTab === 'pending'
                  ? 'border-yellow-500 text-yellow-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Clock className="h-4 w-4" />
              <span>Pending</span>
              <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded-full">
                {getHistoryCount('pending')}
              </span>
            </button>
            
            <button
              onClick={() => setHistoryActiveTab('completed')}
              className={`flex items-center space-x-2 py-4 px-6 border-b-2 font-medium text-sm ${
                historyActiveTab === 'completed'
                  ? 'border-green-500 text-green-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <CheckCircle className="h-4 w-4" />
              <span>Completed</span>
              <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">
                {getHistoryCount('completed')}
              </span>
            </button>
            
            <button
              onClick={() => setHistoryActiveTab('failed')}
              className={`flex items-center space-x-2 py-4 px-6 border-b-2 font-medium text-sm ${
                historyActiveTab === 'failed'
                  ? 'border-red-500 text-red-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <XCircle className="h-4 w-4" />
              <span>Failed</span>
              <span className="bg-red-100 text-red-800 text-xs px-2 py-1 rounded-full">
                {getHistoryCount('failed')}
              </span>
            </button>
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loadingHistory ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <div className="space-y-3">
              {getHistoryOrders().length > 0 ? (
                getHistoryOrders().map((order) => (
                  <div 
                    key={order.order_id} 
                    className={`border rounded-lg p-4 ${
                      historyActiveTab === 'pending' ? 'border-yellow-200 bg-yellow-50' :
                      historyActiveTab === 'completed' ? 'border-green-200 bg-green-50' :
                      'border-red-200 bg-red-50'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <span className="font-semibold text-gray-900">{order.order_id}</span>
                          <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(order.status)}`}>
                            {order.status}
                          </span>
                          {order.is_delivered && (
                            <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                              Delivered
                            </span>
                          )}
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm text-gray-700">
                          <div>
                            <span className="text-gray-500">User:</span> <span className="font-medium">{order.username}</span>
                          </div>
                          <div>
                            <span className="text-gray-500">Printer:</span> <span className="font-medium">{order.printer_id}</span>
                          </div>
                          <div>
                            <span className="text-gray-500">Pages:</span> <span className="font-medium">{order.pages_count} × {order.copies}</span>
                          </div>
                          <div>
                            <span className="text-gray-500">Price:</span> <span className="font-medium">₹{order.price.toFixed(2)}</span>
                          </div>
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                          {order.completion_date 
                            ? `Completed: ${formatDateTime(order.completion_date)}`
                            : `Ordered: ${formatDateTime(order.order_date)}`
                          }
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-12">
                  <AlertTriangle className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                  <p className="text-gray-500">No {historyActiveTab} orders found</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )}
</div>
);
};
export default SupervisorOrders;