"""
SNJ Bank - Main Application Entry Point
A comprehensive banking application with OTP authentication, transactions, loans, and more

Author: SNJ Bank Development Team
Version: 2.0
"""

import streamlit as st

# Import service modules
from services.auth_service import ensure_session, session_expired, refresh_session_activity
from services.account_service import format_currency

# Import UI rendering functions
from ui.render_views import (
    render_landing, render_register, render_login, render_dashboard,
    render_deposit, render_withdraw, render_transfer, render_mini_statement,
    render_change_pin, render_transaction_chart, render_calculate_interest,
    render_apply_loan, render_view_loans, render_repay_loan, render_logout,
    render_emi_calculator
)


# ============================================
# APPLICATION INITIALIZATION
# ============================================

# Initialize session state
ensure_session()

# Configure Streamlit page
st.set_page_config(page_title="SNJ Bank", layout="centered")


# ============================================
# MAIN APPLICATION LOGIC
# ============================================

def main():
    """
    Main application controller
    Handles routing between authenticated and unauthenticated views
    """
    
    # Check if user is logged in
    if st.session_state.account:
        # Check session timeout
        if session_expired():
            st.session_state.account = None
            st.warning("Session timed out due to inactivity. Please log in again.")
            st.rerun()
        
        # Refresh activity timestamp
        refresh_session_activity()
        
        # Render sidebar with account info
        _render_sidebar()
        
        # Render selected menu page
        _render_authenticated_page()
    
    else:
        # Render landing page for unauthenticated users
        _render_unauthenticated_page()


def _render_sidebar():
    """Renders sidebar with account information and navigation menu"""
    st.sidebar.title("Account")
    st.sidebar.write(st.session_state.account["name"])
    st.sidebar.caption(f"{st.session_state.account['account_number']}")
    st.sidebar.caption(st.session_state.account.get("email", ""))
    st.sidebar.write(f"Balance: {format_currency(st.session_state.account['balance'])}")
    
    # Navigation menu
    menu = st.sidebar.radio(
        "Account Menu",
        [
            "Dashboard",
            "Transaction Chart",
            "Calculate Interest",
            "Deposit",
            "Withdraw",
            "Transfer",
            "Mini Statement",
            "EMI Calculator",
            "Apply for Loan",
            "View Loans",
            "Repay Loan",
            "Change PIN",
            "Logout",
        ],
    )
    
    # Store selected menu in session state
    st.session_state.selected_menu = menu


def _render_authenticated_page():
    """Routes to appropriate page based on menu selection"""
    menu = st.session_state.get("selected_menu", "Dashboard")
    
    # Menu routing
    if menu == "Dashboard":
        render_dashboard()
    elif menu == "Deposit":
        render_deposit()
    elif menu == "Withdraw":
        render_withdraw()
    elif menu == "Transfer":
        render_transfer()
    elif menu == "Mini Statement":
        render_mini_statement()
    elif menu == "Change PIN":
        render_change_pin()
    elif menu == "Transaction Chart":
        render_transaction_chart()
    elif menu == "Calculate Interest":
        render_calculate_interest()
    elif menu == "EMI Calculator":
        render_emi_calculator()
    elif menu == "Apply for Loan":
        render_apply_loan()
    elif menu == "View Loans":
        render_view_loans()
    elif menu == "Repay Loan":
        render_repay_loan()
    elif menu == "Logout":
        render_logout()


def _render_unauthenticated_page():
    """Renders landing page with login/register options"""
    action = render_landing()
    
    if action == "Register":
        render_register()
    else:
        render_login()


# ============================================
# APPLICATION ENTRY POINT
# ============================================

if __name__ == "__main__":
    main()
