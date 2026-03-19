"""
Database Manager Module
Handles all database connections, schema initialization, and query execution
"""

import mysql.connector
import streamlit as st
from config.settings import DB_NAME, DB_HOST, DB_USER, DB_PASSWORD


@st.cache_resource
def get_connection():
    """
    Establishes and caches database connection
    Initializes database schema if not exists
    
    Returns:
        mysql.connector.connection: Database connection object
    """
    # Connect to MySQL server
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    
    # Create database if not exists
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    cursor.execute(f"USE {DB_NAME}")
    
    # Initialize schema
    _create_tables(cursor)
    _ensure_columns(cursor)
    _ensure_bigint_account_numbers(cursor)
    
    conn.commit()
    cursor.close()
    return conn


def _create_tables(cursor):
    """
    Creates required database tables if they don't exist
    
    Args:
        cursor: MySQL cursor object
    """
    # Accounts table - PIN stored as VARCHAR to preserve leading zeros
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_number BIGINT PRIMARY KEY,
            name VARCHAR(255),
            email VARCHAR(255),
            balance FLOAT,
            pin VARCHAR(4),
            account_type VARCHAR(50) DEFAULT 'Savings',
            interest_rate FLOAT DEFAULT 3.2
        );
    """)
    
    # Transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            account_number BIGINT,
            type VARCHAR(50),
            amount FLOAT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_number) REFERENCES accounts(account_number)
        );
    """)
    
    # Loans table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            loan_id INT AUTO_INCREMENT PRIMARY KEY,
            account_number BIGINT,
            loan_type VARCHAR(50),
            loan_amount FLOAT,
            interest_rate FLOAT,
            tenure INT,
            remaining_amount FLOAT,
            status VARCHAR(50) DEFAULT 'Active',
            FOREIGN KEY (account_number) REFERENCES accounts(account_number)
        );
    """)


def _ensure_columns(cursor):
    """
    Ensures all required columns exist in tables
    Adds missing columns if necessary
    
    Args:
        cursor: MySQL cursor object
    """
    # Check and add email column
    cursor.execute("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME='accounts' AND COLUMN_NAME='email'
    """, (DB_NAME,))
    
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE accounts ADD COLUMN email VARCHAR(255)")
    
    # Check and add last_interest_date column
    cursor.execute("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME='accounts' AND COLUMN_NAME='last_interest_date'
    """, (DB_NAME,))
    
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE accounts ADD COLUMN last_interest_date DATE")
    
    # Check and convert PIN column from INT to VARCHAR(4) to preserve leading zeros
    cursor.execute("""
        SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME='accounts' AND COLUMN_NAME='pin'
    """, (DB_NAME,))
    
    result = cursor.fetchone()
    if result and result[0].lower() in ['int', 'integer', 'tinyint', 'smallint', 'mediumint', 'bigint']:
        # Convert PIN from INT to VARCHAR(4)
        cursor.execute("ALTER TABLE accounts MODIFY COLUMN pin VARCHAR(4)")


def _ensure_bigint_account_numbers(cursor):
    """
    Ensures account_number columns are BIGINT type
    Handles foreign key constraints during migration
    
    Args:
        cursor: MySQL cursor object
    """
    # Check current column type
    cursor.execute("""
        SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME='accounts' AND COLUMN_NAME='account_number'
    """, (DB_NAME,))
    
    row = cursor.fetchone()
    if row and "bigint" in row[0].lower():
        return  # Already BIGINT
    
    # Get foreign key constraints
    cursor.execute("""
        SELECT CONSTRAINT_NAME, TABLE_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA=%s AND REFERENCED_TABLE_NAME='accounts' 
        AND REFERENCED_COLUMN_NAME='account_number'
    """, (DB_NAME,))
    
    fks = cursor.fetchall()
    
    # Drop foreign keys temporarily
    for fk_name, table_name in fks:
        cursor.execute(f"ALTER TABLE {table_name} DROP FOREIGN KEY {fk_name}")
    
    # Modify column types to BIGINT
    cursor.execute("ALTER TABLE accounts MODIFY account_number BIGINT")
    cursor.execute("ALTER TABLE transactions MODIFY account_number BIGINT")
    cursor.execute("ALTER TABLE loans MODIFY account_number BIGINT")
    
    # Re-add foreign keys
    for fk_name, table_name in fks:
        if table_name == "transactions":
            cursor.execute("""
                ALTER TABLE transactions 
                ADD CONSTRAINT transactions_ibfk_1 
                FOREIGN KEY (account_number) REFERENCES accounts(account_number)
            """)
        elif table_name == "loans":
            cursor.execute("""
                ALTER TABLE loans 
                ADD CONSTRAINT loans_ibfk_1 
                FOREIGN KEY (account_number) REFERENCES accounts(account_number)
            """)


def db_execute(query, params=None, fetchone=False, fetchall=False):
    """
    Executes a database query with optional fetch operations
    
    Args:
        query (str): SQL query to execute
        params (tuple, optional): Query parameters
        fetchone (bool): Whether to fetch one result
        fetchall (bool): Whether to fetch all results
    
    Returns:
        Query result if fetch is requested, None otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params or ())
    
    result = None
    if fetchone:
        result = cursor.fetchone()
    elif fetchall:
        result = cursor.fetchall()
    
    conn.commit()
    cursor.close()
    return result
