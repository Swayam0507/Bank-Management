"""
Loan Service Module
Handles loan applications, EMI calculations, and loan repayments
"""

from database.db_manager import db_execute
from config.settings import LOAN_TYPES


# ============================================
# LOAN APPLICATION
# ============================================

def apply_loan(account_number, loan_type_key, loan_amount, tenure):
    """
    Applies for a loan
    
    Args:
        account_number (int): Account number
        loan_type_key (str): Loan type selection key
        loan_amount (float): Requested loan amount
        tenure (int): Loan tenure in months
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if loan_amount <= 0:
        return False, "Loan amount must be greater than 0."
    
    loan_type, interest_rate = LOAN_TYPES[loan_type_key]
    
    db_execute(
        """INSERT INTO loans (account_number, loan_type, loan_amount, interest_rate, tenure, remaining_amount)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (account_number, loan_type, loan_amount, interest_rate, tenure, loan_amount),
    )
    
    return True, f"{loan_type} of INR {loan_amount:,.2f} applied successfully."


# ============================================
# LOAN RETRIEVAL
# ============================================

def get_loans_with_emi(account_number):
    """
    Retrieves all loans for an account with calculated EMI
    
    Args:
        account_number (int): Account number
    
    Returns:
        list: List of loan dictionaries with EMI details
    """
    loans = db_execute(
        """SELECT loan_id, loan_type, loan_amount, interest_rate, tenure, remaining_amount, status
           FROM loans WHERE account_number=%s""",
        (account_number,),
        fetchall=True,
    )
    
    if not loans:
        return []
    
    loans_with_emi = []
    for loan in loans:
        loan_id, loan_type, loan_amount, interest_rate, tenure, remaining_amount, status = loan
        monthly_emi = calculate_emi(loan_amount, interest_rate, tenure)
        
        loans_with_emi.append({
            "loan_id": loan_id,
            "loan_type": loan_type,
            "loan_amount": loan_amount,
            "interest_rate": interest_rate,
            "tenure": tenure,
            "remaining_amount": remaining_amount,
            "status": status,
            "monthly_emi": monthly_emi
        })
    
    return loans_with_emi


def get_active_loans(account_number):
    """
    Retrieves only active loans for an account
    
    Args:
        account_number (int): Account number
    
    Returns:
        list: List of active loan tuples
    """
    loans = db_execute(
        """SELECT loan_id, loan_type, loan_amount, interest_rate, tenure, remaining_amount
           FROM loans WHERE account_number=%s AND status='Active'""",
        (account_number,),
        fetchall=True,
    )
    return loans or []


# ============================================
# EMI CALCULATION
# ============================================

def calculate_emi(loan_amount, interest_rate, tenure):
    """
    Calculates EMI using standard amortization formula
    
    Formula: EMI = [P × r × (1 + r)^n] / [(1 + r)^n - 1]
    Where:
        P = Principal loan amount
        r = Monthly interest rate (annual rate / 12 / 100)
        n = Tenure in months
    
    Args:
        loan_amount (float): Principal loan amount
        interest_rate (float): Annual interest rate (%)
        tenure (int): Loan tenure in months
    
    Returns:
        float: Monthly EMI amount
    """
    if tenure == 0:
        return 0
    monthly_interest_rate = (interest_rate / 12) / 100
    if monthly_interest_rate == 0:
        return loan_amount / tenure
    emi = (
        loan_amount * monthly_interest_rate * (1 + monthly_interest_rate) ** tenure
    ) / ((1 + monthly_interest_rate) ** tenure - 1)
    return emi


def calculate_emi_details(loan_amount, interest_rate, tenure):
    """
    Calculates detailed EMI breakdown including total interest and total payment
    
    Args:
        loan_amount (float): Principal loan amount
        interest_rate (float): Annual interest rate (%)
        tenure (int): Loan tenure in months
    
    Returns:
        dict: Dictionary containing:
            - monthly_emi: Monthly EMI amount
            - total_amount: Total amount to be paid
            - total_interest: Total interest amount
            - principal_amount: Original loan amount
    """
    monthly_emi = calculate_emi(loan_amount, interest_rate, tenure)
    total_amount = monthly_emi * tenure
    total_interest = total_amount - loan_amount
    
    return {
        "monthly_emi": monthly_emi,
        "total_amount": total_amount,
        "total_interest": total_interest,
        "principal_amount": loan_amount
    }


# ============================================
# LOAN REPAYMENT
# ============================================

def repay_loan_emi(loan_id, loan_amount, interest_rate, tenure, remaining_amount, current_balance):
    """
    Processes loan EMI payment
    
    Args:
        loan_id (int): Loan ID
        loan_amount (float): Original loan amount
        interest_rate (float): Annual interest rate
        tenure (int): Loan tenure in months
        remaining_amount (float): Remaining loan amount
        current_balance (float): Current account balance
    
    Returns:
        tuple: (success: bool, message: str, emi: float, new_remaining: float, loan_paid: bool)
    """
    # Calculate EMI
    emi = calculate_emi(loan_amount, interest_rate, tenure)
    
    if emi <= 0:
        return False, "Invalid EMI calculated. Please contact support.", 0, remaining_amount, False
    
    # Check balance
    if current_balance < emi:
        return False, "Insufficient balance to pay EMI.", 0, remaining_amount, False
    
    # Calculate new remaining amount
    if remaining_amount - emi < 0:
        emi = remaining_amount
        new_remaining = 0
    else:
        new_remaining = remaining_amount - emi
    
    # Update loan in database
    db_execute("UPDATE loans SET remaining_amount=%s WHERE loan_id=%s", (new_remaining, loan_id))
    
    # Mark as paid if fully repaid
    loan_paid = False
    if new_remaining <= 0:
        db_execute("UPDATE loans SET status='Paid' WHERE loan_id=%s", (loan_id,))
        loan_paid = True
    
    return True, f"EMI of INR {emi:,.2f} paid successfully.", emi, new_remaining, loan_paid
