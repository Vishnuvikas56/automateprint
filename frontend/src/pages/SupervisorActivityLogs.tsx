import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Calendar,
  FileText,
  Printer,
  User,
  Settings,
  Package,
  AlertTriangle,
  Clock,
  Filter
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

interface ActivityLog {
  log_id: number;
  action: string;
  entity_type: string;
  entity_id: string;
  old_value: any;
  new_value: any;
  timestamp: string;
  ip_address: string | null;
}

const SupervisorActivityLogs: React.FC = () => {
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeFilter, setTimeFilter] = useState<'today' | 'week' | 'month' | 'all'>('today');
  const [entityTypeFilter, setEntityTypeFilter] = useState('all');

  useEffect(() => {
    fetchActivityLogs();
  }, [timeFilter, entityTypeFilter]);

  const fetchActivityLogs = async () => {
    try {
      setLoading(true);
      
      // Calculate date range based on time filter
      const now = new Date();
      let startDate = '';

      switch (timeFilter) {
        case 'today':
          startDate = now.toISOString().split('T')[0];
          break;
        case 'week':
          const weekAgo = new Date(now);
          weekAgo.setDate(now.getDate() - 7);
          startDate = weekAgo.toISOString().split('T')[0];
          break;
        case 'month':
          const monthAgo = new Date(now);
          monthAgo.setMonth(now.getMonth() - 1);
          startDate = monthAgo.toISOString().split('T')[0];
          break;
        case 'all':
          // No date filter for 'all'
          break;
      }

      const response = await axios.get(`${API_BASE_URL}/supervisor/activity-logs`, {
        params: {
          entity_type: entityTypeFilter !== 'all' ? entityTypeFilter : undefined,
          start_date: startDate || undefined,
          limit: timeFilter === 'today' ? 50 : 100
        }
      });
      setLogs(response.data.logs);
    } catch (error) {
      console.error('Failed to fetch activity logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const getActionIcon = (entityType: string) => {
    switch (entityType) {
      case 'printer': return <Printer className="h-5 w-5" />;
      case 'order': return <Package className="h-5 w-5" />;
      case 'profile': return <User className="h-5 w-5" />;
      case 'alert': return <AlertTriangle className="h-5 w-5" />;
      case 'query': return <FileText className="h-5 w-5" />;
      default: return <Settings className="h-5 w-5" />;
    }
  };

  const getActionColor = (action: string) => {
    if (action.includes('create') || action.includes('add')) return 'text-green-600 bg-green-50 border-green-200';
    if (action.includes('update') || action.includes('change')) return 'text-blue-600 bg-blue-50 border-blue-200';
    if (action.includes('delete') || action.includes('remove')) return 'text-red-600 bg-red-50 border-red-200';
    if (action.includes('resolve') || action.includes('complete')) return 'text-purple-600 bg-purple-50 border-purple-200';
    return 'text-gray-600 bg-gray-50 border-gray-200';
  };

  const formatActionText = (action: string): string => {
    const actionMap: { [key: string]: string } = {
      'printer_status_change': 'Printer Status Changed',
      'order_delivered': 'Order Delivered',
      'binding_completed': 'Binding Completed',
      'alert_acknowledged': 'Alert Acknowledged',
      'alert_fixed': 'Alert Fixed',
      'alert_muted': 'Alert Muted',
      'query_created': 'Query Created',
      'profile_updated': 'Profile Updated',
      'password_changed': 'Password Changed',
      'job_cancelled': 'Job Cancelled',
      'printer_paused': 'Printer Paused',
      'printer_resumed': 'Printer Resumed',
      'test_print': 'Test Print',
      'queue_override': 'Queue Override'
    };

    return actionMap[action] || action.replace(/_/g, ' ').toUpperCase();
  };

  const getEntityDisplayName = (entityType: string, entityId: string) => {
    switch (entityType) {
      case 'printer': return `Printer: ${entityId}`;
      case 'order': return `Order: ${entityId}`;
      case 'alert': return `Alert: #${entityId}`;
      case 'query': return `Query: ${entityId}`;
      case 'profile': return 'User Profile';
      default: return `${entityType}: ${entityId}`;
    }
  };

  const formatDetails = (log: ActivityLog): { title: string; description: string } => {
    const { action, entity_type, old_value, new_value } = log;

    switch (action) {
      case 'printer_status_change':
        const oldStatus = old_value?.status || 'Unknown';
        const newStatus = new_value?.status || 'Unknown';
        return {
          title: `Printer status updated`,
          description: `Changed from ${oldStatus} to ${newStatus}${new_value?.reason ? `. Reason: ${new_value.reason}` : ''}`
        };

      case 'order_delivered':
        return {
          title: 'Order marked as delivered',
          description: new_value?.notes || 'Order handed over to customer'
        };

      case 'binding_completed':
        return {
          title: 'Binding work completed',
          description: new_value?.notes || 'Document binding finished'
        };

      case 'alert_acknowledged':
        return {
          title: 'Alert acknowledged',
          description: new_value?.action_taken || 'Alert reviewed and acknowledged'
        };

      case 'alert_fixed':
        return {
          title: 'Critical alert resolved',
          description: `Action taken: ${new_value?.action_taken || 'Issue fixed'}${new_value?.notes ? `. Notes: ${new_value.notes}` : ''}`
        };

      case 'alert_muted':
        return {
          title: 'Alert muted',
          description: `Muted until ${new_value?.muted_until ? new Date(new_value.muted_until).toLocaleString() : 'specified time'}`
        };

      case 'profile_updated':
        return {
          title: 'Profile updated',
          description: 'User profile information modified'
        };

      case 'password_changed':
        return {
          title: 'Password changed',
          description: 'Account password updated successfully'
        };

      case 'job_cancelled':
        return {
          title: 'Print job cancelled',
          description: `Job ${new_value?.cancelled_job_id || ''} was cancelled`
        };

      case 'printer_paused':
        return {
          title: 'Printer paused',
          description: 'Printer operation temporarily stopped'
        };

      case 'printer_resumed':
        return {
          title: 'Printer resumed',
          description: 'Printer operation restarted'
        };

      case 'test_print':
        return {
          title: 'Test print executed',
          description: 'Printer test page was printed'
        };

      case 'queue_override':
        return {
          title: 'Queue management',
          description: `Jobs moved to ${new_value?.printer_id || 'another printer'}${new_value?.reason ? `. Reason: ${new_value.reason}` : ''}`
        };

      default:
        return {
          title: formatActionText(action),
          description: 'Action performed on the system'
        };
    }
  };

  const getTimeFilterLabel = (filter: string) => {
    switch (filter) {
      case 'today': return 'Today';
      case 'week': return 'This Week';
      case 'month': return 'This Month';
      case 'all': return 'All Time';
      default: return filter;
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
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Activity Logs</h1>
        <p className="text-gray-600 mt-2">Track all supervisor actions and system changes</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Clock className="h-5 w-5 text-gray-400" />
              <span className="text-sm font-medium text-gray-700">Time Range:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {(['today', 'week', 'month', 'all'] as const).map((filter) => (
                <button
                  key={filter}
                  onClick={() => setTimeFilter(filter)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    timeFilter === filter
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {getTimeFilterLabel(filter)}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Filter className="h-5 w-5 text-gray-400" />
            <select
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={entityTypeFilter}
              onChange={(e) => setEntityTypeFilter(e.target.value)}
            >
              <option value="all">All Entities</option>
              <option value="printer">Printers</option>
              <option value="order">Orders</option>
              <option value="alert">Alerts</option>
              <option value="query">Queries</option>
              <option value="profile">Profile</option>
            </select>
          </div>
        </div>
      </div>

      {/* Activity Logs */}
      <div className="space-y-4">
        {logs.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <FileText className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-500">No activity logs found for the selected period</p>
            <p className="text-sm text-gray-400 mt-1">Try selecting a different time range or entity type</p>
          </div>
        ) : (
          logs.map((log) => {
            const details = formatDetails(log);
            return (
              <div
                key={log.log_id}
                className="bg-white rounded-lg shadow border border-gray-200 p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4 flex-1">
                    <div className="flex items-center justify-center w-10 h-10 bg-gray-100 rounded-lg">
                      {getActionIcon(log.entity_type)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-3 mb-2">
                        <span className={`px-3 py-1 text-sm font-medium rounded-full border ${getActionColor(log.action)}`}>
                          {details.title}
                        </span>
                        <span className="text-sm text-gray-500">
                          {getEntityDisplayName(log.entity_type, log.entity_id)}
                        </span>
                      </div>
                      
                      <p className="text-gray-700 mb-3">
                        {details.description}
                      </p>
                      
                      <div className="flex items-center space-x-4 text-sm text-gray-500">
                        <div className="flex items-center space-x-1">
                          <Calendar className="h-4 w-4" />
                          <span>{new Date(log.timestamp).toLocaleDateString()}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Clock className="h-4 w-4" />
                          <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                        </div>
                        {log.ip_address && (
                          <span className="text-xs bg-gray-100 px-2 py-1 rounded">IP: {log.ip_address}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Summary */}
      <div className="mt-8 p-6 bg-gray-50 rounded-lg">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Activity Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{logs.length}</div>
            <div className="text-sm text-gray-600">Total Actions</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {logs.filter(l => l.entity_type === 'printer').length}
            </div>
            <div className="text-sm text-gray-600">Printer Actions</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {logs.filter(l => l.entity_type === 'order').length}
            </div>
            <div className="text-sm text-gray-600">Order Actions</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              {logs.filter(l => l.entity_type === 'alert').length}
            </div>
            <div className="text-sm text-gray-600">Alert Actions</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SupervisorActivityLogs;