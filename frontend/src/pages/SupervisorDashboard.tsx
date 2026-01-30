import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  FileText, 
  Printer, 
  CheckCircle, 
  Clock, 
  AlertTriangle,
  DollarSign,
  Plus,
  Loader,
  Pause,
  Square,
  RotateCcw,
  X,
  Bell,
  Filter,
  ChevronDown,
  ChevronUp,
  Flame,
  Droplet,
  FileCheck,
  AlertCircle,
  Settings,
  Check,
  Wrench,
  VolumeX,
  RefreshCw
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

interface SupervisorStats {
  orders: {
    total_today: number;
    revenue_today: number;
    active_orders: number;
    completed_today: number;
    pending_binding: number;
  };
  printers: {
    total: number;
    up_count: number;
    down_count: number;
  };
  alerts: {
    sla_breaches: number;
    low_inventory: number;
  };
  printer_load: Array<{
    printer_id: string;
    printer_name: string;
    pages_printed_today: number;
    load_percentage: number;
  }>;
}

interface Printer {
  printer_id: string;
  printer_name: string;
  printer_model: string;
  type: string;
  status: string;
  paper_available: number;
  ink_toner_level: any;
  color_support: boolean;
  duplex_support: boolean;
  connection_type: string;
  pages_printed: number;
  current_job_id: string | null;
  queue_length: number;
  temperature: number;
  humidity: number;
  total_pages_printed: number;
  last_maintenance: string | null;
}

interface NotificationAlert {
  alert_id: number;
  alert_type: string;
  alert_message: string;
  severity: string;
  status: string;
  printer_id: string | null;
  order_id: string | null;
  created_at: string;
  acknowledged: boolean;
  fixed: boolean;
  action_taken: string | null;
  metadata: any;
}

interface GroupedNotifications {
  printer_id: string | null;
  printer_name: string;
  alerts: NotificationAlert[];
}

interface NotificationSummary {
  critical_issues: number;
  warnings: number;
  info_alerts: number;
  total_alerts: number;
  printers_ok: boolean;
  healthy_printers: number;
  total_printers: number;
}

const SupervisorDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<SupervisorStats | null>(null);
  const [printers, setPrinters] = useState<Printer[]>([]);
  const [notifications, setNotifications] = useState<GroupedNotifications[]>([]);
  const [notificationSummary, setNotificationSummary] = useState<NotificationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAddPrinter, setShowAddPrinter] = useState(false);
  const [creatingPrinter, setCreatingPrinter] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  
  // Notification filters
  const [notificationFilter, setNotificationFilter] = useState<string>('all');
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);

  const [printerForm, setPrinterForm] = useState({
    printer_id: '',
    printer_name: '',
    printer_model: '',
    type: 'Laser',
    supported_sizes: ['A4'],
    color_support: false,
    duplex_support: false,
    connection_type: 'USB',
    paper_capacity: 500
  });

  useEffect(() => {
    fetchDashboardData();
    
    const interval = setInterval(() => {
      if (autoRefresh) {
        fetchDashboardData();
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [autoRefresh, notificationFilter]);

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem('token');
      const config = { headers: { Authorization: `Bearer ${token}` } };

      const [statsRes, printersRes, notificationsRes, summaryRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/supervisor/dashboard-stats`, config),
        axios.get(`${API_BASE_URL}/supervisor/printers`, config),
        axios.get(`${API_BASE_URL}/supervisor/notifications?severity=${notificationFilter === 'all' ? '' : notificationFilter}`, config),
        axios.get(`${API_BASE_URL}/supervisor/notifications/summary`, config),
      ]);

      setStats(statsRes.data);
      setPrinters(printersRes.data.printers);
      setNotifications(notificationsRes.data.grouped_alerts);
      setNotificationSummary(summaryRes.data);
    } catch (error) {
      console.error('Failed to fetch supervisor dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddPrinter = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingPrinter(true);

    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API_BASE_URL}/supervisor/printers`, 
        printerForm,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setShowAddPrinter(false);
      setPrinterForm({
        printer_id: '',
        printer_name: '',
        printer_model: '',
        type: 'Laser',
        supported_sizes: ['A4'],
        color_support: false,
        duplex_support: false,
        connection_type: 'USB',
        paper_capacity: 500
      });
      fetchDashboardData();
    } catch (error: any) {
      console.error('Failed to create printer:', error);
      alert(error.response?.data?.detail || 'Failed to create printer');
    } finally {
      setCreatingPrinter(false);
    }
  };

  const handlePrinterAction = async (printerId: string, action: string) => {
    try {
      const token = localStorage.getItem('token');
      
      let endpoint = '';
      switch (action) {
        case 'pause':
          endpoint = `/supervisor/printers/${printerId}/pause`;
          break;
        case 'resume':
          endpoint = `/supervisor/printers/${printerId}/resume`;
          break;
        case 'cancel':
          endpoint = `/supervisor/printers/${printerId}/cancel-job`;
          break;
        case 'test':
          endpoint = `/supervisor/printers/${printerId}/test-print`;
          break;
        default:
          return;
      }
  
      const response = await axios.post(
        `${API_BASE_URL}${endpoint}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
  
      const backendMessage = response.data?.message || response.data?.detail || `${action} successful`;
      alert(backendMessage);
      fetchDashboardData();
  
    } catch (error: any) {
      console.error(`Failed to ${action} printer:`, error);
      const backendError = error.response?.data?.message || error.response?.data?.detail || `Failed to ${action} printer`;
      alert(backendError);
    }
  };

  const handleAcknowledge = async (alertId: number) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API_BASE_URL}/supervisor/notifications/${alertId}/acknowledge`,
        { action_taken: "Acknowledged by supervisor" },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchDashboardData();
    } catch (error: any) {
      console.error('Failed to acknowledge alert:', error);
      alert(error.response?.data?.detail || 'Failed to acknowledge alert');
    }
  };

  const handleFix = async (alertId: number) => {
    const actionTaken = "Action taken by the supervisor. problem's fixed.";
    if (!actionTaken) return;

    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API_BASE_URL}/supervisor/notifications/${alertId}/fix`,
        { 
          action_taken: actionTaken,
          notes: "Fixed by supervisor"
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchDashboardData();
    } catch (error: any) {
      console.error('Failed to fix alert:', error);
      alert(error.response?.data?.detail || 'Failed to fix alert');
    }
  };

  const handleMute = async (alertId: number) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API_BASE_URL}/supervisor/notifications/${alertId}/mute`,
        { duration_minutes: 60 },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchDashboardData();
    } catch (error: any) {
      console.error('Failed to mute alert:', error);
      alert(error.response?.data?.detail || 'Failed to mute alert');
    }
  };

  const toggleGroup = (groupId: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(groupId)) {
      newExpanded.delete(groupId);
    } else {
      newExpanded.add(groupId);
    }
    setExpandedGroups(newExpanded);
  };

  const getAlertIcon = (alertType: string) => {
    switch (alertType) {
      case 'paper_empty':
      case 'low_paper':
        return <FileCheck className="h-4 w-4" />;
      case 'low_ink':
        return <Droplet className="h-4 w-4" />;
      case 'jam':
      case 'offline':
      case 'maintenance':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <Settings className="h-4 w-4" />;
    }
  };

  const getSeverityStyles = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return {
          bg: 'bg-red-50',
          border: 'border-red-200',
          text: 'text-red-800',
          badge: 'bg-red-100 text-red-800',
          icon: 'text-red-600'
        };
      case 'warning':
        return {
          bg: 'bg-yellow-50',
          border: 'border-yellow-200',
          text: 'text-yellow-800',
          badge: 'bg-yellow-100 text-yellow-800',
          icon: 'text-yellow-600'
        };
      case 'info':
        return {
          bg: 'bg-blue-50',
          border: 'border-blue-200',
          text: 'text-blue-800',
          badge: 'bg-blue-100 text-blue-800',
          icon: 'text-blue-600'
        };
      default:
        return {
          bg: 'bg-gray-50',
          border: 'border-gray-200',
          text: 'text-gray-800',
          badge: 'bg-gray-100 text-gray-800',
          icon: 'text-gray-600'
        };
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'online':
        return 'bg-green-100 text-green-800';
      case 'offline':
        return 'bg-red-100 text-red-800';
      case 'maintenance':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'idle':
        return 'bg-blue-100 text-blue-800';
      case 'busy':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (days === 1) return `Yesterday at ${date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
    return date.toLocaleString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
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
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Supervisor Dashboard</h1>
          <p className="text-gray-600 mt-2">Real-time monitoring and management overview</p>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={() => fetchDashboardData()}
            className="flex items-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition ${
              autoRefresh 
                ? 'bg-green-100 text-green-700' 
                : 'bg-gray-100 text-gray-700'
            }`}
          >
            <span>Auto-refresh: {autoRefresh ? 'ON' : 'OFF'}</span>
          </button>
        </div>
      </div>

      {/* Notification Summary Banner */}
      {notificationSummary && notificationSummary.total_alerts > 0 && (
        <div className="mb-6 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-6">
              {notificationSummary.critical_issues > 0 && (
                <div className="flex items-center space-x-2">
                  <Flame className="h-5 w-5 text-red-600" />
                  <span className="text-red-700 font-semibold">
                    {notificationSummary.critical_issues} Critical Issue{notificationSummary.critical_issues !== 1 ? 's' : ''}
                  </span>
                </div>
              )}
              {notificationSummary.warnings > 0 && (
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="h-5 w-5 text-yellow-600" />
                  <span className="text-yellow-700 font-semibold">
                    {notificationSummary.warnings} Warning{notificationSummary.warnings !== 1 ? 's' : ''}
                  </span>
                </div>
              )}
              {notificationSummary.info_alerts > 0 && (
                <div className="flex items-center space-x-2">
                  <Bell className="h-5 w-5 text-blue-600" />
                  <span className="text-blue-700 font-semibold">
                    {notificationSummary.info_alerts} Info Alert{notificationSummary.info_alerts !== 1 ? 's' : ''}
                  </span>
                </div>
              )}
            </div>
            {notificationSummary.printers_ok && (
              <div className="flex items-center space-x-2 text-green-700">
                <CheckCircle className="h-5 w-5" />
                <span className="font-semibold">All Printers OK</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Add Printer Button if no printers */}
      {printers.length === 0 && (
        <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <Printer className="h-12 w-12 text-yellow-600 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-yellow-800 mb-2">No Printers Found</h2>
          <p className="text-yellow-700 mb-4">
            You need to add printers to start managing orders. Click the button below to add your first printer.
          </p>
          <button
            onClick={() => setShowAddPrinter(true)}
            className="bg-yellow-600 text-white px-6 py-3 rounded-lg hover:bg-yellow-700 transition flex items-center justify-center space-x-2 mx-auto"
          >
            <Plus className="h-5 w-5" />
            <span>Add First Printer</span>
          </button>
        </div>
      )}

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Orders Today</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.orders.total_today || 0}</p>
              <p className="text-xs text-green-600 mt-1">Live</p>
            </div>
            <FileText className="h-10 w-10 text-blue-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Revenue Today</p>
              <p className="text-2xl font-bold text-gray-900">₹{stats?.orders.revenue_today?.toFixed(2) || '0.00'}</p>
              <p className="text-xs text-green-600 mt-1">Live</p>
            </div>
            <DollarSign className="h-10 w-10 text-green-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-emerald-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Printers Operational</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.printers.up_count || 0}/{stats?.printers.total || 0}</p>
              <p className="text-xs text-red-600 mt-1">{stats?.printers.down_count || 0} printers down</p>
            </div>
            <Printer className="h-10 w-10 text-emerald-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-orange-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Active Orders</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.orders.active_orders || 0}</p>
              <p className="text-xs text-gray-600 mt-1">{stats?.orders.pending_binding || 0} pending binding</p>
            </div>
            <Clock className="h-10 w-10 text-orange-500" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Printer Status Overview */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">Printer Status</h2>
            <button
              onClick={() => setShowAddPrinter(true)}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm"
            >
              <Plus className="h-4 w-4" />
              <span>Add Printer</span>
            </button>
          </div>
          
          {printers.length > 0 ? (
            <div className="space-y-4">
              {printers.map((printer) => (
                <div key={printer.printer_id} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="font-semibold text-gray-900">{printer.printer_name}</h3>
                      <p className="text-sm text-gray-600">{printer.printer_model} • {printer.printer_id}</p>
                    </div>
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(printer.status)}`}>
                      {printer.status}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 text-sm mb-3">
                    <div>
                      <span className="text-gray-600">Paper:</span>
                      <span className="ml-2 font-medium">{printer.paper_available} sheets</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Queue:</span>
                      <span className="ml-2 font-medium">{printer.queue_length} jobs</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Type:</span>
                      <span className="ml-2 font-medium">{printer.type}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Pages printed:</span>
                      <span className="ml-2 font-medium">{printer.total_pages_printed}</span>
                    </div>
                  </div>

                  <div className="flex space-x-2">
                    <button
                      onClick={() => handlePrinterAction(printer.printer_id, 'pause')}
                      className="flex items-center space-x-1 px-3 py-1 bg-yellow-100 text-yellow-700 rounded text-xs hover:bg-yellow-200"
                    >
                      <Pause className="h-3 w-3" />
                      <span>Pause</span>
                    </button>
                    <button
                      onClick={() => handlePrinterAction(printer.printer_id, 'cancel')}
                      className="flex items-center space-x-1 px-3 py-1 bg-red-100 text-red-700 rounded text-xs hover:bg-red-200"
                    >
                      <Square className="h-3 w-3" />
                      <span>Cancel Job</span>
                    </button>
                    {/* <button
                      onClick={() => handlePrinterAction(printer.printer_id, 'test')}
                      className="flex items-center space-x-1 px-3 py-1 bg-blue-100 text-blue-700 rounded text-xs hover:bg-blue-200"
                    >
                      <RotateCcw className="h-3 w-3" />
                      <span>Test Print</span>
                    </button> */}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Printer className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p>No printers added yet</p>
            </div>
          )}
        </div>

        {/* Enhanced Notifications Panel */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900 flex items-center">
              <Bell className="h-5 w-5 mr-2" />
              Notifications
            </h2>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center space-x-2 px-3 py-1 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition text-sm"
            >
              <Filter className="h-4 w-4" />
              <span>Filter</span>
            </button>
          </div>

          {/* Filter Options */}
          {showFilters && (
            <div className="mb-4 flex space-x-2">
              <button
                onClick={() => setNotificationFilter('all')}
                className={`px-3 py-1 rounded text-sm ${
                  notificationFilter === 'all'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setNotificationFilter('Critical')}
                className={`px-3 py-1 rounded text-sm ${
                  notificationFilter === 'Critical'
                    ? 'bg-red-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Critical
              </button>
              <button
                onClick={() => setNotificationFilter('Warning')}
                className={`px-3 py-1 rounded text-sm ${
                  notificationFilter === 'Warning'
                    ? 'bg-yellow-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Warning
              </button>
              <button
                onClick={() => setNotificationFilter('Info')}
                className={`px-3 py-1 rounded text-sm ${
                  notificationFilter === 'Info'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Info
              </button>
            </div>
          )}

          {/* Grouped Notifications */}
          <div className="space-y-4 max-h-[600px] overflow-y-auto">
            {notifications.length > 0 ? (
              notifications.map((group) => {
                const groupId = group.printer_id || 'system';
                const isExpanded = expandedGroups.has(groupId);
                const criticalCount = group.alerts.filter(a => a.severity === 'Critical').length;
                const warningCount = group.alerts.filter(a => a.severity === 'Warning').length;

                return (
                  <div key={groupId} className="border rounded-lg overflow-hidden">
                    {/* Group Header */}
                    <button
                      onClick={() => toggleGroup(groupId)}
                      className="w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 transition"
                    >
                    <div className="flex items-center space-x-3">
                        <Printer className="h-5 w-5 text-gray-600" />
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900">{group.printer_name}</h3>
                          <div className="flex items-center space-x-2 mt-1">
                            {criticalCount > 0 && (
                              <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">
                                {criticalCount} Critical
                              </span>
                            )}
                            {warningCount > 0 && (
                              <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full font-medium">
                                {warningCount} Warning
                              </span>
                            )}
                            <span className="text-xs text-gray-500">
                              {group.alerts.length} total
                            </span>
                          </div>
                        </div>
                        {isExpanded ? (
                          <ChevronUp className="h-5 w-5 text-gray-400" />
                        ) : (
                          <ChevronDown className="h-5 w-5 text-gray-400" />
                        )}
                      </div>
                    </button>

                    {/* Group Content */}
                    {isExpanded && (
                      <div className="divide-y divide-gray-100">
                        {group.alerts.map((alert) => {
                          const styles = getSeverityStyles(alert.severity);
                          return (
                            <div
                              key={alert.alert_id}
                              className={`p-4 ${styles.bg} border-l-4 ${styles.border}`}
                            >
                              <div className="flex items-start justify-between mb-2">
                                <div className="flex items-start space-x-3 flex-1">
                                  <div className={styles.icon}>
                                    {getAlertIcon(alert.alert_type)}
                                  </div>
                                  <div className="flex-1">
                                    <div className="flex items-center space-x-2 mb-1">
                                      <span className={`text-xs font-semibold px-2 py-0.5 rounded ${styles.badge}`}>
                                        {alert.severity.toUpperCase()}
                                      </span>
                                      <span className="text-xs text-gray-500">
                                        {formatTimestamp(alert.created_at)}
                                      </span>
                                    </div>
                                    <p className={`font-medium ${styles.text}`}>
                                      {alert.alert_message}
                                    </p>
                                    {alert.action_taken && (
                                      <p className="text-xs text-gray-600 mt-1 italic">
                                        Action taken: {alert.action_taken}
                                      </p>
                                    )}
                                  </div>
                                </div>
                              </div>

                              {/* Action Buttons */}
                              <div className="flex items-center space-x-2 mt-3">
                                {alert.severity === 'Critical' && !alert.fixed && (
                                  <button
                                    onClick={() => handleFix(alert.alert_id)}
                                    className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 transition"
                                  >
                                    <Wrench className="h-3 w-3" />
                                    <span>Fix</span>
                                  </button>
                                )}
                                
                                {(alert.severity === 'Warning' || alert.severity === 'Info') && !alert.acknowledged && (
                                  <button
                                    onClick={() => handleAcknowledge(alert.alert_id)}
                                    className="flex items-center space-x-1 px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 transition"
                                  >
                                    <Check className="h-3 w-3" />
                                    <span>Acknowledge</span>
                                  </button>
                                )}

                                <button
                                  onClick={() => handleMute(alert.alert_id)}
                                  className="flex items-center space-x-1 px-3 py-1 bg-gray-600 text-white rounded text-xs hover:bg-gray-700 transition"
                                >
                                  <VolumeX className="h-3 w-3" />
                                  <span>Mute 1h</span>
                                </button>

                                {alert.printer_id && (
                                  <button
                                    onClick={() => navigate(`/supervisor/printers`)}
                                    className="flex items-center space-x-1 px-3 py-1 bg-gray-100 text-gray-700 rounded text-xs hover:bg-gray-200 transition"
                                  >
                                    <Printer className="h-3 w-3" />
                                    <span>View Printer</span>
                                  </button>
                                )}

                                {alert.order_id && (
                                  <button
                                    onClick={() => navigate(`/supervisor/orders`)}
                                    className="flex items-center space-x-1 px-3 py-1 bg-gray-100 text-gray-700 rounded text-xs hover:bg-gray-200 transition"
                                  >
                                    <FileText className="h-3 w-3" />
                                    <span>View Order</span>
                                  </button>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="text-center py-12">
                <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">All Clear!</h3>
                <p className="text-gray-600">No notifications at the moment</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Add Printer Modal */}
      {showAddPrinter && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Add New Printer</h2>
              <button
                onClick={() => setShowAddPrinter(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="h-6 w-6" />
              </button>
            </div>

            <form onSubmit={handleAddPrinter}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Printer ID *
                  </label>
                  <input
                    type="text"
                    required
                    value={printerForm.printer_id}
                    onChange={(e) => setPrinterForm({...printerForm, printer_id: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., PRINTER-001"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Printer Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={printerForm.printer_name}
                    onChange={(e) => setPrinterForm({...printerForm, printer_name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., ColorJet Pro"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Printer Model *
                  </label>
                  <input
                    type="text"
                    required
                    value={printerForm.printer_model}
                    onChange={(e) => setPrinterForm({...printerForm, printer_model: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., HP LaserJet Pro M404"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Type
                    </label>
                    <select
                      value={printerForm.type}
                      onChange={(e) => setPrinterForm({...printerForm, type: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="Laser">Laser</option>
                      <option value="Inkjet">Inkjet</option>
                      <option value="Thermal">Thermal</option>
                      <option value="Dot Matrix">Dot Matrix</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Connection
                    </label>
                    <select
                      value={printerForm.connection_type}
                      onChange={(e) => setPrinterForm({...printerForm, connection_type: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="USB">USB</option>
                      <option value="WiFi">WiFi</option>
                      <option value="Ethernet">Ethernet</option>
                      <option value="Cloud Print">Cloud Print</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Paper Capacity *
                  </label>
                  <input
                    type="number"
                    required
                    min="1"
                    value={printerForm.paper_capacity}
                    onChange={(e) => setPrinterForm({...printerForm, paper_capacity: parseInt(e.target.value)})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="flex space-x-4">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={printerForm.color_support}
                      onChange={(e) => setPrinterForm({...printerForm, color_support: e.target.checked})}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">Color Support</span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={printerForm.duplex_support}
                      onChange={(e) => setPrinterForm({...printerForm, duplex_support: e.target.checked})}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">Duplex Printing</span>
                  </label>
                </div>
              </div>

              <div className="flex space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowAddPrinter(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingPrinter}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center"
                >
                  {creatingPrinter ? (
                    <>
                      <Loader className="animate-spin h-4 w-4 mr-2" />
                      Adding...
                    </>
                  ) : (
                    'Add Printer'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default SupervisorDashboard;