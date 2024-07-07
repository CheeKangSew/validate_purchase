# -*- coding: utf-8 -*-
"""
Created on Sun Jul  7 10:35:28 2024

@author: CK
"""

import streamlit as st
import pandas as pd
from io import StringIO

def load_and_prepare_data(file1, file2):
    # Load the two CSV files
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    # Convert the date columns to datetime
    df1['Date Time'] = pd.to_datetime(df1['Date Time'], format='%d/%m/%Y %H:%M', errors='coerce')
    df2['TransactionDateTime'] = pd.to_datetime(df2['TransactionDateTime'], format='%d/%m/%Y %H:%M', errors='coerce')

    # Convert numeric columns to float
    df1['Transaction Amount (RM)'] = pd.to_numeric(df1['Transaction Amount (RM)'], errors='coerce')
    df2['Amount'] = pd.to_numeric(df2['Amount'], errors='coerce')

    # Filter necessary columns for matching
    df1_filtered = df1[['Date Time', 'Transaction Amount (RM)', 'Vehicle Number']]
    df2_filtered = df2[['TransactionDateTime', 'Amount', 'VehicleRegistrationNo']]

    # Rename columns for clarity
    df1_filtered.rename(columns={'Date Time': 'TransactionDateTime', 'Transaction Amount (RM)': 'Amount1', 'Vehicle Number': 'VehicleNumber1'}, inplace=True)
    df2_filtered.rename(columns={'Amount': 'Amount2', 'VehicleRegistrationNo': 'VehicleNumber2'}, inplace=True)
    
    return df1, df1_filtered, df2_filtered

def match_transactions(df1_filtered, df2_filtered, time_buffer_hours=1):
    # Create an empty DataFrame to store matched transactions
    matched_transactions = pd.DataFrame(columns=['TransactionDateTime', 'Amount1', 'VehicleNumber1', 'Amount2', 'VehicleNumber2'])

    # Loop through each row in the first DataFrame
    for index1, row1 in df1_filtered.iterrows():
        # Find rows in the second DataFrame that match the vehicle number
        df2_vehicle_match = df2_filtered[df2_filtered['VehicleNumber2'] == row1['VehicleNumber1']]
        
        # Further filter rows based on the time buffer of +/- 1 hour
        time_buffer = pd.Timedelta(hours=time_buffer_hours)
        df2_time_match = df2_vehicle_match[
            (df2_vehicle_match['TransactionDateTime'] >= (row1['TransactionDateTime'] - time_buffer)) &
            (df2_vehicle_match['TransactionDateTime'] <= (row1['TransactionDateTime'] + time_buffer))
        ]
        
        # Find matches where the transaction amounts are the same
        final_matches = df2_time_match[abs(df2_time_match['Amount2'] - row1['Amount1']) < 0.01]  # Allow for minor differences in amounts
        
        # Append matched transactions to the matched_transactions DataFrame
        for index2, row2 in final_matches.iterrows():
            matched_transactions = matched_transactions.append({
                'TransactionDateTime': row1['TransactionDateTime'],
                'Amount1': row1['Amount1'],
                'VehicleNumber1': row1['VehicleNumber1'],
                'Amount2': row2['Amount2'],
                'VehicleNumber2': row2['VehicleNumber2']
            }, ignore_index=True)
    
    return matched_transactions

def count_transactions(df1_filtered, df2_filtered, matched_transactions):
    total_transactions_file1 = df1_filtered.shape[0]
    total_transactions_file2 = df2_filtered.shape[0]
    total_matched_transactions = matched_transactions.shape[0]

    return total_transactions_file1, total_transactions_file2, total_matched_transactions

def add_matched_column(df1, matched_transactions):
    # Create a new column in df1 to indicate whether the transaction is matched
    df1['Matched'] = df1.apply(
        lambda row: any(
            (matched_transactions['TransactionDateTime'] == row['Date Time']) &
            (matched_transactions['Amount1'] == row['Transaction Amount (RM)']) &
            (matched_transactions['VehicleNumber1'] == row['Vehicle Number'])
        ), axis=1
    )
    
    return df1

def main():
    st.title("Transaction Matching Application")

    # Upload files
    file1 = st.file_uploader("Upload the fleetcard CSV file from Petron", type="csv")
    file2 = st.file_uploader("Upload the transaction CSV file from Soliduz", type="csv")

    if file1 and file2:
        # Time buffer slider
        time_buffer_hours = st.slider("Select time buffer in hours", min_value=0, max_value=24, value=1, step=1)

        # Process files
        df1, df1_filtered, df2_filtered = load_and_prepare_data(file1, file2)
        matched_transactions = match_transactions(df1_filtered, df2_filtered, time_buffer_hours)

        total_transactions_file1, total_transactions_file2, total_matched_transactions = count_transactions(df1_filtered, df2_filtered, matched_transactions)
        
        st.write(f"Total transactions in Petron file: {total_transactions_file1}")
        st.write(f"Total transactions in Soliduz file: {total_transactions_file2}")
        st.write(f"Total matched transactions: {total_matched_transactions}")

        # Add matched column to df1
        df1_with_matched = add_matched_column(df1, matched_transactions)
        
        # Display matched transactions
        st.subheader("Matched Transactions")
        st.dataframe(matched_transactions)
        
        # Display the first file with matched column
        st.subheader("Petron File with Matched Column")
        st.dataframe(df1_with_matched)

        # Download buttons
        st.download_button(
            label="Download Matched Transactions",
            data=matched_transactions.to_csv(index=False).encode('utf-8'),
            file_name='matched_transactions.csv',
            mime='text/csv'
        )

        st.download_button(
            label="Download Petron File with Matched Column",
            data=df1_with_matched.to_csv(index=False).encode('utf-8'),
            file_name='TransactionListing_with_matched.csv',
            mime='text/csv'
        )

if __name__ == "__main__":
    main()
