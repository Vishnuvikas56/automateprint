import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Filter, 
  Search,
  Eye,
  Check,
  X
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

interface Alert {
  alert_id: number;
  alert_type: string;
  alert_message: string;
  severity: string;
  status: string;
  printer_id: string | null;
  order_id: string | null;
  created_at: string;
  resolved_at: string | null;
  metadata: any;
}

const SupervisorAlerts: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  useEffect(() => {
    fetchAlerts();
  }, [severityFilter, statusFilter]);

  const fetchAlerts = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/supervisor/alerts`, {
        params: {
          severity: severityFilter !== 'all' ? severityFilter : undefined,
          status: statusFilter !== 'all' ? statusFilter : undefined,
          limit: 100
        }
      });
      setAlerts(response.data.alerts);
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  const acknowledgeAlert = async (alertId: number) => {
    setActionLoading(alertId);
    try {
      await axios.post(`${API_BASE_URL}/supervisor/alerts/${alertId}/acknowledge`);
      fetchAlerts();
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
    } finally {
      setActionLoading(null);
    }
  };

  const resolveAlert = async (alertId: number) => {
    setActionLoading(alertId);
    try {
      await axios.post(`${API_BASE_URL}/supervisor/alerts/${alertId}/resolve`);
      fetchAlerts();
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    } finally {
      setActionLoading(null);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'warning': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'info': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'unread': return 'bg-red-100 text-red-800';
      case 'acknowledged': return 'bg-yellow-100 text-yellow-800';
      case 'resolved': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getAlertIcon = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical': return <AlertTriangle className="h-5 w-5 text-red-500" />;
      case 'warning': return <AlertTriangle className="h-5 w-5 text-orange-500" />;
      case 'info': return <Clock className="h-5 w-5 text-blue-500" />;
      default: return <AlertTriangle className="h-5 w-5 text-gray-500" />;
    }
  };

  const filteredAlerts = alerts.filter(alert =>
    alert.alert_message.toLowerCase().includes(searchTerm.toLowerCase()) ||
    alert.alert_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (alert.printer_id && alert.printer_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (alert.order_id && alert.order_id.toLowerCase().includes(searchTerm.toLowerCase()))
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
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">System Alerts</h1>
        <p className="text-gray-600 mt-2">Monitor and manage system alerts and notifications</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
              <input
                type="text"
                placeholder="Search alerts..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          <select
            className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>
          <select
            className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Status</option>
            <option value="unread">Unread</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>
      </div>

      {/* Alerts List */}
      <div className="space-y-4">
        {filteredAlerts.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <CheckCircle className="h-12 w-12 mx-auto text-green-500 mb-4" />
            <p className="text-gray-500">No alerts found</p>
          </div>
        ) : (
          filteredAlerts.map((alert) => (
            <div
              key={alert.alert_id}
              className="bg-white rounded-lg shadow border border-gray-200 p-6"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4 flex-1">
                  <div className="flex-shrink-0">
                    {getAlertIcon(alert.severity)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="font-semibold text-gray-900">
                        {alert.alert_type.replace(/_/g, ' ').toUpperCase()}
                      </h3>
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getSeverityColor(alert.severity)}`}>
                        {alert.severity}
                      </span>
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(alert.status)}`}>
                        {alert.status}
                      </span>
                    </div>
                    <p className="text-gray-700 mb-3">{alert.alert_message}</p>
                    <div className="flex items-center space-x-4 text-sm text-gray-500">
                      <span>Created: {new Date(alert.created_at).toLocaleString()}</span>
                      {alert.printer_id && (
                        <span>Printer: {alert.printer_id}</span>
                      )}
                      {alert.order_id && (
                        <span>Order: {alert.order_id}</span>
                      )}
                    </div>
                    {alert.metadata && (
                      <div className="mt-2 text-sm text-gray-600">
                        <pre className="whitespace-pre-wrap">
                          {JSON.stringify(alert.metadata, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-2 ml-4">
                  {alert.status === 'Unread' && (
                    <button
                      onClick={() => acknowledgeAlert(alert.alert_id)}
                      disabled={actionLoading === alert.alert_id}
                      className="flex items-center space-x-1 px-3 py-2 bg-yellow-600 text-white text-sm rounded hover:bg-yellow-700 transition disabled:opacity-50"
                    >
                      <Eye className="h-4 w-4" />
                      <span>Acknowledge</span>
                    </button>
                  )}
                  {alert.status !== 'Resolved' && (
                    <button
                      onClick={() => resolveAlert(alert.alert_id)}
                      disabled={actionLoading === alert.alert_id}
                      className="flex items-center space-x-1 px-3 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition disabled:opacity-50"
                    >
                      <Check className="h-4 w-4" />
                      <span>Resolve</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Summary */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4 text-sm text-gray-600">
        <div>Total: {alerts.length} alerts</div>
        <div>Unread: {alerts.filter(a => a.status === 'Unread').length}</div>
        <div>Acknowledged: {alerts.filter(a => a.status === 'Acknowledged').length}</div>
        <div>Resolved: {alerts.filter(a => a.status === 'Resolved').length}</div>
      </div>
    </div>
  );
};

export default SupervisorAlerts;