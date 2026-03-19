"""
Account Service Module
Handles account operations like balance updates, interest calculation, and PIN changes
"""

from datetime import datetime
import streamlit as st

from database.db_manager import db_execute
from services.email_service import send_email, build_otp_email
from services.transaction_service import record_transaction, write_passbook
from services.auth_service import (
    generate_otp, is_otp_expired, reset_pin_otp_state
)
from config.settings import OTP_TTL_SECONDS, OTP_MAX_ATTEMPTS


# ============================================
# ACCOUNT DATA RETRIEVAL
# ============================================

def refresh_account(account_number):
    """
    Fetches latest account data from database
    
    Args:
        account_number (int): Account number
    
    Returns:
        tuple: Account data (account_number, name, email, balance, account_type, interest_rate, last_interest_date)
    """
    return db_execute(
        """SELECT account_number, name, email, balance, account_type, interest_rate, last_interest_date 
           FROM accounts WHERE account_number=%s""",
        (account_number,),
        fetchone=True,
    )


def update_balance(new_balance, account_number):
    """
    Updates account balance in database and session
    
    Args:
        new_balance (float): New balance amount
        account_number (int): Account number
    """
    db_execute("UPDATE accounts SET balance=%s WHERE account_number=%s", (new_balance, account_number))
    st.session_state.account["balance"] = new_balance


# ============================================
# INTEREST CALCULATION
# ============================================

def calculate_and_apply_interest(account_number, name, account_type, balance, interest_rate):
    """
    Calculates and applies monthly interest to savings account
    Interest can only be applied once per month
    
    Args:
        account_number (int): Account number
        name (str): Account holder name
        account_type (str): Account type
        balance (float): Current balance
        interest_rate (float): Annual interest rate (%)
    
    Returns:
        tuple: (success: bool, message: str, interest: float, new_balance: float)
    """
    # Check if interest already applied this month
    last_date = db_execute(
        "SELECT last_interest_date FROM accounts WHERE account_number=%s",
        (account_number,),
        fetchone=True,
    )
    
    today = datetime.now().date()
    if last_date and last_date[0]:
        if last_date[0].year == today.year and last_date[0].month == today.month:
            return False, "Interest has already been applied this month.", 0, balance
    
    # Calculate monthly interest
    monthly_rate = interest_rate / 12
    interest = (balance * monthly_rate) / 100
    new_balance = balance + interest
    
    # Update balance
    update_balance(new_balance, account_number)
    
    # Record transaction
    record_transaction(account_number, "Interest", interest)
    
    # Update last interest date
    db_execute(
        "UPDATE accounts SET last_interest_date=%s WHERE account_number=%s",
        (today, account_number),
    )
    
    # Update passbook
    write_passbook(account_number, name, account_type, new_balance, "Interest", interest)
    
    # Update session
    st.session_state.account["last_interest_date"] = today
    
    return True, f"Interest of INR {interest:,.2f} added. New balance: INR {new_balance:,.2f}", interest, new_balance


# ============================================
# PIN CHANGE OPERATIONS
# ============================================

def send_pin_change_otp(email):
    """
    Sends OTP for PIN change
    
    Args:
        email (str): Account email address
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if not email:
        return False, "No email found for this account. Please contact support."
    
    otp = generate_otp()
    st.session_state.pin_otp = otp
    st.session_state.pin_otp_expires = datetime.now().timestamp() + OTP_TTL_SECONDS
    st.session_state.pin_otp_attempts = 0
    
    try:
        send_email(email, "Your PIN Change OTP", build_otp_email(otp, "PIN Change OTP"))
        return True, "OTP sent to your email."
    except Exception:
        reset_pin_otp_state()
        return False, "Failed to send OTP email. Please try again."


def verify_and_change_pin(account_number, new_pin, otp_input):
    """
    Verifies OTP and changes account PIN
    
    Args:
        account_number (int): Account number
        new_pin (str): New 4-digit PIN
        otp_input (str): OTP entered by user
    
    Returns:
        tuple: (success: bool, message: str)
    """
    # Check if OTP was sent
    if not st.session_state.pin_otp:
        return False, "Please send OTP first."
    
    # Check expiration
    if is_otp_expired(st.session_state.pin_otp_expires):
        reset_pin_otp_state()
        return False, "OTP expired. Please request a new OTP."
    
    # Check attempts
    st.session_state.pin_otp_attempts += 1
    if st.session_state.pin_otp_attempts > OTP_MAX_ATTEMPTS:
        reset_pin_otp_state()
        return False, "Too many invalid attempts. Please request a new OTP."
    
    # Verify OTP
    if not otp_input.isdigit() or int(otp_input) != st.session_state.pin_otp:
        return False, "Invalid OTP."
    
    # Validate new PIN
    if not new_pin.isdigit() or len(new_pin) != 4:
        return False, "Enter a valid 4-digit PIN."
    
    # Store PIN as string to preserve leading zeros
    pin_str = new_pin.zfill(4)  # Ensure 4 digits with leading zeros
    
    # Update PIN
    db_execute(
        "UPDATE accounts SET pin=%s WHERE account_number=%s",
        (pin_str, account_number),
    )
    
    reset_pin_otp_state()
    return True, "PIN changed successfully."


# ============================================
# UTILITY FUNCTIONS
# ============================================

def format_amount(value):
    """
    Formats large amounts with K/M/B suffixes
    
    Args:
        value (float): Amount to format
    
    Returns:
        str: Formatted amount string
    """
    if value >= 1_000_000_000:
        return f"{value/1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value/1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value/1_000:.2f}K"
    return f"{value:.2f}"


def format_currency(value):
    """
    Formats amount as Indian currency
    
    Args:
        value (float): Amount to format
    
    Returns:
        str: Formatted currency string
    """
    return f"INR {value:,.2f}"
