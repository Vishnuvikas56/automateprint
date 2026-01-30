import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { FileText, Loader, CheckCircle, XCircle, Upload, X, Plus, Eye, EyeOff } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

// Razorpay types
declare global {
  interface Window {
    Razorpay: any;
  }
}

interface Store {
  store_id: string;
  store_name: string;
  pricing_info: {
    bw_per_page: number;
    color_per_page: number;
    thick_per_page: number;
    glossy_per_page: number;
    poster_per_page: number;
    binding: number;
  };
}

interface UploadedFile {
  filename: string;
  file_url: string;
  size_mb: number;
  page_count?: number;
}

interface PrintOption {
  type: 'bw' | 'color' | 'glossy' | 'thick';
  pages: string;
  enabled: boolean;
}

interface DocumentConfig {
  fileIndex: number;
  printMode: 'bw' | 'color' | 'glossy' | 'thick' | 'mixed';
  pageNumbers: string;
  excludePages: boolean;
  mixedOptions: PrintOption[];
  binding: boolean;
  orientation: 'portrait' | 'landscape';
  copies: number;
}

interface CostBreakdown {
  filename: string;
  printDetails: string;
  copies: number;
  pages: number;
  subtotal: number;
  binding: number;
  total: number;
}

// Updated prices to match backend pricing
const PRICES = {
  bw: 2,
  color: 10,
  glossy: 15,
  thick: 15,
  binding: 10,
};

// Paper type mapping
const PAPER_TYPES = {
  bw: 'A4',
  color: 'A4',
  glossy: 'Glossy',
  thick: 'Thick'
};

export default function NewOrder() {
  const navigate = useNavigate();
  const [stores, setStores] = useState<Store[]>([]);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [previewFile, setPreviewFile] = useState<string | null>(null);

  const [costBreakdown, setCostBreakdown] = useState<CostBreakdown[]>([]);
  const [totalCost, setTotalCost] = useState(0);

  const [formData, setFormData] = useState({
    store_id: 'STORE001',
    priority: 5,
  });

  const [configs, setConfigs] = useState<DocumentConfig[]>([]);

  // Get auth token
  const getAuthToken = () => {
    return localStorage.getItem('token') || '';
  };

  useEffect(() => {
    fetchStores();
    // Load Razorpay script
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    document.body.appendChild(script);
  }, []);

  useEffect(() => {
    if (uploadedFiles.length > configs.length) {
      const newConfigsToAdd = uploadedFiles.slice(configs.length).map((_, relativeIndex) => ({
        fileIndex: configs.length + relativeIndex,
        printMode: 'bw' as const,
        pageNumbers: '',
        excludePages: false,
        mixedOptions: [
          { type: 'bw' as const, pages: '', enabled: false },
          { type: 'color' as const, pages: '', enabled: false },
          { type: 'glossy' as const, pages: '', enabled: false },
          { type: 'thick' as const, pages: '', enabled: false },
        ],
        binding: false,
        orientation: 'portrait' as const,
        copies: 1,
      }));
      setConfigs([...configs, ...newConfigsToAdd]);
    }
  }, [uploadedFiles.length]);

  useEffect(() => {
    if (uploadedFiles.length > 0 && configs.length === uploadedFiles.length) {
      const { breakdown, total } = calculateCostBreakdown();
      setCostBreakdown(breakdown);
      setTotalCost(total);
    }
  }, [configs, uploadedFiles]);

  const fetchStores = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/stores`, {
        headers: { Authorization: `Bearer ${getAuthToken()}` }
      });
      setStores(response.data.stores);
    } catch (error) {
      console.error('Failed to fetch stores:', error);
    }
  };

  const validatePageNumbers = (pageStr: string, totalPages?: number): { valid: boolean; error?: string } => {
    if (!pageStr.trim()) return { valid: true };

    if (/,,/.test(pageStr)) {
      return { valid: false, error: 'Invalid format: consecutive commas found' };
    }
    if (/^[,\s]+$/.test(pageStr)) {
      return { valid: false, error: 'Invalid format: only commas and spaces' };
    }

    const parts = pageStr.split(',').map(p => p.trim()).filter(p => p.length > 0);
    
    if (parts.length === 0) {
      return { valid: false, error: 'Invalid format: no valid page numbers found' };
    }

    for (const part of parts) {
      if (part.includes('-')) {
        const rangeParts = part.split('-');
        if (rangeParts.length !== 2) {
          return { valid: false, error: `Invalid range format: ${part}` };
        }
        const [start, end] = rangeParts.map(p => p.trim());
        if (!start || !end || isNaN(Number(start)) || isNaN(Number(end))) {
          return { valid: false, error: `Invalid range format: ${part}` };
        }
        const startNum = parseInt(start);
        const endNum = parseInt(end);
        if (startNum > endNum) {
          return { valid: false, error: `Invalid range: ${part} (start > end)` };
        }
        if (totalPages && (startNum > totalPages || endNum > totalPages)) {
          return { valid: false, error: `Page numbers exceed PDF page count (${totalPages})` };
        }
        if (startNum < 1) {
          return { valid: false, error: `Page numbers must be at least 1` };
        }
      } else {
        if (isNaN(Number(part))) {
          return { valid: false, error: `Invalid page number: ${part}` };
        }
        if (totalPages && parseInt(part) > totalPages) {
          return { valid: false, error: `Page ${part} exceeds PDF page count (${totalPages})` };
        }
        if (parseInt(part) < 1) {
          return { valid: false, error: `Page numbers must be at least 1` };
        }
      }
    }
    
    return { valid: true };
  };

  const calculatePagesFromString = (pageStr: string, totalPages: number): number[] => {
    if (!pageStr.trim()) return Array.from({ length: totalPages }, (_, i) => i + 1);
    
    const pages = new Set<number>();
    const parts = pageStr.split(',').map(p => p.trim()).filter(p => p.length > 0);
    
    for (const part of parts) {
      if (part.includes('-')) {
        const [start, end] = part.split('-').map(p => parseInt(p.trim()));
        for (let i = start; i <= end; i++) {
          if (i <= totalPages) pages.add(i);
        }
      } else {
        const pageNum = parseInt(part);
        if (pageNum <= totalPages) pages.add(pageNum);
      }
    }
    
    return Array.from(pages).sort((a, b) => a - b);
  };

  const calculateCostBreakdown = (): { breakdown: CostBreakdown[]; total: number } => {
    const breakdown: CostBreakdown[] = [];
    let grandTotal = 0;

    configs.forEach((config, index) => {
      const file = uploadedFiles[index];
      
      if (!file || !file.page_count) {
        return;
      }

      let subtotal = 0;
      let printDetails = '';
      let totalPages = 0;

      if (config.printMode === 'mixed') {
        const enabledOptions = config.mixedOptions.filter(opt => opt.enabled);
        
        let accountedPages = new Set<number>();

        enabledOptions.forEach(opt => {
          if (opt.pages.trim()) {
            const pages = calculatePagesFromString(opt.pages, file.page_count!);
            pages.forEach(p => accountedPages.add(p));
            const cost = pages.length * PRICES[opt.type] * config.copies;
            subtotal += cost;
            totalPages += pages.length;
          }
        });

        const blankOption = enabledOptions.find(opt => !opt.pages.trim());
        if (blankOption) {
          const remainingPageCount = file.page_count - accountedPages.size;
          const cost = remainingPageCount * PRICES[blankOption.type] * config.copies;
          subtotal += cost;
          totalPages += remainingPageCount;
        }

        const optionsList = enabledOptions.map(opt => {
          if (opt.pages.trim()) {
            return `${opt.type.toUpperCase()}: ${opt.pages}`;
          } else {
            return `${opt.type.toUpperCase()}: remaining pages`;
          }
        });
        printDetails = `Mixed (${optionsList.join(', ')})`;
      } else {
        let pagesToPrint: number[];
        
        if (config.pageNumbers.trim()) {
          pagesToPrint = calculatePagesFromString(config.pageNumbers, file.page_count);
          
          if (config.excludePages) {
            const allPages = Array.from({ length: file.page_count }, (_, i) => i + 1);
            pagesToPrint = allPages.filter(p => !pagesToPrint.includes(p));
          }
        } else {
          pagesToPrint = Array.from({ length: file.page_count }, (_, i) => i + 1);
        }

        totalPages = pagesToPrint.length;
        const cost = pagesToPrint.length * PRICES[config.printMode] * config.copies;
        subtotal += cost;

        if (config.pageNumbers.trim()) {
          printDetails = `${config.printMode.toUpperCase()}${config.excludePages ? ' (exclude)' : ''}: ${config.pageNumbers}`;
        } else {
          printDetails = `${config.printMode.toUpperCase()}: All pages`;
        }
      }

      const bindingCost = config.binding ? PRICES.binding : 0;
      const itemTotal = subtotal + bindingCost;

      breakdown.push({
        filename: file.filename,
        printDetails,
        copies: config.copies,
        pages: totalPages,
        subtotal,
        binding: bindingCost,
        total: itemTotal,
      });

      grandTotal += itemTotal;
    });

    return { breakdown, total: grandTotal };
  };

  // In the buildOrderPayload function, add total_page_count:
  const buildOrderPayload = (config: DocumentConfig, file: UploadedFile) => {
    const pages: { [key: string]: { pages: string; exclude: boolean } } = {};
    const printType: { [key: string]: string } = {};
    const paperType: { [key: string]: string } = {};

    if (config.printMode === 'mixed') {
      const enabledOptions = config.mixedOptions.filter(opt => opt.enabled);
      
      enabledOptions.forEach(opt => {
        pages[opt.type] = {
          pages: opt.pages,
          exclude: false
        };
        printType[opt.type] = PAPER_TYPES[opt.type];
        paperType[opt.type] = PAPER_TYPES[opt.type];
      });
    } else {
      pages[config.printMode] = {
        pages: config.pageNumbers,
        exclude: config.excludePages
      };
      printType[config.printMode] = PAPER_TYPES[config.printMode];
      paperType[config.printMode] = PAPER_TYPES[config.printMode];
    }

    return {
      pages,
      print_type: printType,
      paper_type: paperType,
      mixed: config.printMode === 'mixed',
      copies: config.copies,
      priority: formData.priority,
      duplex: false,
      collate: true,
      store_id: formData.store_id,
      file_url: file.file_url,
      extras: {
        binding: config.binding
      },
      total_page_count: file.page_count // ← ADD THIS LINE
    };
  };

  const handleFilesSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);

    if (files.length === 0) return;
    
    if (files.length + uploadedFiles.length > 10) {
      setUploadError(`Maximum 10 files allowed. You already have ${uploadedFiles.length} files.`);
      return;
    }

    for (const file of files) {
      if (file.type !== 'application/pdf') {
        setUploadError(`${file.name} is not a PDF file`);
        return;
      }
      const fileSizeMB = file.size / (1024 * 1024);
      if (fileSizeMB > 30) {
        setUploadError(`${file.name} is too large (${fileSizeMB.toFixed(2)}MB, max 30MB)`);
        return;
      }
    }

    setUploadingFile(true);
    setUploadError('');

    try {
      const uploadFormData = new FormData();
      files.forEach((file) => uploadFormData.append('files', file));

      const response = await axios.post(
        `${API_BASE_URL}/orders/upload-bulk-files`, 
        uploadFormData, 
        {
          headers: { 
            'Content-Type': 'multipart/form-data',
            'Authorization': `Bearer ${getAuthToken()}`
          }
        }
      );

      setUploadedFiles(prev => [...prev, ...response.data.files]);
      
      if (response.data.failed_count > 0) {
        setUploadError(`${response.data.failed_count} file(s) failed to upload`);
      }
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploadingFile(false);
    }
  };

  const handleRemoveFile = (index: number) => {
    setUploadedFiles(uploadedFiles.filter((_, i) => i !== index));
    setConfigs(configs.filter((_, i) => i !== index));
    if (previewFile === uploadedFiles[index].file_url) {
      setPreviewFile(null);
    }
  };

  const handlePreviewFile = (fileUrl: string) => {
    setPreviewFile(previewFile === fileUrl ? null : fileUrl);
  };

  const handleRazorpayPayment = (paymentData: any) => {
    const options = {
      key: paymentData.key_id,
      amount: paymentData.amount * 100,
      currency: paymentData.currency,
      order_id: paymentData.razorpay_order_id,
      name: 'Print Management System',
      description: paymentData.order_count > 1 
        ? `Bulk Order: ${paymentData.order_count} documents` 
        : `Order: ${paymentData.order_ids[0]}`,
      handler: async function (response: any) {
        try {
          const verifyResponse = await axios.post(
            `${API_BASE_URL}/orders/verify-payment`,
            {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            },
            {
              headers: { Authorization: `Bearer ${getAuthToken()}` }
            }
          );

          if (verifyResponse.data.success) {
            setSuccess(true);
            setLoading(false);
            
            verifyResponse.data.order_ids.forEach((orderId: string) => {
              connectToSSE(orderId);
            });
          } else {
            throw new Error('Payment verification failed');
          }
        } catch (err: any) {
          setError(err.response?.data?.detail || 'Payment verification failed');
          setLoading(false);
        }
      },
      prefill: {
        email: localStorage.getItem('user_email') || '',
        contact: localStorage.getItem('user_phone') || '',
      },
      theme: {
        color: '#2563eb'
      },
      modal: {
        ondismiss: function() {
          setLoading(false);
          setError('Payment cancelled');
        }
      }
    };

    const razorpay = new window.Razorpay(options);
    razorpay.open();
  };

  const connectToSSE = (orderId: string) => {
    const eventSource = new EventSource(
      `${API_BASE_URL}/orders/stream`,
      {
        withCredentials: false,
      }
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.event === 'order_update' && data.data.order_id === orderId) {
          console.log('Order update:', data.data);
          
          if (data.data.status === 'completed') {
            console.log('Order completed!');
            eventSource.close();
          } else if (data.data.status === 'failed') {
            console.log('Order failed:', data.data.message);
            eventSource.close();
          }
        }
      } catch (err) {
        console.error('SSE parsing error:', err);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      eventSource.close();
    };

    setTimeout(() => {
      eventSource.close();
    }, 300000);
  };

  const handleProceedToPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (uploadedFiles.length === 0) {
      setError('Please upload at least one PDF file');
      return;
    }

    // Validation
    let validationError = '';
    
    for (let i = 0; i < configs.length; i++) {
      const config = configs[i];
      const file = uploadedFiles[i];

      if (config.printMode === 'mixed') {
        const enabledOptions = config.mixedOptions.filter(opt => opt.enabled);
        if (enabledOptions.length === 0) {
          validationError = `${file.filename}: Please select at least one print option in mixed mode`;
          break;
        }

        const blankFieldCount = enabledOptions.filter(opt => !opt.pages.trim()).length;
        if (blankFieldCount > 1) {
          validationError = `${file.filename}: Only one option can have blank pages in mixed mode`;
          break;
        }

        for (const opt of enabledOptions) {
          if (opt.pages.trim()) {
            const validation = validatePageNumbers(opt.pages, file.page_count);
            if (!validation.valid) {
              validationError = `${file.filename}: ${validation.error}`;
              break;
            }
          }
        }
        if (validationError) break;
      } else {
        if (config.pageNumbers.trim()) {
          const validation = validatePageNumbers(config.pageNumbers, file.page_count);
          if (!validation.valid) {
            validationError = `${file.filename}: ${validation.error}`;
            break;
          }
        }
      }
    }

    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);

    try {
      // Build orders array in new format
      const orders = uploadedFiles.map((file, index) => {
        const config = configs[index];
        return buildOrderPayload(config, file);
      });

      // Create single payment for all orders
      const response = await axios.post(
        `${API_BASE_URL}/orders/create-payment`,
        { orders },
        {
          headers: { Authorization: `Bearer ${getAuthToken()}` }
        }
      );

      // Open Razorpay payment
      handleRazorpayPayment(response.data);

    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to create order(s)');
      setLoading(false);
    }
  };

  const renderDocumentConfig = (config: DocumentConfig, index: number) => (
    <div key={index} className="p-4 border border-gray-300 rounded-lg space-y-4">
      <div className="flex justify-between items-center">
        <h4 className="font-semibold text-gray-900">
          {uploadedFiles[index].filename}
          <span className="ml-2 text-sm text-gray-500">({uploadedFiles[index].page_count} pages)</span>
        </h4>
        <button
          type="button"
          onClick={() => handlePreviewFile(uploadedFiles[index].file_url)}
          className="flex items-center space-x-2 px-3 py-1 bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 transition-colors text-sm"
        >
          {previewFile === uploadedFiles[index].file_url ? (
            <>
              <EyeOff className="h-4 w-4" />
              <span>Hide</span>
            </>
          ) : (
            <>
              <Eye className="h-4 w-4" />
              <span>Preview</span>
            </>
          )}
        </button>
      </div>

      {previewFile === uploadedFiles[index].file_url && (
        <div className="border rounded-lg p-2 bg-gray-50">
          <iframe
            src={uploadedFiles[index].file_url}
            className="w-full h-96"
            title={`PDF Preview - ${uploadedFiles[index].filename}`}
          />
        </div>
      )}
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Print Mode</label>
        <select
          value={config.printMode}
          onChange={(e) => {
            const newConfigs = configs.map((cfg, idx) => 
              idx === index ? { ...cfg, printMode: e.target.value as any } : cfg
            );
            setConfigs(newConfigs);
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="bw">Black & White (₹2/page)</option>
          <option value="color">Color (₹10/page)</option>
          <option value="glossy">Glossy (₹15/page)</option>
          <option value="thick">Thick Paper (₹15/page)</option>
          <option value="mixed">Mixed Options</option>
        </select>
      </div>

      {config.printMode !== 'mixed' ? (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Page Numbers (Optional)</label>
          <input
            type="text"
            value={config.pageNumbers}
            onChange={(e) => {
              const newConfigs = configs.map((cfg, idx) => 
                idx === index ? { ...cfg, pageNumbers: e.target.value } : cfg
              );
              setConfigs(newConfigs);
            }}
            placeholder="e.g., 1-5, 8, 10-12"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">Leave blank to print all pages</p>
          
          {config.pageNumbers.trim() && (
            <div className="mt-2 flex items-center">
              <input
                type="checkbox"
                checked={config.excludePages}
                onChange={(e) => {
                  const newConfigs = configs.map((cfg, idx) => 
                    idx === index ? { ...cfg, excludePages: e.target.checked } : cfg
                  );
                  setConfigs(newConfigs);
                }}
                className="mr-2"
              />
              <label className="text-sm text-gray-700">Exclude these pages</label>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm font-medium text-gray-700">Select print options (Only one can be blank):</p>
          
          {config.mixedOptions.map((opt, optIdx) => (
            <div key={opt.type} className="flex items-start space-x-3">
              <input
                type="checkbox"
                checked={opt.enabled}
                onChange={(e) => {
                  const newConfigs = configs.map((cfg, idx) => {
                    if (idx === index) {
                      const newMixedOptions = cfg.mixedOptions.map((o, oIdx) => 
                        oIdx === optIdx ? { ...o, enabled: e.target.checked } : o
                      );
                      return { ...cfg, mixedOptions: newMixedOptions };
                    }
                    return cfg;
                  });
                  setConfigs(newConfigs);
                }}
                className="mt-1"
              />
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {opt.type.toUpperCase()} (₹{PRICES[opt.type]}/page)
                </label>
                <input
                  type="text"
                  value={opt.pages}
                  onChange={(e) => {
                    const newConfigs = configs.map((cfg, idx) => {
                      if (idx === index) {
                        const newMixedOptions = cfg.mixedOptions.map((o, oIdx) => 
                          oIdx === optIdx ? { ...o, pages: e.target.value } : o
                        );
                        return { ...cfg, mixedOptions: newMixedOptions };
                      }
                      return cfg;
                    });
                    setConfigs(newConfigs);
                  }}
                  placeholder="e.g., 1-5, 8 (or leave blank for remaining pages)"
                  disabled={!opt.enabled}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                />
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Copies</label>
          <input
            type="number"
            value={config.copies}
            onChange={(e) => {
              const newConfigs = configs.map((cfg, idx) => 
                idx === index ? { ...cfg, copies: parseInt(e.target.value) || 1 } : cfg
              );
              setConfigs(newConfigs);
            }}
            min="1"
            max="100"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Orientation</label>
          <select
            value={config.orientation}
            onChange={(e) => {
              const newConfigs = configs.map((cfg, idx) => 
                idx === index ? { ...cfg, orientation: e.target.value as any } : cfg
              );
              setConfigs(newConfigs);
            }}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="portrait">Portrait</option>
            <option value="landscape">Landscape</option>
          </select>
        </div>

        <div className="flex items-end">
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={config.binding}
              onChange={(e) => {
                const newConfigs = configs.map((cfg, idx) => 
                  idx === index ? { ...cfg, binding: e.target.checked } : cfg
                );
                setConfigs(newConfigs);
              }}
              className="w-4 h-4"
            />
            <span className="text-sm font-medium text-gray-700">Binding (₹10)</span>
          </label>
        </div>
      </div>
    </div>
  );

  if (success) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-20 text-center">
        <CheckCircle className="h-16 w-16 text-green-600 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          {uploadedFiles.length > 1 
            ? `${uploadedFiles.length} Orders Placed Successfully!` 
            : 'Order Placed Successfully!'}
        </h2>
        <p className="text-gray-600 mb-4">Your print job(s) are being processed...</p>
        <p className="text-sm text-gray-500 mb-6">You'll receive real-time updates on order status</p>
        <button
          onClick={() => navigate('/my-orders')}
          className="px-6 py-3 bg-blue-600 text-white rounded-md font-semibold hover:bg-blue-700"
        >
          View My Orders
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Create Print Order</h1>
        <p className="text-gray-600 mt-2">Upload up to 10 PDF files (max 30MB each)</p>
      </div>

      <form onSubmit={handleProceedToPayment} className="bg-white rounded-lg shadow p-6">
        <div className="mb-6 p-4 border-2 border-dashed border-gray-300 rounded-lg">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Upload PDFs - {uploadedFiles.length}/10 files
          </label>

          {uploadedFiles.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <label className="cursor-pointer flex flex-col items-center space-y-2">
                <Plus className="h-12 w-12 text-gray-400" />
                <span className="text-sm text-gray-600">Click to select PDFs</span>
                <input
                  type="file"
                  accept="application/pdf"
                  multiple
                  onChange={handleFilesSelect}
                  className="hidden"
                  disabled={uploadingFile}
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
                      <p className="text-xs text-gray-600">
                        {file.size_mb} MB • {file.page_count} pages
                      </p>
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
              
              {uploadedFiles.length < 10 && (
                <label className="cursor-pointer block text-center py-2 text-blue-600 hover:text-blue-800">
                  <Plus className="h-5 w-5 inline mr-2" />
                  Add more files ({uploadedFiles.length}/10)
                  <input
                    type="file"
                    accept="application/pdf"
                    multiple
                    onChange={handleFilesSelect}
                    className="hidden"
                    disabled={uploadingFile}
                  />
                </label>
              )}
            </div>
          )}

          {uploadingFile && (
            <div className="mt-2 text-center">
              <Loader className="animate-spin h-6 w-6 mx-auto text-blue-600" />
              <p className="text-sm text-gray-600 mt-2">Uploading files...</p>
            </div>
          )}

          {uploadError && (
            <div className="mt-2 p-2 bg-red-100 text-red-700 text-sm rounded">{uploadError}</div>
          )}
        </div>

        {uploadedFiles.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Print Configuration</h3>
            <div className="space-y-6">
              {configs.map((config, index) => renderDocumentConfig(config, index))}
            </div>
          </div>
        )}

        {/* Cost Breakdown Section */}
        {uploadedFiles.length > 0 && costBreakdown.length > 0 && (
          <div className="mb-6 p-4 border border-gray-300 rounded-lg bg-gray-50">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost Breakdown</h3>
            <div className="space-y-4">
              {costBreakdown.map((item, index) => (
                <div key={index} className="border rounded-lg p-4 bg-white">
                  <h4 className="font-semibold text-gray-900 mb-2">{item.filename}</h4>
                  <div className="text-sm text-gray-600 space-y-1">
                    <p><strong>Print:</strong> {item.printDetails}</p>
                    <p><strong>Copies:</strong> {item.copies}</p>
                    <p><strong>Pages to print:</strong> {item.pages}</p>
                  </div>
                  <div className="mt-3 pt-3 border-t border-gray-200 text-sm">
                    <div className="flex justify-between">
                      <span>Print cost:</span>
                      <span>₹{item.subtotal.toFixed(2)}</span>
                    </div>
                    {item.binding > 0 && (
                      <div className="flex justify-between text-gray-600">
                        <span>Binding:</span>
                        <span>₹{item.binding.toFixed(2)}</span>
                      </div>
                    )}
                    <div className="flex justify-between font-semibold text-gray-900 mt-2 pt-2 border-t">
                      <span>Subtotal:</span>
                      <span>₹{item.total.toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              ))}

              <div className="border-t-2 border-gray-300 pt-4 mt-4">
                <div className="flex justify-between items-center text-xl font-bold text-gray-900">
                  <span>Total Amount:</span>
                  <span className="text-2xl text-blue-600">₹{totalCost.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
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
            <label className="block text-sm font-medium text-gray-700 mb-2">Priority</label>
            <select
              value={formData.priority}
              onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="1">Urgent (Priority 1)</option>
              <option value="2">High (Priority 2)</option>
              <option value="5">Normal (Priority 5)</option>
              <option value="8">Low (Priority 8)</option>
              <option value="10">Very Low (Priority 10)</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-100 text-red-700 rounded-lg border border-red-300">
            <div className="flex items-center">
              <XCircle className="h-5 w-5 mr-2" />
              <span className="font-medium">Error:</span>
            </div>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}

        <div className="flex space-x-4">
          <button
            type="submit"
            disabled={loading || uploadingFile || uploadedFiles.length === 0}
            className="flex-1 py-3 bg-blue-600 text-white rounded-md font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center"
          >
            {loading ? (
              <>
                <Loader className="animate-spin h-5 w-5 mr-2" />
                Processing...
              </>
            ) : (
              'Proceed to Payment'
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
}