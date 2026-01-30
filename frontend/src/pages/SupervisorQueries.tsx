import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Plus, 
  Search, 
  Filter, 
  FileText,
  Printer,
  Package,
  Settings,
  AlertTriangle,
  Clock,
  CheckCircle,
  XCircle,
  MoreVertical,
  Upload,
  Loader
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

interface Query {
  query_id: string;
  query_type: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  printer_id: string | null;
  order_id: string | null;
  file_url: string | null;
  file_name: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

interface QueryCreate {
  query_type: string;
  title: string;
  description: string;
  priority: string;
  printer_id?: string;
  order_id?: string;
}

const SupervisorQueries: React.FC = () => {
  const [queries, setQueries] = useState<Query[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [queryTypeFilter, setQueryTypeFilter] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createForm, setCreateForm] = useState<QueryCreate>({
    query_type: 'printer',
    title: '',
    description: '',
    priority: 'Info',
    printer_id: '',
    order_id: ''
  });

  useEffect(() => {
    fetchQueries();
  }, [statusFilter, queryTypeFilter]);

  const fetchQueries = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/supervisor/queries`, {
        params: {
          status: statusFilter !== 'all' ? statusFilter : undefined,
          query_type: queryTypeFilter !== 'all' ? queryTypeFilter : undefined,
          limit: 100
        }
      });
      setQueries(response.data.queries);
    } catch (error) {
      console.error('Failed to fetch queries:', error);
    } finally {
      setLoading(false);
    }
  };

  const createQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLoading(true);
    try {
      const payload = {
        ...createForm,
        printer_id: createForm.printer_id || undefined,
        order_id: createForm.order_id || undefined
      };
      await axios.post(`${API_BASE_URL}/supervisor/queries`, payload);
      setShowCreateModal(false);
      setCreateForm({
        query_type: 'printer',
        title: '',
        description: '',
        priority: 'Info',
        printer_id: '',
        order_id: ''
      });
      fetchQueries();
    } catch (error: any) {
      console.error('Failed to create query:', error);
      alert(error.response?.data?.detail || 'Failed to create query');
    } finally {
      setCreateLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'open': return 'bg-red-100 text-red-800 border-red-200';
      case 'in_progress': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'resolved': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'open': return <AlertTriangle className="h-4 w-4" />;
      case 'in_progress': return <Clock className="h-4 w-4" />;
      case 'resolved': return <CheckCircle className="h-4 w-4" />;
      default: return <FileText className="h-4 w-4" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'warning': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'info': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getQueryTypeIcon = (type: string) => {
    switch (type) {
      case 'printer': return <Printer className="h-5 w-5" />;
      case 'user_order': return <Package className="h-5 w-5" />;
      case 'inventory': return <Settings className="h-5 w-5" />;
      case 'system': return <AlertTriangle className="h-5 w-5" />;
      default: return <FileText className="h-5 w-5" />;
    }
  };

  const formatStatusText = (status: string) => {
    switch (status.toLowerCase()) {
      case 'open': return 'Open - Awaiting Response';
      case 'in_progress': return 'In Progress - Being Reviewed';
      case 'resolved': return 'Resolved - Issue Fixed';
      default: return status.replace('_', ' ');
    }
  };

  const getTimeSinceCreation = (createdAt: string) => {
    const created = new Date(createdAt);
    const now = new Date();
    const diffMs = now.getTime() - created.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor(diffMs / (1000 * 60));

    if (diffDays > 0) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    if (diffHours > 0) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffMinutes > 0) return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
    return 'Just now';
  };

  const filteredQueries = queries.filter(query =>
    query.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    query.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
    query.query_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

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
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Issue Management</h1>
          <p className="text-gray-600 mt-2">Create and track system issues and queries</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          <Plus className="h-4 w-4" />
          <span>New Query</span>
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
              <input
                type="text"
                placeholder="Search queries..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          <select
            className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Status</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
          </select>
          <select
            className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={queryTypeFilter}
            onChange={(e) => setQueryTypeFilter(e.target.value)}
          >
            <option value="all">All Types</option>
            <option value="printer">Printer</option>
            <option value="user_order">User Order</option>
            <option value="inventory">Inventory</option>
            <option value="system">System</option>
            <option value="other">Other</option>
          </select>
        </div>
      </div>

      {/* Queries List */}
      <div className="space-y-4">
        {filteredQueries.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <FileText className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-500">No queries found</p>
            <p className="text-sm text-gray-400 mt-1">
              {searchTerm || statusFilter !== 'all' || queryTypeFilter !== 'all' 
                ? 'Try adjusting your search filters' 
                : 'Create your first query to get started'}
            </p>
          </div>
        ) : (
          filteredQueries.map((query) => (
            <div
              key={query.query_id}
              className="bg-white rounded-lg shadow border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4 flex-1">
                  <div className="flex-shrink-0 mt-1">
                    <div className="flex items-center justify-center w-10 h-10 bg-gray-100 rounded-lg">
                      {getQueryTypeIcon(query.query_type)}
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="font-semibold text-gray-900 text-lg">{query.title}</h3>
                      <span className={`px-3 py-1 text-xs font-semibold rounded-full border ${getPriorityColor(query.priority)}`}>
                        {query.priority}
                      </span>
                    </div>
                    
                    <p className="text-gray-700 mb-4">{query.description}</p>
                    
                    <div className="flex items-center space-x-6 text-sm text-gray-600 mb-3">
                      <div className="flex items-center space-x-1">
                        <span className="font-medium">Type:</span>
                        <span className="capitalize">{query.query_type.replace('_', ' ')}</span>
                      </div>
                      {query.printer_id && (
                        <div className="flex items-center space-x-1">
                          <span className="font-medium">Printer:</span>
                          <span>{query.printer_id}</span>
                        </div>
                      )}
                      {query.order_id && (
                        <div className="flex items-center space-x-1">
                          <span className="font-medium">Order:</span>
                          <span>{query.order_id}</span>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4 text-sm text-gray-500">
                        <span>Created: {new Date(query.created_at).toLocaleDateString()}</span>
                        <span>•</span>
                        <span>{getTimeSinceCreation(query.created_at)}</span>
                        {query.resolved_at && (
                          <>
                            <span>•</span>
                            <span>Resolved: {new Date(query.resolved_at).toLocaleDateString()}</span>
                          </>
                        )}
                      </div>

                      <div className="flex items-center space-x-2">
                        <div className="flex items-center space-x-2 px-3 py-2 rounded-lg border">
                          {getStatusIcon(query.status)}
                          <span className={`text-sm font-medium ${getStatusColor(query.status).split(' ')[0]} ${getStatusColor(query.status).split(' ')[1]}`}>
                            {formatStatusText(query.status)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {query.file_url && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <a
                          href={query.file_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-800"
                        >
                          <Upload className="h-4 w-4" />
                          <span>{query.file_name || 'View Attachment'}</span>
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Create Query Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">Create New Query</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <XCircle className="h-6 w-6" />
              </button>
            </div>
            
            <form onSubmit={createQuery}>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Query Type *
                    </label>
                    <select
                      required
                      value={createForm.query_type}
                      onChange={(e) => setCreateForm({...createForm, query_type: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="printer">Printer Issue</option>
                      <option value="user_order">User Order Problem</option>
                      <option value="inventory">Inventory Management</option>
                      <option value="system">System Issue</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Priority Level *
                    </label>
                    <select
                      required
                      value={createForm.priority}
                      onChange={(e) => setCreateForm({...createForm, priority: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="Info">Info - General Inquiry</option>
                      <option value="Warning">Warning - Needs Attention</option>
                      <option value="Critical">Critical - Urgent Issue</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Issue Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={createForm.title}
                    onChange={(e) => setCreateForm({...createForm, title: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Brief description of the issue"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Detailed Description *
                  </label>
                  <textarea
                    required
                    value={createForm.description}
                    onChange={(e) => setCreateForm({...createForm, description: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={4}
                    placeholder="Please provide detailed information about the issue, steps to reproduce, and any relevant context..."
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Printer ID (if applicable)
                    </label>
                    <input
                      type="text"
                      value={createForm.printer_id || ''}
                      onChange={(e) => setCreateForm({...createForm, printer_id: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., PRINTER-001"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Order ID (if applicable)
                    </label>
                    <input
                      type="text"
                      value={createForm.order_id || ''}
                      onChange={(e) => setCreateForm({...createForm, order_id: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., ORDER-001"
                    />
                  </div>
                </div>
              </div>
              <div className="flex space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
                >
                  {createLoading ? (
                    <div className="flex items-center justify-center space-x-2">
                      <Loader className="h-4 w-4 animate-spin" />
                      <span>Creating Query...</span>
                    </div>
                  ) : (
                    'Create Query'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Summary */}
      <div className="mt-8 p-6 bg-gray-50 rounded-lg">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Query Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{queries.length}</div>
            <div className="text-sm text-gray-600">Total Queries</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">
              {queries.filter(q => q.status === 'open').length}
            </div>
            <div className="text-sm text-gray-600">Open Issues</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-600">
              {queries.filter(q => q.status === 'in_progress').length}
            </div>
            <div className="text-sm text-gray-600">In Progress</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {queries.filter(q => q.status === 'resolved').length}
            </div>
            <div className="text-sm text-gray-600">Resolved</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SupervisorQueries;