"""
UI Rendering Module
Contains all Streamlit UI rendering functions for the banking application
"""

import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from database.db_manager import db_execute
from services.auth_service import (
    send_registration_otp, verify_registration_otp,
    send_login_otp, verify_login_otp, refresh_session_activity
)
from services.account_service import (
    format_currency, format_amount, calculate_and_apply_interest,
    send_pin_change_otp, verify_and_change_pin
)
from services.transaction_service import (
    process_deposit, process_withdrawal, process_transfer,
    get_mini_statement, get_transaction_summary
)
from services.loan_service import (
    apply_loan, get_loans_with_emi, get_active_loans, repay_loan_emi, calculate_emi_details
)
from services.email_service import send_full_statement
from config.settings import LOAN_TYPES, MIN_BALANCE, PENALTY_AMOUNT


# ============================================
# LANDING PAGE
# ============================================

def render_landing():
    """
    Renders the landing page with login/register options
    
    Returns:
        str: Selected action ("Login" or "Register")
    """
    st.markdown("""
        <div style="padding: 12px 0;">
            <h1 style="margin-bottom: 6px;">SNJ Bank</h1>
            <p style="font-size: 1.05rem; color: #444;">
                Secure, simple banking - deposits, transfers, loans, and smart tracking in one place.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.markdown("**Instant Access**")
        st.write("OTP-secured login and quick account actions.")
    with col2:
        st.markdown("**Smart Insights**")
        st.write("Mini statements and visual transaction breakdowns.")
    with col3:
        st.markdown("**Loans & EMI**")
        st.write("Apply for loans and repay EMIs in seconds.")
    
    st.markdown("---")
    action = st.radio("Get started", ["Login", "Register"], horizontal=True)
    return action


# ============================================
# REGISTRATION PAGE
# ============================================

def render_register():
    """Renders the registration page with OTP verification"""
    st.subheader("Register with Email OTP")
    
    name = st.text_input("Full Name")
    email = st.text_input("Email")
    pin = st.text_input("Set 4-digit PIN", type="password")
    initial_balance = st.number_input("Initial Balance", min_value=0.0, step=100.0)
    otp_input = st.text_input("OTP", max_chars=6)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Send OTP"):
            refresh_session_activity()
            success, message = send_registration_otp(name, email, pin, initial_balance)
            if success:
                st.success(message)
            else:
                st.error(message)
    
    with col2:
        if st.button("Verify & Create Account"):
            refresh_session_activity()
            success, message, account_number = verify_registration_otp(otp_input)
            if success:
                st.success(message)
            else:
                st.error(message)


# ============================================
# LOGIN PAGE
# ============================================

def render_login():
    """Renders the login page with OTP verification"""
    st.title("Secure Email OTP Login")
    
    account_number = st.text_input("Account Number")
    email = st.text_input("Email")
    otp_input = st.text_input("OTP", max_chars=6)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Send OTP"):
            refresh_session_activity()
            success, message = send_login_otp(account_number, email)
            if success:
                st.success(message)
            else:
                st.error(message)
    
    with col2:
        if st.button("Verify & Login"):
            refresh_session_activity()
            success, message = verify_login_otp(otp_input)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)


# ============================================
# DASHBOARD
# ============================================

def render_dashboard():
    """Renders the account dashboard with overview"""
    account = st.session_state.account
    
    st.subheader(f"Welcome, {account['name']}")
    st.caption("Your account overview and quick stats.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"Account Number: {account['account_number']}")
        st.write(f"Account Type: {account['account_type']}")
        st.write(f"Email: {account.get('email', '') or 'Not provided'}")
    
    with col2:
        st.write(f"Available Balance: {format_currency(account['balance'])}")
        st.write(f"Interest Rate: {account['interest_rate']}% p.a.")
        last_interest = account.get("last_interest_date")
        st.write(f"Last Interest Applied: {last_interest or 'Not yet'}")


# ============================================
# DEPOSIT
# ============================================

def render_deposit():
    """Renders the deposit page with PIN verification"""
    st.subheader("Deposit")
    st.caption("Add funds to your account instantly.")
    st.info(
        f"Current balance: {format_currency(st.session_state.account['balance'])}. "
        f"Minimum balance requirement: INR {MIN_BALANCE:,}."
    )
    
    amount = st.number_input("Amount", min_value=0.0, step=100.0, key="deposit_amount")
    pin_input = st.text_input("Enter your 4-digit PIN", type="password", max_chars=4, key="deposit_pin")
    
    if st.button("Deposit"):
        refresh_session_activity()
        
        # Validate PIN first
        if not pin_input:
            st.error("Please enter your PIN.")
            return
        
        if not pin_input.isdigit() or len(pin_input) != 4:
            st.error("PIN must be exactly 4 digits.")
            return
        
        # Verify PIN from database
        stored_pin = db_execute(
            "SELECT pin FROM accounts WHERE account_number=%s",
            (st.session_state.account["account_number"],),
            fetchone=True
        )
        
        if not stored_pin or str(stored_pin[0]) != pin_input:
            st.error("❌ Invalid PIN. Transaction cancelled.")
            return
        
        # PIN verified, proceed with deposit
        success, message, new_balance = process_deposit(
            st.session_state.account["account_number"],
            st.session_state.account["name"],
            st.session_state.account["account_type"],
            st.session_state.account["balance"],
            amount
        )
        
        if success:
            st.session_state.account["balance"] = new_balance
            st.success("✅ " + message)
        else:
            st.error(message)


# ============================================
# WITHDRAWAL
# ============================================

def render_withdraw():
    """Renders the withdrawal page with PIN verification"""
    st.subheader("Withdraw")
    st.caption("Withdraw funds with minimum balance rule.")
    st.info(
        f"Current balance: {format_currency(st.session_state.account['balance'])}. "
        f"If balance falls below INR {MIN_BALANCE:,}, a penalty of INR {PENALTY_AMOUNT} is applied."
    )
    
    amount = st.number_input("Amount", min_value=0.0, step=100.0, key="withdraw_amount")
    pin_input = st.text_input("Enter your 4-digit PIN", type="password", max_chars=4, key="withdraw_pin")
    
    if st.button("Withdraw"):
        refresh_session_activity()
        
        # Validate PIN first
        if not pin_input:
            st.error("Please enter your PIN.")
            return
        
        if not pin_input.isdigit() or len(pin_input) != 4:
            st.error("PIN must be exactly 4 digits.")
            return
        
        # Verify PIN from database
        stored_pin = db_execute(
            "SELECT pin FROM accounts WHERE account_number=%s",
            (st.session_state.account["account_number"],),
            fetchone=True
        )
        
        if not stored_pin or str(stored_pin[0]) != pin_input:
            st.error("❌ Incorrect PIN. Transaction denied.")
            return
        
        # PIN verified, proceed with withdrawal
        success, message, new_balance, penalty_applied = process_withdrawal(
            st.session_state.account["account_number"],
            st.session_state.account["name"],
            st.session_state.account["account_type"],
            st.session_state.account["balance"],
            amount
        )
        
        if success:
            st.session_state.account["balance"] = new_balance
            if penalty_applied:
                st.warning("✅ " + message)
            else:
                st.success("✅ " + message)
        else:
            st.error(message)


# ============================================
# TRANSFER
# ============================================

def render_transfer():
    """Renders the transfer page with PIN verification"""
    st.subheader("Transfer")
    st.caption("Send money to another account securely.")
    st.info(
        f"Available balance: {format_currency(st.session_state.account['balance'])}. "
        "Transfers are recorded in both accounts."
    )
    
    recipient_acc = st.text_input("Recipient Account Number", key="transfer_recipient")
    amount = st.number_input("Amount", min_value=0.0, step=100.0, key="transfer_amount")
    pin_input = st.text_input("Enter your 4-digit PIN", type="password", max_chars=4, key="transfer_pin")
    
    if st.button("Transfer"):
        refresh_session_activity()
        
        if not recipient_acc.isdigit():
            st.error("Enter a valid recipient account number.")
            return
        
        # Validate PIN first
        if not pin_input:
            st.error("Please enter your PIN.")
            return
        
        if not pin_input.isdigit() or len(pin_input) != 4:
            st.error("PIN must be exactly 4 digits.")
            return
        
        # Verify PIN from database
        stored_pin = db_execute(
            "SELECT pin FROM accounts WHERE account_number=%s",
            (st.session_state.account["account_number"],),
            fetchone=True
        )
        
        if not stored_pin or str(stored_pin[0]) != pin_input:
            st.error("❌ Incorrect PIN. Transaction denied.")
            return
        
        # PIN verified, proceed with transfer
        success, message, new_balance, recipient_name = process_transfer(
            st.session_state.account["account_number"],
            st.session_state.account["name"],
            st.session_state.account["account_type"],
            st.session_state.account["balance"],
            int(recipient_acc),
            amount
        )
        
        if recipient_name:
            st.write(f"Recipient Name: {recipient_name}")
        
        if success:
            st.session_state.account["balance"] = new_balance
            st.success("✅ " + message)
        else:
            st.error(message)


# ============================================
# MINI STATEMENT
# ============================================

def render_mini_statement():
    """Renders mini statement with last 5 transactions"""
    st.subheader("Mini Statement")
    st.caption("Last 5 transactions for quick review.")
    
    transactions = get_mini_statement(st.session_state.account["account_number"])
    
    if transactions:
        rows = []
        for t in transactions:
            rows.append({
                "Time": t[2],
                "Type": t[0],
                "Amount": format_currency(float(t[1]))
            })
        st.table(rows)
    else:
        st.info("No transactions available.")
    
    st.divider()
    
    # Email full statement section
    st.subheader("Get Full Statement")
    
    if st.button("Email Full Statement"):
        email = st.session_state.account.get("email")
        
        if email:
            success = send_full_statement(email, st.session_state.account["account_number"])
            
            if success:
                st.success(f"Statement sent successfully to {email} 📧")
            else:
                st.error("Failed to send email.")
        else:
            st.error("No email registered with this account.")


# ============================================
# CHANGE PIN
# ============================================

def render_change_pin():
    """Renders PIN change page with OTP verification"""
    st.subheader("Change PIN")
    st.caption("Secure your account with a new 4-digit PIN.")
    st.info("OTP is required. OTP is valid for 3 minutes with max 3 attempts.")
    
    new_pin = st.text_input("New 4-digit PIN", type="password")
    otp_input = st.text_input("OTP", max_chars=4)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Send OTP"):
            refresh_session_activity()
            email = st.session_state.account.get("email")
            success, message = send_pin_change_otp(email)
            if success:
                st.success(message)
            else:
                st.error(message)
    
    with col2:
        if st.button("Change PIN"):
            refresh_session_activity()
            success, message = verify_and_change_pin(
                st.session_state.account["account_number"],
                new_pin,
                otp_input
            )
            if success:
                st.success(message)
            else:
                st.error(message)


# ============================================
# TRANSACTION CHART
# ============================================

def render_transaction_chart():
    """Renders visual transaction breakdown chart"""
    st.subheader("Transaction History Chart")
    st.caption("Visual breakdown by transaction type.")
    
    totals = get_transaction_summary(st.session_state.account["account_number"])
    
    if not totals:
        st.info("No transactions available for visualization.")
        return
    
    categories = [
        "Deposit", "Withdrawal", "Transfer Sent", "Transfer Received",
        "Interest", "Penalty", "Loan Repayment"
    ]
    
    palette = plt.cm.tab20.colors
    series = [(cat, totals.get(cat, 0.0), palette[i % len(palette)]) for i, cat in enumerate(categories)]
    total_value = sum(v for _, v, _ in series)
    
    if total_value <= 0:
        st.info("No positive transaction totals to display.")
        return
    
    labels = [l for l, _, _ in series]
    values = [v for _, v, _ in series]
    colors = [c for _, _, c in series]
    sizes = [v if v > 0 else 0.0 for v in values]
    
    def pct_fmt(pct):
        return f"{pct:.1f}%" if pct >= 1 else ""
    
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(
        sizes,
        labels=None,
        autopct=pct_fmt,
        colors=colors,
        startangle=140,
        shadow=False,
        pctdistance=0.75,
        wedgeprops={"edgecolor": "white", "linewidth": 1},
    )
    ax.set_title(f"Transaction Distribution for {st.session_state.account['name']}")
    
    # Create legend
    legend_handles = []
    for label, value, color in series:
        legend_color = color if value > 0 else "#D0D0D0"
        legend_handles.append(
            Patch(facecolor=legend_color, edgecolor="white", label=f"{label} ({format_amount(value)})")
        )
    ax.legend(handles=legend_handles, loc="center left", bbox_to_anchor=(1, 0.5))
    
    st.pyplot(fig)


# ============================================
# CALCULATE INTEREST
# ============================================

def render_calculate_interest():
    """Renders interest calculation page"""
    st.subheader("Calculate Interest")
    
    if st.session_state.account["account_type"] != "Savings":
        st.info("Interest calculation is not applicable for this account type.")
        return
    
    st.info(
        f"Annual interest rate: {st.session_state.account['interest_rate']}% (monthly applied). "
        "Interest can be applied once per month."
    )
    st.caption("Monthly interest based on the annual rate will be applied.")
    
    if st.button("Calculate Interest"):
        refresh_session_activity()
        success, message, interest, new_balance = calculate_and_apply_interest(
            st.session_state.account["account_number"],
            st.session_state.account["name"],
            st.session_state.account["account_type"],
            st.session_state.account["balance"],
            st.session_state.account["interest_rate"]
        )
        
        if success:
            st.session_state.account["balance"] = new_balance
            st.success(message)
        else:
            st.warning(message)


# ============================================
# EMI CALCULATOR
# ============================================

def render_emi_calculator():
    """Renders standalone EMI calculator tool"""
    st.subheader("EMI Calculator")
    st.caption("Calculate your loan EMI before applying.")
    
    st.info("Enter loan details to see monthly EMI, total interest, and payment breakdown.")
    
    # Input fields
    col1, col2 = st.columns(2)
    
    with col1:
        calc_loan_amount = st.number_input(
            "Loan Amount (₹)", 
            min_value=1000.0, 
            max_value=100000000.0,
            value=100000.0,
            step=10000.0,
            key="calc_loan_amount"
        )
        calc_interest_rate = st.number_input(
            "Annual Interest Rate (%)", 
            min_value=0.1, 
            max_value=50.0,
            value=10.0,
            step=0.1,
            key="calc_interest_rate"
        )
    
    with col2:
        calc_tenure = st.number_input(
            "Loan Tenure (Months)", 
            min_value=1, 
            max_value=360,
            value=12,
            step=1,
            key="calc_tenure"
        )
        calc_tenure_years = calc_tenure / 12
        st.caption(f"≈ {calc_tenure_years:.1f} years")
    
    # Calculate EMI details
    if calc_loan_amount > 0 and calc_tenure > 0:
        emi_details = calculate_emi_details(calc_loan_amount, calc_interest_rate, calc_tenure)
        
        st.markdown("---")
        st.subheader("📊 EMI Breakdown")
        
        # Display results in cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
                <div style="background:#1f77b4; padding:20px; border-radius:10px; text-align:center;">
                    <h4 style="color:white; margin:0;">Monthly EMI</h4>
                    <h2 style="color:white; margin:10px 0;">₹{emi_details['monthly_emi']:,.2f}</h2>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
                <div style="background:#2ca02c; padding:20px; border-radius:10px; text-align:center;">
                    <h4 style="color:white; margin:0;">Principal</h4>
                    <h2 style="color:white; margin:10px 0;">₹{emi_details['principal_amount']:,.2f}</h2>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
                <div style="background:#ff7f0e; padding:20px; border-radius:10px; text-align:center;">
                    <h4 style="color:white; margin:0;">Total Interest</h4>
                    <h2 style="color:white; margin:10px 0;">₹{emi_details['total_interest']:,.2f}</h2>
                </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
                <div style="background:#d62728; padding:20px; border-radius:10px; text-align:center;">
                    <h4 style="color:white; margin:0;">Total Amount</h4>
                    <h2 style="color:white; margin:10px 0;">₹{emi_details['total_amount']:,.2f}</h2>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Detailed breakdown table
        st.subheader("📋 Payment Summary")
        
        summary_data = {
            "Description": [
                "Loan Amount (Principal)",
                "Interest Rate (Annual)",
                "Loan Tenure",
                "Monthly EMI",
                "Total Interest Payable",
                "Total Amount Payable",
                "Interest as % of Principal"
            ],
            "Value": [
                f"₹{emi_details['principal_amount']:,.2f}",
                f"{calc_interest_rate}%",
                f"{calc_tenure} months ({calc_tenure_years:.1f} years)",
                f"₹{emi_details['monthly_emi']:,.2f}",
                f"₹{emi_details['total_interest']:,.2f}",
                f"₹{emi_details['total_amount']:,.2f}",
                f"{(emi_details['total_interest'] / emi_details['principal_amount'] * 100):.2f}%"
            ]
        }
        
        st.table(summary_data)
        
        # Visual representation
        st.subheader("📈 Principal vs Interest")
        
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=(8, 5))
        
        categories = ['Principal', 'Interest']
        amounts = [emi_details['principal_amount'], emi_details['total_interest']]
        colors = ['#2ca02c', '#ff7f0e']
        
        bars = ax.bar(categories, amounts, color=colors, alpha=0.7, edgecolor='black')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'₹{height:,.0f}',
                   ha='center', va='bottom', fontsize=12, fontweight='bold')
        
        ax.set_ylabel('Amount (₹)', fontsize=12)
        ax.set_title('Loan Breakdown: Principal vs Interest', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        st.pyplot(fig)
        
        # Amortization note
        st.info(
            f"💡 **Note:** You will pay ₹{emi_details['monthly_emi']:,.2f} every month for {calc_tenure} months. "
            f"Out of the total ₹{emi_details['total_amount']:,.2f} you'll pay, "
            f"₹{emi_details['total_interest']:,.2f} ({(emi_details['total_interest'] / emi_details['total_amount'] * 100):.1f}%) is interest."
        )


# ============================================
# APPLY FOR LOAN
# ============================================

def render_apply_loan():
    """Renders loan application page with EMI preview"""
    st.subheader("Apply for Loan")
    st.caption("Choose a loan type and tenure.")
    st.info("Loan eligibility is subject to account status and available balance.")
    
    loan_choice = st.selectbox("Loan Type", list(LOAN_TYPES.keys()))
    loan_amount = st.number_input("Loan Amount", min_value=0.0, step=1000.0)
    tenure = st.number_input("Tenure (months)", min_value=1, step=1)
    
    # Show EMI preview
    if loan_amount > 0 and tenure > 0:
        loan_type, interest_rate = LOAN_TYPES[loan_choice]
        emi_details = calculate_emi_details(loan_amount, interest_rate, tenure)
        
        st.markdown("---")
        st.subheader("📊 Loan Preview")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Monthly EMI", f"₹{emi_details['monthly_emi']:,.2f}")
        
        with col2:
            st.metric("Total Interest", f"₹{emi_details['total_interest']:,.2f}")
        
        with col3:
            st.metric("Total Payable", f"₹{emi_details['total_amount']:,.2f}")
        
        st.info(
            f"💡 You will pay **₹{emi_details['monthly_emi']:,.2f}** every month for **{tenure} months**. "
            f"Total interest: ₹{emi_details['total_interest']:,.2f}"
        )
    
    if st.button("Apply Loan"):
        refresh_session_activity()
        success, message = apply_loan(
            st.session_state.account["account_number"],
            loan_choice,
            loan_amount,
            tenure
        )
        
        if success:
            st.success(message)
            if loan_amount > 0 and tenure > 0:
                loan_type, interest_rate = LOAN_TYPES[loan_choice]
                emi_details = calculate_emi_details(loan_amount, interest_rate, tenure)
                st.success(f"✅ Your monthly EMI will be: ₹{emi_details['monthly_emi']:,.2f}")
        else:
            st.error(message)


# ============================================
# VIEW LOANS
# ============================================

def render_view_loans():
    """Renders loan overview page with EMI details"""
    st.subheader("Your Loans")
    st.caption("Overview of active and paid loans with monthly EMI.")
    
    loans = get_loans_with_emi(st.session_state.account["account_number"])
    
    if not loans:
        st.info("No loans found.")
        return
    
    active_loans = [loan for loan in loans if loan["status"] == "Active"]
    total_remaining = sum(loan["remaining_amount"] for loan in active_loans)
    total_monthly_emi = sum(loan["monthly_emi"] for loan in active_loans)
    
    # Summary card
    st.markdown(f"""
        <div style="
            background:#1f3b57;
            padding:20px;
            border-radius:12px;
            margin-bottom:20px;">
            <h4 style="color:#4da6ff; margin:0;">
                Active Loans: {len(active_loans)}
            </h4>
            <p style="color:white; margin:5px 0 0 0;">
                Total Remaining: ₹{total_remaining:,.2f}
            </p>
            <p style="color:#4da6ff; margin:5px 0 0 0; font-size:1.1em;">
                <strong>Total Monthly EMI: ₹{total_monthly_emi:,.2f}</strong>
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Display loan cards using Streamlit components instead of HTML
    for loan in loans:
        status_color = "#28a745" if loan["status"] == "Active" else "#6c757d"
        progress = ((loan["loan_amount"] - loan["remaining_amount"]) / loan["loan_amount"]) * 100 if loan["loan_amount"] else 0
        
        # Calculate payments made and remaining
        payments_made = int((loan["loan_amount"] - loan["remaining_amount"]) / loan["monthly_emi"]) if loan["monthly_emi"] > 0 else 0
        payments_remaining = loan["tenure"] - payments_made
        
        # Create container for each loan
        with st.container():
            # Header with loan type and status
            col_header1, col_header2 = st.columns([3, 1])
            with col_header1:
                st.markdown(f"### {loan['loan_type']}")
            with col_header2:
                status_badge = "🟢 Active" if loan["status"] == "Active" else "⚫ Paid"
                st.markdown(f"**{status_badge}**")
            
            st.markdown("---")
            
            # Loan details in two columns
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Loan ID:** {loan['loan_id']}")
                st.write(f"**Loan Amount:** ₹{loan['loan_amount']:,.2f}")
                st.write(f"**Interest Rate:** {loan['interest_rate']}% p.a.")
                st.write(f"**Tenure:** {loan['tenure']} months")
            
            with col2:
                st.markdown(f"**Monthly EMI:** <span style='color:#1f77b4; font-size:1.3em;'>₹{loan['monthly_emi']:,.2f}</span>", unsafe_allow_html=True)
                st.write(f"**Remaining:** ₹{loan['remaining_amount']:,.2f}")
                st.write(f"**Progress:** {progress:.1f}%")
                st.write(f"**Payments:** {payments_made}/{loan['tenure']} ({payments_remaining} remaining)")
            
            # Progress bar
            if loan["status"] == "Active":
                st.progress(progress / 100)
                st.caption(f"₹{loan['loan_amount'] - loan['remaining_amount']:,.2f} paid out of ₹{loan['loan_amount']:,.2f}")
            
            st.markdown("---")


# ============================================
# REPAY LOAN
# ============================================

def render_repay_loan():
    """Renders loan repayment page"""
    st.subheader("Repay Loan")
    st.caption("Pay EMI for active loans.")
    st.info("EMI is calculated using standard amortization formula.")
    
    loans = get_active_loans(st.session_state.account["account_number"])
    
    if not loans:
        st.info("No active loans to repay.")
        return
    
    loan_map = {f"Loan {l[0]} - {l[1]}": l for l in loans}
    selected = st.selectbox("Select Loan", list(loan_map.keys()))
    
    if st.button("Pay EMI"):
        refresh_session_activity()
        loan = loan_map[selected]
        loan_id, _, loan_amount, interest_rate, tenure, remaining_amount = loan
        
        success, message, emi, new_remaining, loan_paid = repay_loan_emi(
            loan_id, loan_amount, interest_rate, tenure, remaining_amount,
            st.session_state.account["balance"]
        )
        
        if success:
            # Update balance
            new_balance = st.session_state.account["balance"] - emi
            from services.account_service import update_balance
            from services.transaction_service import record_transaction, write_passbook
            
            update_balance(new_balance, st.session_state.account["account_number"])
            record_transaction(st.session_state.account["account_number"], "Loan Repayment", emi)
            write_passbook(
                st.session_state.account["account_number"],
                st.session_state.account["name"],
                st.session_state.account["account_type"],
                new_balance,
                "Loan Repayment",
                emi
            )
            
            st.success(f"{message} Remaining loan amount: INR {new_remaining:,.2f}")
        else:
            st.error(message)


# ============================================
# LOGOUT
# ============================================

def render_logout():
    """Renders logout button"""
    if st.button("Logout"):
        st.session_state.account = None
        st.success("Logged out.")
