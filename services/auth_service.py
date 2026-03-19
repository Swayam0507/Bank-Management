"""
Authentication Service Module
Handles OTP generation, user registration, login, and session management
"""

import random
from datetime import datetime
import streamlit as st

from database.db_manager import db_execute
from services.email_service import send_email, build_otp_email, build_welcome_email
from config.settings import (
    SESSION_TIMEOUT_MINUTES, OTP_TTL_SECONDS, OTP_MAX_ATTEMPTS,
    DEFAULT_ACCOUNT_TYPE, DEFAULT_INTEREST_RATE
)


# ============================================
# OTP GENERATION
# ============================================

def generate_otp():
    """
    Generates a random 4-digit OTP
    
    Returns:
        int: 4-digit OTP
    """
    return random.randint(1000, 9999)


# ============================================
# ACCOUNT NUMBER GENERATION
# ============================================

def generate_unique_account_number():
    """
    Generates a unique 11-digit account number
    Ensures no collision with existing accounts
    
    Returns:
        int: Unique account number
    """
    while True:
        account_number = random.randint(10000000000, 99999999999)
        existing = db_execute(
            "SELECT account_number FROM accounts WHERE account_number=%s",
            (account_number,),
            fetchone=True,
        )
        if not existing:
            return account_number


# ============================================
# SESSION MANAGEMENT
# ============================================

def ensure_session():
    """
    Initializes all session state variables
    Called at application startup
    """
    st.session_state.setdefault("account", None)
    st.session_state.setdefault("reg_pending", None)
    st.session_state.setdefault("reg_otp", None)
    st.session_state.setdefault("reg_otp_expires", None)
    st.session_state.setdefault("reg_otp_attempts", 0)
    st.session_state.setdefault("pin_otp", None)
    st.session_state.setdefault("login_otp", None)
    st.session_state.setdefault("login_pending", None)
    st.session_state.setdefault("login_email", None)
    st.session_state.setdefault("login_otp_expires", None)
    st.session_state.setdefault("login_otp_attempts", 0)
    st.session_state.setdefault("pin_otp_expires", None)
    st.session_state.setdefault("pin_otp_attempts", 0)
    st.session_state.setdefault("last_active", datetime.now())


def refresh_session_activity():
    """Updates last activity timestamp to prevent session timeout"""
    st.session_state.last_active = datetime.now()


def session_expired():
    """
    Checks if session has expired due to inactivity
    
    Returns:
        bool: True if session expired, False otherwise
    """
    last = st.session_state.get("last_active")
    if not last:
        return False
    delta = datetime.now() - last
    return delta.total_seconds() > SESSION_TIMEOUT_MINUTES * 60


# ============================================
# OTP VALIDATION
# ============================================

def is_otp_expired(expires_at):
    """
    Checks if OTP has expired
    
    Args:
        expires_at (float): Expiration timestamp
    
    Returns:
        bool: True if expired, False otherwise
    """
    return expires_at and datetime.now().timestamp() > expires_at


# ============================================
# OTP STATE RESET FUNCTIONS
# ============================================

def reset_reg_otp_state():
    """Resets registration OTP state"""
    st.session_state.reg_otp = None
    st.session_state.reg_otp_expires = None
    st.session_state.reg_otp_attempts = 0
    st.session_state.reg_pending = None


def reset_login_otp_state():
    """Resets login OTP state"""
    st.session_state.login_otp = None
    st.session_state.login_otp_expires = None
    st.session_state.login_otp_attempts = 0
    st.session_state.login_pending = None
    st.session_state.login_email = None


def reset_pin_otp_state():
    """Resets PIN change OTP state"""
    st.session_state.pin_otp = None
    st.session_state.pin_otp_expires = None
    st.session_state.pin_otp_attempts = 0


# ============================================
# REGISTRATION FUNCTIONS
# ============================================

def send_registration_otp(name, email, pin, initial_balance):
    """
    Sends OTP for account registration
    
    Args:
        name (str): Account holder name
        email (str): Email address
        pin (str): 4-digit PIN
        initial_balance (float): Initial deposit amount
    
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validation
    if not name or not email or not pin.isdigit() or len(pin) != 4:
        return False, "Please enter a valid name, email, and 4-digit PIN."
    
    if initial_balance < 1000:
        return False, "Initial balance must be at least 1000."
    
    # Check if email already exists
    existing = db_execute(
        "SELECT account_number FROM accounts WHERE email=%s",
        (email,),
        fetchone=True,
    )
    if existing:
        return False, "Email already registered."
    
    # Generate and send OTP
    otp = generate_otp()
    st.session_state.reg_otp = otp
    st.session_state.reg_otp_expires = datetime.now().timestamp() + OTP_TTL_SECONDS
    st.session_state.reg_otp_attempts = 0
    st.session_state.reg_pending = {
        "name": name,
        "email": email,
        "pin": int(pin),  # Store as int temporarily, will be converted to string with leading zeros when saving
        "initial_balance": initial_balance,
    }
    
    try:
        send_email(email, "Your Registration OTP", build_otp_email(otp, "Registration OTP"))
        return True, "OTP sent to your email."
    except Exception:
        reset_reg_otp_state()
        return False, "Failed to send OTP email. Please try again."


def verify_registration_otp(otp_input):
    """
    Verifies registration OTP and creates account
    
    Args:
        otp_input (str): OTP entered by user
    
    Returns:
        tuple: (success: bool, message: str, account_number: int or None)
    """
    # Check if OTP was sent
    if not st.session_state.reg_otp or not st.session_state.reg_pending:
        return False, "Please send OTP first.", None
    
    # Check expiration
    if is_otp_expired(st.session_state.reg_otp_expires):
        reset_reg_otp_state()
        return False, "OTP expired. Please request a new OTP.", None
    
    # Check attempts
    st.session_state.reg_otp_attempts += 1
    if st.session_state.reg_otp_attempts > OTP_MAX_ATTEMPTS:
        reset_reg_otp_state()
        return False, "Too many invalid attempts. Please request a new OTP.", None
    
    # Verify OTP
    if not otp_input.isdigit() or int(otp_input) != st.session_state.reg_otp:
        return False, "Invalid OTP.", None
    
    # Create account
    pending = st.session_state.reg_pending
    account_number = generate_unique_account_number()
    
    # Store PIN as string to preserve leading zeros
    pin_str = str(pending["pin"]).zfill(4)  # Ensure 4 digits with leading zeros
    
    db_execute(
        """INSERT INTO accounts (account_number, name, email, balance, pin, account_type, interest_rate) 
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (
            account_number,
            pending["name"],
            pending["email"],
            pending["initial_balance"],
            pin_str,  # Store as string
            DEFAULT_ACCOUNT_TYPE,
            DEFAULT_INTEREST_RATE,
        ),
    )
    
    # Send welcome email
    try:
        send_email(pending["email"], "Welcome to SNJ Bank", build_welcome_email(pending["name"], account_number))
    except Exception:
        pass  # Account created, email failure is not critical
    
    reset_reg_otp_state()
    return True, f"Account created. Your account number is {account_number}", account_number


# ============================================
# LOGIN FUNCTIONS
# ============================================

def send_login_otp(account_number, email):
    """
    Sends OTP for login
    
    Args:
        account_number (str): Account number
        email (str): Email address
    
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validation
    if not account_number.isdigit() or not email:
        return False, "Enter valid account number and email first."
    
    # Verify account exists
    account = db_execute(
        "SELECT account_number FROM accounts WHERE account_number=%s AND email=%s",
        (int(account_number), email),
        fetchone=True,
    )
    if not account:
        return False, "Account number and email do not match."
    
    # Generate and send OTP
    otp = generate_otp()
    st.session_state.login_otp = otp
    st.session_state.login_pending = int(account_number)
    st.session_state.login_email = email
    st.session_state.login_otp_expires = datetime.now().timestamp() + OTP_TTL_SECONDS
    st.session_state.login_otp_attempts = 0
    
    try:
        send_email(email, "Your Login OTP", build_otp_email(otp, "Login OTP"))
        return True, "OTP sent to your email."
    except Exception:
        reset_login_otp_state()
        return False, "Failed to send OTP email. Please try again."


def verify_login_otp(otp_input):
    """
    Verifies login OTP and logs in user
    
    Args:
        otp_input (str): OTP entered by user
    
    Returns:
        tuple: (success: bool, message: str)
    """
    # Check if OTP was sent
    if not st.session_state.login_otp or not st.session_state.login_pending:
        return False, "Please send OTP first."
    
    # Check expiration
    if is_otp_expired(st.session_state.login_otp_expires):
        reset_login_otp_state()
        return False, "OTP expired. Please request a new OTP."
    
    # Check attempts
    st.session_state.login_otp_attempts += 1
    if st.session_state.login_otp_attempts > OTP_MAX_ATTEMPTS:
        reset_login_otp_state()
        return False, "Too many invalid attempts. Please request a new OTP."
    
    # Verify OTP
    if not otp_input.isdigit() or int(otp_input) != st.session_state.login_otp:
        return False, "Invalid OTP."
    
    # Fetch account details
    account = db_execute(
        "SELECT account_number, name, email, balance, account_type, interest_rate, last_interest_date FROM accounts WHERE account_number=%s",
        (st.session_state.login_pending,),
        fetchone=True,
    )
    
    if not account:
        return False, "Account not found."
    
    # Set session
    st.session_state.account = {
        "account_number": account[0],
        "name": account[1],
        "email": account[2],
        "balance": account[3],
        "account_type": account[4],
        "interest_rate": account[5],
        "last_interest_date": account[6],
    }
    
    reset_login_otp_state()
    return True, "Login successful."
