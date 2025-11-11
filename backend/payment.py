"""
Razorpay payment integration utilities
"""

import razorpay
import hmac
import hashlib
from typing import Dict, Optional
import logging
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=".env")
logger = logging.getLogger(__name__)

# Environment variables - SET THESE IN YOUR .env FILE
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def create_razorpay_order(amount: float, order_id: str, currency: str = "INR") -> Dict:
    """
    Create Razorpay order
    
    Args:
        amount: Amount in rupees (will be converted to paise)
        order_id: Internal order ID
        currency: Currency code (default INR)
    
    Returns:
        Dict with razorpay_order_id and other details
    """
    try:
        # Convert rupees to paise (smallest currency unit)
        amount_paise = int(amount * 100)
        
        order_data = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": order_id,
            "notes": {
                "order_id": order_id
            }
        }
        
        razorpay_order = razorpay_client.order.create(data=order_data)
        logger.info(f"Razorpay order created: {razorpay_order['id']} for order {order_id}")
        
        return {
            "razorpay_order_id": razorpay_order["id"],
            "amount": amount,
            "currency": currency,
            "status": razorpay_order["status"]
        }
        
    except Exception as e:
        logger.error(f"Failed to create Razorpay order: {e}")
        raise Exception(f"Payment gateway error: {str(e)}")


def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str
) -> bool:
    """
    Verify Razorpay payment signature
    
    Args:
        razorpay_order_id: Razorpay order ID
        razorpay_payment_id: Razorpay payment ID
        razorpay_signature: Signature from frontend
    
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Create signature string
        message = f"{razorpay_order_id}|{razorpay_payment_id}"
        
        # Generate expected signature
        generated_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        is_valid = hmac.compare_digest(generated_signature, razorpay_signature)
        
        if is_valid:
            logger.info(f"Payment signature verified for payment {razorpay_payment_id}")
        else:
            logger.warning(f"Invalid payment signature for payment {razorpay_payment_id}")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def get_payment_details(razorpay_payment_id: str) -> Optional[Dict]:
    """
    Fetch payment details from Razorpay
    
    Args:
        razorpay_payment_id: Razorpay payment ID
    
    Returns:
        Payment details dict or None
    """
    try:
        payment = razorpay_client.payment.fetch(razorpay_payment_id)
        return payment
    except Exception as e:
        logger.error(f"Failed to fetch payment details: {e}")
        return None


def refund_payment(razorpay_payment_id: str, amount: Optional[int] = None) -> Dict:
    """
    Initiate refund for a payment
    
    Args:
        razorpay_payment_id: Razorpay payment ID
        amount: Amount in paise (None for full refund)
    
    Returns:
        Refund details dict
    """
    try:
        refund_data = {}
        if amount:
            refund_data["amount"] = amount
        
        refund = razorpay_client.payment.refund(razorpay_payment_id, refund_data)
        logger.info(f"Refund initiated for payment {razorpay_payment_id}")
        return refund
        
    except Exception as e:
        logger.error(f"Refund failed: {e}")
        raise Exception(f"Refund error: {str(e)}")