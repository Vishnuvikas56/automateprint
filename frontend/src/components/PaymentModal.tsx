import React, { useEffect } from 'react';
import { X, CreditCard } from 'lucide-react';

interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  orderDetails: {
    order_id: string;
    razorpay_order_id: string;
    amount: number;
    currency: string;
    key_id: string;
  } | null;
  onPaymentSuccess: (paymentData: any) => void;
  onPaymentFailure: (error: any) => void;
}

// Extend Window interface for Razorpay
declare global {
  interface Window {
    Razorpay: any;
  }
}

const PaymentModal: React.FC<PaymentModalProps> = ({
  isOpen,
  onClose,
  orderDetails,
  onPaymentSuccess,
  onPaymentFailure,
}) => {
  useEffect(() => {
    // Load Razorpay script
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, []);

  const handlePayment = () => {
    if (!orderDetails || !window.Razorpay) {
      alert('Payment gateway not loaded. Please refresh and try again.');
      return;
    }

    const options = {
      key: orderDetails.key_id,
      amount: orderDetails.amount * 100, // Convert to paise
      currency: orderDetails.currency,
      name: 'SmartPrint',
      description: `Print Order ${orderDetails.order_id}`,
      order_id: orderDetails.razorpay_order_id,
      handler: function (response: any) {
        // Payment successful
        onPaymentSuccess({
          razorpay_order_id: response.razorpay_order_id,
          razorpay_payment_id: response.razorpay_payment_id,
          razorpay_signature: response.razorpay_signature,
        });
      },
      prefill: {
        name: '',
        email: '',
        contact: '',
      },
      theme: {
        color: '#2563eb', // Blue-600
      },
      modal: {
        ondismiss: function () {
          onPaymentFailure({ error: 'Payment cancelled by user' });
        },
      },
    };

    const razorpay = new window.Razorpay(options);
    
    razorpay.on('payment.failed', function (response: any) {
      onPaymentFailure({
        error: response.error.description,
        code: response.error.code,
        meta: response.error.meta,
      });
    });

    razorpay.open();
  };

  if (!isOpen || !orderDetails) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        >
          <X className="h-6 w-6" />
        </button>

        <div className="text-center mb-6">
          <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
            <CreditCard className="h-8 w-8 text-blue-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Complete Payment</h2>
          <p className="text-gray-600 mt-2">Order #{orderDetails.order_id}</p>
        </div>

        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <div className="flex justify-between items-center">
            <span className="text-gray-600">Amount to Pay:</span>
            <span className="text-2xl font-bold text-gray-900">
              ₹{orderDetails.amount.toFixed(2)}
            </span>
          </div>
        </div>

        <button
          onClick={handlePayment}
          className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition flex items-center justify-center space-x-2"
        >
          <CreditCard className="h-5 w-5" />
          <span>Proceed to Payment</span>
        </button>

        <p className="text-xs text-gray-500 text-center mt-4">
          Powered by Razorpay • Secure Payment Gateway
        </p>
      </div>
    </div>
  );
};

export default PaymentModal;