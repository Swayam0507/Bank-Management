"""
Configuration Settings for SNJ Bank Application
Reads sensitive values from environment variables (.env file)
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ============================================
# DATABASE CONFIGURATION
# ============================================
DB_NAME = os.getenv("DB_NAME", "bankaccountdatabase")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# ============================================
# SESSION & SECURITY CONFIGURATION
# ============================================
SESSION_TIMEOUT_MINUTES = 15   # Auto-logout after inactivity
OTP_TTL_SECONDS = 180          # OTP validity: 3 minutes
OTP_MAX_ATTEMPTS = 3           # Maximum OTP verification attempts

# ============================================
# EMAIL CONFIGURATION (SMTP)
# ============================================
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# ============================================
# BANK DETAILS
# ============================================
BANK_NAME = "SNJ Bank"
BRANCH_NAME = "Nikol Branch"
BRANCH_ADDRESS = "Shukan Chowkdi, Nikol, Ahmedabad - 382350"
PHONE_NO = "1800 5700 4500"
IFSC_CODE = "SNJB0284946"

# ============================================
# ACCOUNT CONFIGURATION
# ============================================
MIN_BALANCE = 1000        # Minimum balance requirement
PENALTY_AMOUNT = 100      # Penalty for falling below minimum balance
DEFAULT_ACCOUNT_TYPE = "Savings"
DEFAULT_INTEREST_RATE = 3.2  # Annual interest rate (%)

# ============================================
# LOAN TYPES & INTEREST RATES
# ============================================
LOAN_TYPES = {
    "Home Loan (8.5%)": ("Home Loan", 8.5),
    "Gold Loan (10%)": ("Gold Loan", 10),
    "Personal Loan (12%)": ("Personal Loan", 12),
}
