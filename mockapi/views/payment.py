from django.http import JsonResponse
from datetime import datetime
import random

# Mock payment scenarios
MOCK_PAYMENT_SCENARIOS = {
    # Always successful payments (by national number)
    "1231231230": {"status": "success", "reason": None},
    "1231231231": {"status": "success", "reason": None},

    # Always failed payments (by national number)
    "1231231232": {"status": "failed", "reason": "Insufficient funds"},
    "1231231233": {"status": "failed", "reason": "Card expired"},

    # Special test cases (by amount)
    "special_amounts": {
        100.00: {"status": "success", "reason": None},
        999.99: {"status": "failed", "reason": "Transaction limit exceeded"},
        0.01: {"status": "failed", "reason": "Amount too small"},
        10000.00: {"status": "failed", "reason": "Daily limit exceeded"}
    }
}

# Mock payment methods
PAYMENT_METHODS = {
    "CARD": "Credit/Debit Card",
    "BANK": "Bank Transfer",
    "WALLET": "Digital Wallet"
}

def process_payment(request):
    """
    Mock payment processing endpoint
    Expected POST data:
    - national_number: string
    - amount: float
    - payment_method: string (CARD, BANK, WALLET)
    - description: string (optional)
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)

    # Get parameters from request
    national_number = request.POST.get('national_number')
    amount = request.POST.get('amount')
    payment_method = request.POST.get('payment_method', 'CARD')
    description = request.POST.get('description', 'Payment')

    # Validate required fields
    if not national_number or not amount:
        return JsonResponse({
            "error": "Missing required fields",
            "required": ["national_number", "amount"]
        }, status=400)

    # Validate amount
    try:
        amount = float(amount)
        if amount <= 0:
            return JsonResponse({
                "error": "Invalid amount",
                "message": "Amount must be greater than 0"
            }, status=400)
    except (ValueError, TypeError):
        return JsonResponse({
            "error": "Invalid amount format"
        }, status=400)

    # Validate payment method
    if payment_method not in PAYMENT_METHODS:
        return JsonResponse({
            "error": "Invalid payment method",
            "valid_methods": list(PAYMENT_METHODS.keys())
        }, status=400)

    # Check if user exists
    from mockapi.views.beneficiary_info import MOCK_USERS  # Import from your existing module
    if national_number not in MOCK_USERS:
        return JsonResponse({
            "error": "User not found",
            "national_number": national_number
        }, status=404)

    # Generate transaction ID
    transaction_id = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"

    # Determine payment result
    result = None

    # Check if national number has a predetermined result
    if national_number in MOCK_PAYMENT_SCENARIOS:
        result = MOCK_PAYMENT_SCENARIOS[national_number]
    # Check if amount has a predetermined result
    elif amount in MOCK_PAYMENT_SCENARIOS["special_amounts"]:
        result = MOCK_PAYMENT_SCENARIOS["special_amounts"][amount]
    else:
        # Random success/failure (80% success rate)
        if random.random() < 0.8:
            result = {"status": "success", "reason": None}
        else:
            # Random failure reasons
            failure_reasons = [
                "Network error",
                "Bank declined transaction",
                "Invalid card details",
                "Fraud detection triggered",
                "Service temporarily unavailable"
            ]
            result = {"status": "failed", "reason": random.choice(failure_reasons)}

    # Build response
    response_data = {
        "transaction_id": transaction_id,
        "national_number": national_number,
        "amount": amount,
        "currency": "JOD",
        "payment_method": payment_method,
        "payment_method_display": PAYMENT_METHODS[payment_method],
        "description": description,
        "status": result["status"],
        "timestamp": datetime.now().isoformat(),
        "user_name": f"{MOCK_USERS[national_number]['first_name_enu']} {MOCK_USERS[national_number]['last_name_enu']}"
    }

    # Add failure reason if applicable
    if result["status"] == "failed":
        response_data["error_message"] = result["reason"]
        response_data["error_code"] = f"ERR_{random.randint(1000, 9999)}"
    else:
        # Add success details
        response_data["authorization_code"] = f"AUTH{random.randint(100000, 999999)}"
        response_data["receipt_url"] = f"/receipts/{transaction_id}"

    # Return appropriate status code
    status_code = 200 if result["status"] == "success" else 402

    return JsonResponse(response_data, status=status_code)


def check_payment_status(request, transaction_id):
    """
    Mock endpoint to check payment status by transaction ID
    """
    # For demo purposes, we'll generate a consistent status based on the transaction ID
    if not transaction_id.startswith("TXN"):
        return JsonResponse({"error": "Invalid transaction ID format"}, status=400)

    # Extract the random number from the end of transaction ID
    try:
        random_part = int(transaction_id[-4:])
        is_success = random_part % 2 == 0  # Even numbers are successful
    except:
        is_success = True

    response_data = {
        "transaction_id": transaction_id,
        "status": "success" if is_success else "failed",
        "checked_at": datetime.now().isoformat()
    }

    if not is_success:
        response_data["error_message"] = "Transaction failed during processing"
        response_data["error_code"] = "ERR_5001"

    return JsonResponse(response_data)


# URLs configuration (add to your urls.py)
"""
from django.urls import path
from . import views

urlpatterns = [
    path('api/users/<str:national_number>/', views.get_user_info, name='get_user_info'),
    path('api/payment/process/', views.process_payment, name='process_payment'),
    path('api/payment/status/<str:transaction_id>/', views.check_payment_status, name='check_payment_status'),
]
"""