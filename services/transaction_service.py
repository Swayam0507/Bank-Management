"""
Transaction Service Module
Handles deposits, withdrawals, transfers, and passbook generation
"""

import os
from datetime import datetime

from database.db_manager import db_execute
from config.settings import MIN_BALANCE, PENALTY_AMOUNT, BANK_NAME, BRANCH_ADDRESS, PHONE_NO, IFSC_CODE


# ============================================
# PASSBOOK MANAGEMENT
# ============================================

def write_passbook(account_number, name, account_type, balance, transaction_type, amount):
    """
    Writes transaction to local passbook file
    Creates passbook file with bank details if it doesn't exist
    
    Args:
        account_number (int): Account number
        name (str): Account holder name
        account_type (str): Account type (Savings/Current)
        balance (float): Balance after transaction
        transaction_type (str): Type of transaction
        amount (float): Transaction amount
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    passbook_file = f"{account_number}_passbook.txt"
    
    # Create passbook with header if it doesn't exist
    if not os.path.exists(passbook_file):
        with open(passbook_file, "w") as f:
            f.write("========== Bank Details ==========\n")
            f.write(f"Bank Name: {BANK_NAME}\n")
            f.write(f"Branch Address: {BRANCH_ADDRESS}\n")
            f.write(f"Phone No.: {PHONE_NO}\n")
            f.write(f"IFSC Code: {IFSC_CODE}\n")
            f.write("========== Account Details ==========\n")
            f.write(f"Account Holder Name: {name}\n")
            f.write(f"Account Number: {account_number}\n")
            f.write(f"Account Type: {account_type}\n")
            f.write("\n")
            f.write("Transaction History:\n")
            f.write("=" * 50 + "\n")
    
    # Append transaction
    with open(passbook_file, "a") as f:
        f.write(f"{timestamp} | {transaction_type} | Amount: {amount} | Balance: {balance}\n")


# ============================================
# TRANSACTION RECORDING
# ============================================

def record_transaction(account_number, transaction_type, amount):
    """
    Records a transaction in the database
    
    Args:
        account_number (int): Account number
        transaction_type (str): Type of transaction
        amount (float): Transaction amount
    """
    db_execute(
        "INSERT INTO transactions (account_number, type, amount) VALUES (%s, %s, %s)",
        (account_number, transaction_type, amount),
    )


# ============================================
# DEPOSIT OPERATION
# ============================================

def process_deposit(account_number, name, account_type, current_balance, amount):
    """
    Processes a deposit transaction
    
    Args:
        account_number (int): Account number
        name (str): Account holder name
        account_type (str): Account type
        current_balance (float): Current balance
        amount (float): Deposit amount
    
    Returns:
        tuple: (success: bool, message: str, new_balance: float)
    """
    if amount <= 0:
        return False, "Please enter a positive amount.", current_balance
    
    new_balance = current_balance + amount
    
    # Update balance in database
    db_execute("UPDATE accounts SET balance=%s WHERE account_number=%s", (new_balance, account_number))
    
    # Record transaction
    record_transaction(account_number, "Deposit", amount)
    
    # Update passbook
    write_passbook(account_number, name, account_type, new_balance, "Deposit", amount)
    
    return True, f"Deposited INR {amount:,.2f}. New balance: INR {new_balance:,.2f}", new_balance


# ============================================
# WITHDRAWAL OPERATION
# ============================================

def process_withdrawal(account_number, name, account_type, current_balance, amount):
    """
    Processes a withdrawal transaction
    Applies penalty if balance falls below minimum
    
    Args:
        account_number (int): Account number
        name (str): Account holder name
        account_type (str): Account type
        current_balance (float): Current balance
        amount (float): Withdrawal amount
    
    Returns:
        tuple: (success: bool, message: str, new_balance: float, penalty_applied: bool)
    """
    if amount <= 0:
        return False, "Please enter a positive amount.", current_balance, False
    
    if amount > current_balance:
        return False, "Insufficient balance.", current_balance, False
    
    new_balance = current_balance - amount
    penalty_applied = False
    
    # Check minimum balance and apply penalty if needed
    if new_balance < MIN_BALANCE:
        new_balance -= PENALTY_AMOUNT
        record_transaction(account_number, "Penalty", PENALTY_AMOUNT)
        penalty_applied = True
    
    # Update balance in database
    db_execute("UPDATE accounts SET balance=%s WHERE account_number=%s", (new_balance, account_number))
    
    # Record withdrawal transaction
    record_transaction(account_number, "Withdrawal", amount)
    
    # Update passbook
    write_passbook(account_number, name, account_type, new_balance, "Withdrawal", amount)
    
    message = f"Withdrawn INR {amount:,.2f}. New balance: INR {new_balance:,.2f}"
    if penalty_applied:
        message = f"Penalty of INR {PENALTY_AMOUNT} imposed for falling below minimum balance. " + message
    
    return True, message, new_balance, penalty_applied


# ============================================
# TRANSFER OPERATION
# ============================================

def process_transfer(sender_account, sender_name, sender_account_type, sender_balance, recipient_account, amount):
    """
    Processes a transfer between accounts
    
    Args:
        sender_account (int): Sender account number
        sender_name (str): Sender name
        sender_account_type (str): Sender account type
        sender_balance (float): Sender current balance
        recipient_account (int): Recipient account number
        amount (float): Transfer amount
    
    Returns:
        tuple: (success: bool, message: str, new_balance: float, recipient_name: str or None)
    """
    if amount <= 0:
        return False, "Please enter a positive amount.", sender_balance, None
    
    # Check recipient exists
    recipient = db_execute(
        "SELECT name, balance FROM accounts WHERE account_number=%s",
        (recipient_account,),
        fetchone=True,
    )
    
    if not recipient:
        return False, "Recipient account not found.", sender_balance, None
    
    recipient_name = recipient[0]
    
    # Check sender balance
    if amount > sender_balance:
        return False, "Insufficient funds.", sender_balance, recipient_name
    
    # Update sender balance
    new_balance = sender_balance - amount
    db_execute("UPDATE accounts SET balance=%s WHERE account_number=%s", (new_balance, sender_account))
    
    # Update recipient balance
    db_execute("UPDATE accounts SET balance=balance+%s WHERE account_number=%s", (amount, recipient_account))
    
    # Record transactions for both accounts
    record_transaction(sender_account, "Transfer Sent", amount)
    record_transaction(recipient_account, "Transfer Received", amount)
    
    # Update sender passbook
    write_passbook(sender_account, sender_name, sender_account_type, new_balance, "Transfer Sent", amount)
    
    return True, f"Transferred INR {amount:,.2f} to account {recipient_account}.", new_balance, recipient_name


# ============================================
# TRANSACTION HISTORY
# ============================================

def get_mini_statement(account_number, limit=5):
    """
    Retrieves recent transactions for mini statement
    
    Args:
        account_number (int): Account number
        limit (int): Number of transactions to retrieve
    
    Returns:
        list: List of transaction tuples (type, amount, timestamp)
    """
    transactions = db_execute(
        f"SELECT type, amount, timestamp FROM transactions WHERE account_number=%s ORDER BY id DESC LIMIT {limit}",
        (account_number,),
        fetchall=True,
    )
    return transactions or []


def get_transaction_summary(account_number):
    """
    Retrieves transaction summary grouped by type
    
    Args:
        account_number (int): Account number
    
    Returns:
        dict: Dictionary mapping transaction type to total amount
    """
    transactions = db_execute(
        "SELECT type, SUM(amount) FROM transactions WHERE account_number=%s GROUP BY type",
        (account_number,),
        fetchall=True,
    )
    
    if not transactions:
        return {}
    
    return {t[0]: float(t[1] or 0) for t in transactions}
