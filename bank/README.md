# 🏦 SNJ Bank — Digital Banking Application

A full-featured digital banking web application built with **Python** and **Streamlit**, featuring OTP-based authentication, secure PIN-protected transactions, loan management, EMI calculator, and professional PDF statement generation.

---

## 📸 Features

### 🔐 Authentication
- Email OTP-based registration and login
- Session timeout after 15 minutes of inactivity
- PIN-protected transactions (Deposit, Withdraw, Transfer)
- OTP-secured PIN change

### 💳 Transactions
- Deposit with PIN verification
- Withdrawal with minimum balance enforcement and penalty
- Fund transfer between accounts with PIN verification
- Passbook auto-generation (local `.txt` file)

### 📊 Account Management
- Dashboard with account overview
- Mini statement (last 5 transactions)
- Full PDF statement via email (color-coded, professional)
- Transaction history pie chart
- Monthly interest calculation

### 💰 Loan Management
- Apply for Home, Gold, or Personal loans
- EMI preview before applying
- View all loans with monthly EMI and repayment progress
- Pay EMI with balance deduction

### 🧮 EMI Calculator
- Standalone EMI calculator tool
- Shows monthly EMI, total interest, total payable
- Visual bar chart (Principal vs Interest)
- Detailed payment summary table

---

## 🗂️ Project Structure

```
snj-bank/
├── main_new.py                  # Application entry point
│
├── config/
│   └── settings.py              # All configuration (reads from .env)
│
├── database/
│   └── db_manager.py            # DB connection, schema, query helper
│
├── services/
│   ├── auth_service.py          # OTP, registration, login, session
│   ├── account_service.py       # Balance, interest, PIN change
│   ├── transaction_service.py   # Deposit, withdraw, transfer, passbook
│   ├── loan_service.py          # Loan apply, EMI calc, repayment
│   └── email_service.py         # Email sending, PDF statement generation
│
└── ui/
    └── render_views.py          # All Streamlit page components
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.8+
- MySQL Server running locally
- Gmail account with [App Password](https://support.google.com/accounts/answer/185833) enabled

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/snj-bank.git
cd snj-bank
```

### 2. Create a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env
```

Now open `.env` and fill in your values:

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password

SENDER_EMAIL=your_email@gmail.com
APP_PASSWORD=your_gmail_app_password
```

> **Note:** Use a Gmail [App Password](https://support.google.com/accounts/answer/185833), not your real Gmail password.

### 5. Run the Application

```bash
streamlit run main_new.py
```

The app will open at `http://localhost:8501`

---

## 🔑 Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DB_HOST` | MySQL host | `localhost` |
| `DB_USER` | MySQL username | `root` |
| `DB_PASSWORD` | MySQL password | `yourpassword` |
| `DB_NAME` | Database name | `bankaccountdatabase` |
| `SENDER_EMAIL` | Gmail address for sending emails | `you@gmail.com` |
| `APP_PASSWORD` | Gmail App Password | `xxxx xxxx xxxx xxxx` |

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| [Python 3.8+](https://python.org) | Core language |
| [Streamlit](https://streamlit.io) | Web UI framework |
| [MySQL](https://mysql.com) | Database |
| [mysql-connector-python](https://pypi.org/project/mysql-connector-python/) | DB driver |
| [ReportLab](https://www.reportlab.com/) | PDF generation |
| [Matplotlib](https://matplotlib.org/) | Charts & graphs |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | Environment variables |
| [smtplib](https://docs.python.org/3/library/smtplib.html) | Email sending (stdlib) |

---

## 📋 Database Schema

The app auto-creates the database and tables on first run.

```sql
accounts (
    account_number  BIGINT PRIMARY KEY,
    name            VARCHAR(255),
    email           VARCHAR(255),
    balance         FLOAT,
    pin             VARCHAR(4),       -- Stored as string to preserve leading zeros
    account_type    VARCHAR(50),
    interest_rate   FLOAT,
    last_interest_date DATE
)

transactions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    account_number  BIGINT,
    type            VARCHAR(50),
    amount          FLOAT,
    timestamp       TIMESTAMP
)

loans (
    loan_id         INT AUTO_INCREMENT PRIMARY KEY,
    account_number  BIGINT,
    loan_type       VARCHAR(50),
    loan_amount     FLOAT,
    interest_rate   FLOAT,
    tenure          INT,
    remaining_amount FLOAT,
    status          VARCHAR(50)
)
```

---

## 🔒 Security Features

- **OTP Authentication** — Email-based OTP for login and registration
- **PIN Verification** — 4-digit PIN required for every transaction
- **Session Timeout** — Auto-logout after 15 minutes of inactivity
- **OTP Expiry** — OTPs expire after 3 minutes
- **Max Attempts** — OTP locked after 3 failed attempts
- **Leading Zero PINs** — PINs like `0507` stored correctly as strings
- **Environment Variables** — Credentials never hardcoded

---

## 📧 Email Features

- OTP emails for registration, login, and PIN change
- Welcome email on account creation
- Full account statement as a **color-coded PDF attachment**
  - 🔴 Red — Debits (money out)
  - 🟢 Green — Credits (money in)
  - 🔵 Blue — Running balance

---

## 🧮 EMI Formula

```
EMI = [P × r × (1 + r)^n] / [(1 + r)^n - 1]

P = Principal loan amount
r = Monthly interest rate (annual rate / 12 / 100)
n = Tenure in months
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**SNJ Bank Development Team**

---

> ⚠️ **Disclaimer:** This is a demo/educational project. Do not use real banking credentials or sensitive personal data.
