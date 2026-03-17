from celery import shared_task

@shared_task
def process_pending_payments():
    """Process pending payment transactions"""
    from .models import Transaction
    
    pending_transactions = Transaction.objects.filter(status='pending')
    
    for transaction in pending_transactions:
        # Check payment status with Razorpay
        pass
    
    return f"Processed {pending_transactions.count()} pending transactions"

@shared_task
def distribute_earnings(transaction_id):
    """Distribute earnings after successful payment"""
    from .models import Transaction, Wallet
    
    try:
        transaction = Transaction.objects.get(id=transaction_id)
        
        if transaction.status == 'completed':
            # Calculate platform commission and earner amount
            platform_amount = transaction.amount * 0.30
            earner_amount = transaction.amount * 0.70
            
            # Credit to earner's wallet
            wallet, created = Wallet.objects.get_or_create(user=transaction.earner)
            wallet.balance += earner_amount
            wallet.save()
            
            return f"Distributed {earner_amount} to {transaction.earner.email}"
    except Transaction.DoesNotExist:
        return "Transaction not found"
