#!/usr/bin/env python3
"""
Deep content analysis of the Excel file to understand the actual product structure
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path

def deep_content_analysis(file_path):
    """
    Perform deep analysis of the Excel content to understand product structure
    """
    print(f"Deep Content Analysis: {file_path}")
    print("=" * 60)
    
    # Focus on Sheet1 since that's where the data is
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    
    print(f"Sheet1 Raw Data Structure:")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    # Let's examine the content row by row to understand the structure
    print("\n" + "=" * 60)
    print("ROW-BY-ROW ANALYSIS (first 30 rows):")
    print("=" * 60)
    
    for i in range(min(30, len(df))):
        row = df.iloc[i]
        row_content = []
        for j, val in enumerate(row):
            if pd.notna(val) and str(val).strip():
                row_content.append(f"Col{j}: '{val}'")
        
        if row_content:
            print(f"Row {i:3d}: {' | '.join(row_content)}")
    
    print("\n" + "=" * 60)
    print("LOOKING FOR ACTUAL PRODUCT DATA:")
    print("=" * 60)
    
    # Try to identify where the actual product list starts
    product_start_row = None
    header_patterns = ['product', 'item', 'nama', 'barang', 'price', 'harga', 'qty', 'unit']
    
    for i, row in df.iterrows():
        row_text = ' '.join([str(val).lower() for val in row if pd.notna(val)])
        if any(pattern in row_text for pattern in header_patterns):
            print(f"Potential header row {i}: {row_text}")
            if product_start_row is None:
                product_start_row = i
    
    # Look for rows that might contain products based on patterns
    print("\n" + "=" * 60)
    print("POTENTIAL PRODUCT ROWS:")
    print("=" * 60)
    
    product_rows = []
    price_pattern = re.compile(r'[\d,]+\.?\d*')  # Pattern for prices
    
    for i, row in df.iterrows():
        if i < 10:  # Skip likely header area
            continue
            
        # Check if row has content that looks like product data
        non_null_vals = [val for val in row if pd.notna(val) and str(val).strip()]
        
        if len(non_null_vals) >= 2:  # At least 2 values
            # Look for patterns that suggest this is a product row
            has_text = any(isinstance(val, str) and len(str(val).strip()) > 3 for val in non_null_vals)
            has_numbers = any(str(val).replace(',', '').replace('.', '').isdigit() for val in non_null_vals)
            
            if has_text:
                product_rows.append((i, row))
                if len(product_rows) <= 20:  # Show first 20 products
                    row_desc = ' | '.join([f"'{val}'" for val in non_null_vals])
                    print(f"Product Row {i:3d}: {row_desc}")
    
    print(f"\nTotal potential product rows found: {len(product_rows)}")
    
    # Try different parsing strategies
    print("\n" + "=" * 60)
    print("ALTERNATIVE PARSING STRATEGIES:")
    print("=" * 60)
    
    # Strategy 1: Skip header rows and use first data row as header
    for skip_rows in range(10, 20):
        try:
            df_alt = pd.read_excel(file_path, sheet_name='Sheet1', skiprows=skip_rows)
            non_empty_count = df_alt.dropna(how='all').shape[0]
            if non_empty_count > 0:
                print(f"Skip {skip_rows} rows: {non_empty_count} data rows, columns: {list(df_alt.columns)}")
                if non_empty_count > 50 and non_empty_count < 150:  # Likely range for products
                    print(f"  -> This might be the actual product data! Sample:")
                    sample = df_alt.dropna(how='all').head(3)
                    for idx, row in sample.iterrows():
                        print(f"     {[val for val in row if pd.notna(val)]}")
        except:
            continue
    
    # Strategy 2: Look for table-like structure
    print("\n" + "=" * 60)
    print("LOOKING FOR TABLE STRUCTURE:")
    print("=" * 60)
    
    # Find rows where multiple columns have data
    table_start = None
    consecutive_data_rows = 0
    
    for i, row in df.iterrows():
        non_null_count = row.count()
        if non_null_count >= 3:  # Row with data in at least 3 columns
            if table_start is None:
                table_start = i
            consecutive_data_rows += 1
        else:
            if consecutive_data_rows > 10:  # Found a substantial table
                print(f"Table found: rows {table_start} to {i-1} ({consecutive_data_rows} rows)")
                break
            table_start = None
            consecutive_data_rows = 0
    
    if table_start is not None:
        print(f"\nTable structure starting at row {table_start}:")
        table_df = df.iloc[table_start:table_start + min(10, consecutive_data_rows)]
        print(table_df.to_string())

if __name__ == "__main__":
    file_path = "/Users/denisdomashenko/price_list_analyzer/DOC-20250428-WA0004..xlsx"
    deep_content_analysis(file_path)