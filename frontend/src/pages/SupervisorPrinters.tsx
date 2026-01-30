import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Printer, 
  Search, 
  Filter, 
  MoreVertical, 
  Play, 
  Pause, 
  Wrench,
  AlertTriangle,
  Move,
  Trash2,
  Loader,
  Plus
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

interface Printer {
  printer_id: string;
  printer_name: string;
  printer_model: string;
  type: string;
  status: string;
  paper_available: number;
  paper_capacity: number;
  ink_toner_level: {
    black: number;
    cyan?: number;
    magenta?: number;
    yellow?: number;
  };
  color_support: boolean;
  duplex_support: boolean;
  connection_type: string;
  pages_printed_today: number;
  total_pages_printed: number;
  queue_length: number;
  current_job_id: string | null;
  temperature: number;
  humidity: number;
  last_maintenance: string | null;
  last_jam_timestamp: string | null;
  capabilities: {
    supported_sizes: string[];
    color: boolean;
    duplex: boolean;
  };
}

interface PrinterStatusUpdate {
  status: 'Online' | 'Offline' | 'Maintenance' | 'Error';
  reason?: string;
}

interface QueueOverrideRequest {
  target_printer_id: string;
  reason: string;
}

const SupervisorPrinters: React.FC = () => {
  const [printers, setPrinters] = useState<Printer[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [showQueueOverride, setShowQueueOverride] = useState(false);
  const [showAddPrinter, setShowAddPrinter] = useState(false);
  const [selectedPrinter, setSelectedPrinter] = useState<Printer | null>(null);
  const [statusForm, setStatusForm] = useState<PrinterStatusUpdate>({
    status: 'Online',
    reason: ''
  });
  const [overrideForm, setOverrideForm] = useState<QueueOverrideRequest>({
    target_printer_id: '',
    reason: ''
  });
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
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchPrinters();
  }, []);

  const fetchPrinters = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/supervisor/printers/detailed`);
      setPrinters(response.data.printers);
    } catch (error) {
      console.error('Failed to fetch printers:', error);
    } finally {
      setLoading(false);
    }
  };

  const updatePrinterStatus = async (printerId: string) => {
    setActionLoading(`status-${printerId}`);
    try {
      await axios.post(
        `${API_BASE_URL}/supervisor/printers/${printerId}/status`,
        statusForm
      );
      setShowStatusModal(false);
      setSelectedPrinter(null);
      setStatusForm({ status: 'Online', reason: '' });
      fetchPrinters();
    } catch (error: any) {
      console.error('Failed to update printer status:', error);
      alert(error.response?.data?.detail || 'Failed to update printer status');
    } finally {
      setActionLoading(null);
    }
  };

  const overrideQueue = async (printerId: string) => {
    setActionLoading(`override-${printerId}`);
    try {
      await axios.post(
        `${API_BASE_URL}/supervisor/printers/${printerId}/queue-override`,
        overrideForm
      );
      setShowQueueOverride(false);
      setSelectedPrinter(null);
      setOverrideForm({ target_printer_id: '', reason: '' });
      fetchPrinters();
    } catch (error: any) {
      console.error('Failed to override queue:', error);
      alert(error.response?.data?.detail || 'Failed to override queue');
    } finally {
      setActionLoading(null);
    }
  };

  const deletePrinter = async (printerId: string) => {
    if (!confirm('Are you sure you want to delete this printer? This action cannot be undone.')) {
      return;
    }

    setActionLoading(`delete-${printerId}`);
    try {
      await axios.delete(`${API_BASE_URL}/supervisor/printers/${printerId}`);
      fetchPrinters();
    } catch (error: any) {
      console.error('Failed to delete printer:', error);
      alert(error.response?.data?.detail || 'Failed to delete printer');
    } finally {
      setActionLoading(null);
    }
  };

  const handleAddPrinter = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading('add-printer');
    try {
      await axios.post(`${API_BASE_URL}/supervisor/printers`, printerForm);
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
      fetchPrinters();
    } catch (error: any) {
      console.error('Failed to create printer:', error);
      alert(error.response?.data?.detail || 'Failed to create printer');
    } finally {
      setActionLoading(null);
    }
  };

  const openStatusModal = (printer: Printer, status: PrinterStatusUpdate['status']) => {
    setSelectedPrinter(printer);
    setStatusForm({ status, reason: '' });
    setShowStatusModal(true);
  };

  const openQueueOverride = (printer: Printer) => {
    setSelectedPrinter(printer);
    setOverrideForm({ target_printer_id: '', reason: '' });
    setShowQueueOverride(true);
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'online': return 'bg-green-100 text-green-800 border-green-200';
      case 'offline': return 'bg-red-100 text-red-800 border-red-200';
      case 'maintenance': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'error': return 'bg-red-100 text-red-800 border-red-200';
      case 'idle': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'busy': return 'bg-orange-100 text-orange-800 border-orange-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getInkLevelColor = (level: number) => {
    if (level > 70) return 'bg-green-500';
    if (level > 30) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const filteredPrinters = printers.filter(printer => {
    const matchesSearch = printer.printer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         printer.printer_id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || printer.status.toLowerCase() === statusFilter.toLowerCase();
    return matchesSearch && matchesStatus;
  });

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
          <h1 className="text-3xl font-bold text-gray-900">Printer Management</h1>
          <p className="text-gray-600 mt-2">Monitor and manage all printers in your store</p>
        </div>
        <button
          onClick={() => setShowAddPrinter(true)}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          <Plus className="h-4 w-4" />
          <span>Add Printer</span>
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
                placeholder="Search printers..."
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
            <option value="online">Online</option>
            <option value="offline">Offline</option>
            <option value="maintenance">Maintenance</option>
            <option value="error">Error</option>
            <option value="idle">Idle</option>
            <option value="busy">Busy</option>
          </select>
        </div>
      </div>

      {/* Printers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {filteredPrinters.map((printer) => (
          <div key={printer.printer_id} className="bg-white rounded-lg shadow border border-gray-200">
            {/* Header */}
            <div className="p-6 border-b border-gray-200">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <h3 className="font-bold text-lg text-gray-900">{printer.printer_name}</h3>
                  <p className="text-sm text-gray-600">{printer.printer_model}</p>
                  <p className="text-xs text-gray-400">{printer.printer_id}</p>
                </div>
                <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(printer.status)}`}>
                  {printer.status}
                </span>
              </div>
            </div>

            {/* Stats */}
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Paper:</span>
                  <span className="ml-2 font-medium">
                    {printer.paper_available}/{printer.paper_capacity}
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Queue:</span>
                  <span className="ml-2 font-medium">
                    {printer.queue_length} jobs
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Type:</span>
                  <span className="ml-2 font-medium">
                    {printer.type}
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Pages Today:</span>
                  <span className="ml-2 font-medium">
                    {printer.pages_printed_today}
                  </span>
                </div>
              </div>

              {/* Ink Levels */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Black Toner:</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-16 bg-gray-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${getInkLevelColor(printer.ink_toner_level.black)}`}
                        style={{ width: `${printer.ink_toner_level.black}%` }}
                      ></div>
                    </div>
                    <span className="text-xs w-8">{printer.ink_toner_level.black}%</span>
                  </div>
                </div>
                {printer.color_support && (
                  <>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Cyan:</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-gray-200 rounded-full h-2">
                          <div 
                            className="h-2 rounded-full bg-cyan-500"
                            style={{ width: `${printer.ink_toner_level.cyan}%` }}
                          ></div>
                        </div>
                        <span className="text-xs w-8">{printer.ink_toner_level.cyan}%</span>
                      </div>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Magenta:</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-gray-200 rounded-full h-2">
                          <div 
                            className="h-2 rounded-full bg-pink-500"
                            style={{ width: `${printer.ink_toner_level.magenta}%` }}
                          ></div>
                        </div>
                        <span className="text-xs w-8">{printer.ink_toner_level.magenta}%</span>
                      </div>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Yellow:</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-gray-200 rounded-full h-2">
                          <div 
                            className="h-2 rounded-full bg-yellow-500"
                            style={{ width: `${printer.ink_toner_level.yellow}%` }}
                          ></div>
                        </div>
                        <span className="text-xs w-8">{printer.ink_toner_level.yellow}%</span>
                      </div>
                    </div>
                  </>
                )}
              </div>

              {/* Last Jam */}
              {printer.last_jam_timestamp && (
                <div className="flex items-center space-x-2 text-sm text-red-600">
                  <AlertTriangle className="h-4 w-4" />
                  <span>Last jam: {new Date(printer.last_jam_timestamp).toLocaleString()}</span>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="p-4 bg-gray-50 border-t border-gray-200">
              <div className="flex space-x-2">
                <button
                  onClick={() => openStatusModal(printer, 'Online')}
                  disabled={actionLoading === `status-${printer.printer_id}`}
                  className="flex-1 flex items-center justify-center space-x-1 px-3 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition disabled:opacity-50"
                >
                  {actionLoading === `status-${printer.printer_id}` ? (
                    <Loader className="h-3 w-3 animate-spin" />
                  ) : (
                    <Play className="h-3 w-3" />
                  )}
                  <span>Online</span>
                </button>

                <button
                  onClick={() => openStatusModal(printer, 'Offline')}
                  disabled={actionLoading === `status-${printer.printer_id}`}
                  className="flex-1 flex items-center justify-center space-x-1 px-3 py-2 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition disabled:opacity-50"
                >
                  {actionLoading === `status-${printer.printer_id}` ? (
                    <Loader className="h-3 w-3 animate-spin" />
                  ) : (
                    <Pause className="h-3 w-3" />
                  )}
                  <span>Offline</span>
                </button>

                <button
                  onClick={() => openStatusModal(printer, 'Maintenance')}
                  disabled={actionLoading === `status-${printer.printer_id}`}
                  className="flex-1 flex items-center justify-center space-x-1 px-3 py-2 bg-yellow-600 text-white text-sm rounded hover:bg-yellow-700 transition disabled:opacity-50"
                >
                  {actionLoading === `status-${printer.printer_id}` ? (
                    <Loader className="h-3 w-3 animate-spin" />
                  ) : (
                    <Wrench className="h-3 w-3" />
                  )}
                  <span>Maintenance</span>
                </button>

                <div className="relative">
                  <button className="p-2 text-gray-400 hover:text-gray-600 transition">
                    <MoreVertical className="h-4 w-4" />
                  </button>
                  <div className="absolute right-0 mt-1 w-48 bg-white rounded-md shadow-lg border border-gray-200 z-10 hidden group-hover:block">
                    <div className="py-1">
                      <button
                        onClick={() => openQueueOverride(printer)}
                        className="flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full text-left"
                      >
                        <Move className="h-4 w-4" />
                        <span>Move Queue</span>
                      </button>
                      <button
                        onClick={() => deletePrinter(printer.printer_id)}
                        disabled={actionLoading === `delete-${printer.printer_id}`}
                        className="flex items-center space-x-2 px-4 py-2 text-sm text-red-700 hover:bg-red-50 w-full text-left disabled:opacity-50"
                      >
                        {actionLoading === `delete-${printer.printer_id}` ? (
                          <Loader className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                        <span>Delete</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredPrinters.length === 0 && (
        <div className="text-center py-12">
          <Printer className="h-12 w-12 mx-auto text-gray-400 mb-4" />
          <p className="text-gray-500">No printers found</p>
        </div>
      )}

      {/* Status Update Modal */}
      {showStatusModal && selectedPrinter && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-bold mb-4">Update Printer Status</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status
                </label>
                <div className="text-sm text-gray-900 bg-gray-100 p-2 rounded">
                  {statusForm.status}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason
                </label>
                <textarea
                  value={statusForm.reason}
                  onChange={(e) => setStatusForm({...statusForm, reason: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="Enter reason for status change..."
                />
              </div>
            </div>
            <div className="flex space-x-3 mt-6">
              <button
                onClick={() => setShowStatusModal(false)}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={() => updatePrinterStatus(selectedPrinter.printer_id)}
                disabled={actionLoading === `status-${selectedPrinter.printer_id}`}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:opacity-50"
              >
                {actionLoading === `status-${selectedPrinter.printer_id}` ? 'Updating...' : 'Update Status'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Queue Override Modal */}
      {showQueueOverride && selectedPrinter && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-bold mb-4">Move Printer Queue</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Move from: {selectedPrinter.printer_name}
                </label>
                <p className="text-sm text-gray-600">
                  Queue length: {selectedPrinter.queue_length} jobs
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Target Printer
                </label>
                <select
                  value={overrideForm.target_printer_id}
                  onChange={(e) => setOverrideForm({...overrideForm, target_printer_id: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select target printer</option>
                  {printers
                    .filter(p => p.printer_id !== selectedPrinter.printer_id && p.status === 'Online')
                    .map(printer => (
                      <option key={printer.printer_id} value={printer.printer_id}>
                        {printer.printer_name} ({printer.queue_length} jobs)
                      </option>
                    ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason
                </label>
                <textarea
                  value={overrideForm.reason}
                  onChange={(e) => setOverrideForm({...overrideForm, reason: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="Enter reason for moving queue..."
                  required
                />
              </div>
            </div>
            <div className="flex space-x-3 mt-6">
              <button
                onClick={() => setShowQueueOverride(false)}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={() => overrideQueue(selectedPrinter.printer_id)}
                disabled={!overrideForm.target_printer_id || !overrideForm.reason || actionLoading === `override-${selectedPrinter.printer_id}`}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:opacity-50"
              >
                {actionLoading === `override-${selectedPrinter.printer_id}` ? 'Moving...' : 'Move Queue'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Printer Modal */}
      {showAddPrinter && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">Add New Printer</h2>
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
                  disabled={actionLoading === 'add-printer'}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:opacity-50"
                >
                  {actionLoading === 'add-printer' ? 'Adding...' : 'Add Printer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default SupervisorPrinters;