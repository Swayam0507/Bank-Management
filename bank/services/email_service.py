"""
Email Service Module
Handles all email-related operations including OTP, statements, and notifications
"""

import smtplib
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.message import EmailMessage
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4

from config.settings import (
    SENDER_EMAIL, APP_PASSWORD, SMTP_SERVER, SMTP_PORT,
    BANK_NAME, BRANCH_NAME, BRANCH_ADDRESS, PHONE_NO, IFSC_CODE
)
from database.db_manager import db_execute


# ============================================
# EMAIL SENDING FUNCTIONS
# ============================================

def send_email(receiver_email, subject, body):
    """
    Sends a simple text email via SMTP
    
    Args:
        receiver_email (str): Recipient email address
        subject (str): Email subject
        body (str): Email body content
    """
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = receiver_email
    
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)


# ============================================
# EMAIL TEMPLATE BUILDERS
# ============================================

def build_email_footer():
    """
    Builds standard email footer with bank contact information
    
    Returns:
        str: Formatted email footer
    """
    return (
        f"\n\nThanks,\n"
        f"{BANK_NAME} Digital Team\n"
        f"Support: {PHONE_NO}\n"
        f"Sent on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )


def build_otp_email(otp, purpose):
    """
    Builds OTP email content
    
    Args:
        otp (int): One-time password
        purpose (str): Purpose of OTP (e.g., "Login", "Registration")
    
    Returns:
        str: Formatted OTP email body
    """
    return (
        f"{purpose}\n\n"
        f"Your OTP is: {otp}\n"
        "Valid for 3 minutes. Do not share this OTP with anyone."
        + build_email_footer()
    )


def build_welcome_email(name, account_number):
    """
    Builds welcome email for new account creation
    
    Args:
        name (str): Account holder name
        account_number (int): New account number
    
    Returns:
        str: Formatted welcome email body
    """
    return (
        f"Hello {name},\n\n"
        f"Your {BANK_NAME} account has been created successfully.\n"
        f"Account Number: {account_number}\n"
        "Keep your account number and PIN confidential."
        + build_email_footer()
    )


# ============================================
# STATEMENT GENERATION & EMAIL
# ============================================

def send_full_statement(email, account_number):
    """
    Generates PDF statement and emails it to the account holder
    
    Args:
        email (str): Recipient email address
        account_number (int): Account number for statement generation
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Fetch account data
    account = db_execute(
        "SELECT name, balance, account_type, interest_rate FROM accounts WHERE account_number=%s",
        (account_number,),
        fetchone=True
    )
    
    # Fetch transactions
    transactions = db_execute(
        "SELECT type, amount, timestamp FROM transactions WHERE account_number=%s ORDER BY id ASC",
        (account_number,),
        fetchall=True,
    )
    
    if not transactions or not account:
        return False
    
    try:
        name, current_balance, account_type, interest_rate = account
        
        # Generate PDF
        pdf_file = f"statement_{account_number}.pdf"
        doc = SimpleDocTemplate(pdf_file, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Add bank header
        _add_bank_header(elements, styles)
        
        # Add customer info
        _add_customer_info(elements, styles, name, account_number, account_type, interest_rate)
        
        # Add transaction table
        opening_balance = _add_transaction_table(elements, styles, transactions, current_balance, account_type)
        
        # Add account summary
        _add_account_summary(elements, styles, account_type, opening_balance, current_balance)
        
        # Build PDF
        doc.build(elements)
        
        # Send email with PDF attachment
        _send_statement_email(email, pdf_file)
        
        # Clean up
        os.remove(pdf_file)
        
        return True
    
    except Exception as e:
        print(f"Email Error: {e}")
        return False


def _add_bank_header(elements, styles):
    """Adds professional bank header to PDF statement"""
    # Bank name with professional styling
    bank_title_style = ParagraphStyle(
        name="BankTitle",
        fontSize=20,
        textColor=colors.HexColor('#1f3b57'),
        alignment=1,
        spaceAfter=8,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    elements.append(Paragraph(f"<b>{BANK_NAME}</b>", bank_title_style))
    elements.append(Spacer(1, 5))
    
    # Bank details
    bank_detail_style = ParagraphStyle(
        name="BankDetail",
        fontSize=10,
        textColor=colors.HexColor('#555555'),
        alignment=1,
        spaceAfter=3,
        spaceBefore=2
    )
    
    elements.append(Paragraph(f"<b>Branch:</b> {BRANCH_NAME}", bank_detail_style))
    elements.append(Spacer(1, 2))
    elements.append(Paragraph(f"{BRANCH_ADDRESS}", bank_detail_style))
    elements.append(Spacer(1, 2))
    elements.append(Paragraph(f"<b>Phone:</b> {PHONE_NO} | <b>IFSC:</b> {IFSC_CODE}", bank_detail_style))
    
    elements.append(Spacer(1, 15))
    
    # Statement title with colored background
    statement_title_style = ParagraphStyle(
        name="StatementTitle",
        fontSize=16,
        textColor=colors.white,
        backColor=colors.HexColor('#1f3b57'),
        alignment=1,
        spaceAfter=15,
        spaceBefore=15,
        leading=24
    )
    
    elements.append(Paragraph("ACCOUNT STATEMENT", statement_title_style))
    elements.append(Spacer(1, 20))


def _add_customer_info(elements, styles, name, account_number, account_type, interest_rate):
    """Adds customer information to PDF statement with professional styling"""
    # Customer info box with border
    customer_style = ParagraphStyle(
        name="CustomerInfo",
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        alignment=0,
        spaceAfter=3,
        leftIndent=10
    )
    
    # Create a bordered box for customer info
    customer_data = [
        ["Account Holder", name],
        ["Account Number", str(account_number)],
        ["Account Type", account_type],
        ["Interest Rate", f"{interest_rate}% per annum"],
        ["Statement Date", datetime.now().strftime('%d %B %Y')]
    ]
    
    customer_table = Table(customer_data, colWidths=[150, 350])
    
    customer_table_style = [
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f4f8')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1f3b57')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]
    
    customer_table.setStyle(TableStyle(customer_table_style))
    elements.append(customer_table)
    elements.append(Spacer(1, 20))


def _add_transaction_table(elements, styles, transactions, current_balance, account_type):
    """Adds transaction table to PDF statement and returns opening balance"""
    # Professional header style
    header_style = ParagraphStyle(
        name="TableHeader",
        fontSize=14,
        textColor=colors.white,
        backColor=colors.HexColor('#1f3b57'),
        alignment=1,
        spaceAfter=12,
        spaceBefore=12,
        leading=18
    )
    
    elements.append(Paragraph(f"{account_type} Account - Transaction History", header_style))
    elements.append(Spacer(1, 10))
    
    # Calculate opening balance by working backwards
    temp_balance = current_balance
    for t in reversed(transactions):
        txn_type = t[0].lower()
        amount = float(t[1])
        
        # Reverse the transaction to get opening balance
        if txn_type in ["deposit", "credit", "transfer received", "interest"]:
            temp_balance -= amount
        else:
            temp_balance += amount
    
    opening_balance = temp_balance
    running_balance = opening_balance
    
    # Build transaction table with clear headers (using Rs. instead of ₹)
    data = [["Date", "Transaction Type", "Debit (Rs.)", "Credit (Rs.)", "Balance (Rs.)"]]
    
    # Add opening balance row
    data.append([
        "Opening",
        "Opening Balance",
        "",
        "",
        f"{opening_balance:,.2f}"
    ])
    
    for t in transactions:
        txn_type = t[0]
        amount = float(t[1])
        timestamp = str(t[2])
        date = timestamp.split(" ")[0] if " " in timestamp else timestamp
        
        debit = ""
        credit = ""
        
        # Categorize transactions clearly
        if txn_type.lower() in ["withdrawal", "transfer sent", "penalty", "loan repayment"]:
            debit = f"{amount:,.2f}"
            running_balance -= amount
        else:  # deposit, credit, transfer received, interest
            credit = f"{amount:,.2f}"
            running_balance += amount
        
        data.append([
            date,
            txn_type,
            debit,
            credit,
            f"{running_balance:,.2f}"
        ])
    
    # Add closing balance row
    data.append([
        "Closing",
        "Closing Balance",
        "",
        "",
        f"{current_balance:,.2f}"
    ])
    
    # Create table with better column widths
    col_widths = [80, 150, 90, 90, 90]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    
    # Professional styling
    style_list = [
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5f8d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Opening balance row
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e8f4f8')),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 1), (1, 1), colors.HexColor('#1f3b57')),
        
        # Data rows
        ('FONTNAME', (0, 2), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 2), (-1, -2), 9),
        ('ALIGN', (2, 2), (-1, -2), 'RIGHT'),
        ('ALIGN', (0, 2), (1, -2), 'LEFT'),
        
        # Closing balance row
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, -1), (1, -1), colors.HexColor('#1f3b57')),
        
        # Grid and borders
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
        ('LINEABOVE', (0, 0), (-1, 0), 2, colors.HexColor('#1f3b57')),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1f3b57')),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#1f3b57')),
        
        # Padding
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]
    
    # Color code amounts: Red for debits, Green for credits
    for i in range(2, len(data) - 1):  # Skip header, opening, and closing rows
        # Debit column (red)
        if data[i][2]:  # If debit has value
            style_list.append(('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#d32f2f')))
            style_list.append(('FONTNAME', (2, i), (2, i), 'Helvetica-Bold'))
        
        # Credit column (green)
        if data[i][3]:  # If credit has value
            style_list.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#388e3c')))
            style_list.append(('FONTNAME', (3, i), (3, i), 'Helvetica-Bold'))
        
        # Balance column (blue)
        style_list.append(('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#1976d2')))
        style_list.append(('FONTNAME', (4, i), (4, i), 'Helvetica-Bold'))
        
        # Alternate row colors for better readability
        if i % 2 == 0:
            style_list.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f9f9f9')))
    
    # Balance column styling for opening and closing
    style_list.append(('TEXTCOLOR', (4, 1), (4, 1), colors.HexColor('#1976d2')))  # Opening
    style_list.append(('TEXTCOLOR', (4, -1), (4, -1), colors.HexColor('#1976d2')))  # Closing
    style_list.append(('FONTNAME', (4, 1), (4, 1), 'Helvetica-Bold'))
    style_list.append(('FONTNAME', (4, -1), (4, -1), 'Helvetica-Bold'))
    
    table.setStyle(TableStyle(style_list))
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Add legend for clarity
    legend_style = ParagraphStyle(
        name="Legend",
        fontSize=9,
        textColor=colors.HexColor('#666666'),
        alignment=0,
        spaceAfter=5
    )
    
    elements.append(Paragraph(
        "<b>Legend:</b> "
        "<font color='#d32f2f'>■</font> Debit (Money Out) | "
        "<font color='#388e3c'>■</font> Credit (Money In) | "
        "<font color='#1976d2'>■</font> Balance",
        legend_style
    ))
    elements.append(Spacer(1, 15))
    
    return opening_balance


def _add_account_summary(elements, styles, account_type, opening_balance, current_balance):
    """Adds account summary section to PDF statement"""
    summary_header_style = ParagraphStyle(
        name="SummaryHeader",
        fontSize=14,
        textColor=colors.white,
        backColor=colors.HexColor('#1f3b57'),
        alignment=1,
        spaceAfter=12,
        spaceBefore=12,
        leading=18
    )
    
    elements.append(Paragraph("Account Summary", summary_header_style))
    elements.append(Spacer(1, 10))
    
    # Calculate total debits and credits
    total_debit = abs(current_balance - opening_balance) if current_balance < opening_balance else 0
    total_credit = abs(current_balance - opening_balance) if current_balance > opening_balance else 0
    
    summary_data = [
        ["Description", "Amount (Rs.)"],
        ["Opening Balance", f"{opening_balance:,.2f}"],
        ["Total Credits (+)", f"{total_credit:,.2f}"],
        ["Total Debits (-)", f"{total_debit:,.2f}"],
        ["Closing Balance", f"{current_balance:,.2f}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[300, 200])
    
    summary_style = [
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5f8d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        
        # Opening balance
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e8f4f8')),
        ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor('#1976d2')),
        ('FONTNAME', (1, 1), (1, 1), 'Helvetica-Bold'),
        
        # Credits (green)
        ('TEXTCOLOR', (1, 2), (1, 2), colors.HexColor('#388e3c')),
        ('FONTNAME', (1, 2), (1, 2), 'Helvetica-Bold'),
        
        # Debits (red)
        ('TEXTCOLOR', (1, 3), (1, 3), colors.HexColor('#d32f2f')),
        ('FONTNAME', (1, 3), (1, 3), 'Helvetica-Bold'),
        
        # Closing balance
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#e8f4f8')),
        ('TEXTCOLOR', (1, 4), (1, 4), colors.HexColor('#1976d2')),
        ('FONTNAME', (0, 4), (1, 4), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 4), (1, 4), 12),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
        ('LINEABOVE', (0, 0), (-1, 0), 2, colors.HexColor('#1f3b57')),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1f3b57')),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#1f3b57')),
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]
    
    summary_table.setStyle(TableStyle(summary_style))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Add disclaimer with better styling
    disclaimer_style = ParagraphStyle(
        name="Disclaimer",
        fontSize=9,
        textColor=colors.HexColor('#666666'),
        alignment=1,
        spaceAfter=10
    )
    
    elements.append(Paragraph(
        "<i>This is a computer-generated statement and does not require a signature or stamp.</i>",
        disclaimer_style
    ))
    
    # Add footer
    footer_style = ParagraphStyle(
        name="Footer",
        fontSize=8,
        textColor=colors.HexColor('#999999'),
        alignment=1
    )
    
    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %B %Y at %I:%M %p')} | For any queries, please contact customer support.",
        footer_style
    ))


def _send_statement_email(email, pdf_file):
    """Sends email with PDF statement attachment"""
    msg = EmailMessage()
    msg["From"] = SENDER_EMAIL
    msg["To"] = email
    msg["Subject"] = f"{BANK_NAME} - Account Statement"
    msg.set_content("Please find attached your account statement.")
    
    with open(pdf_file, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=f"{BANK_NAME}_Account_Statement.pdf"
        )
    
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)
