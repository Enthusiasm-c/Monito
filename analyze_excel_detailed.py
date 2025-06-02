#!/usr/bin/env python3
"""
Detailed Excel file analysis script to understand structure and content
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

def analyze_excel_file(file_path):
    """
    Analyze Excel file structure and content in detail
    """
    print(f"Analyzing Excel file: {file_path}")
    print("=" * 60)
    
    try:
        # Read all sheet names first
        xl_file = pd.ExcelFile(file_path)
        sheet_names = xl_file.sheet_names
        
        print(f"Number of sheets: {len(sheet_names)}")
        print(f"Sheet names: {sheet_names}")
        print("\n" + "=" * 60)
        
        total_product_entries = 0
        
        for i, sheet_name in enumerate(sheet_names):
            print(f"\nSheet {i+1}: '{sheet_name}'")
            print("-" * 40)
            
            try:
                # Read the sheet
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                print(f"Raw shape: {df.shape} (rows x columns)")
                
                # Show column names
                print(f"Columns: {list(df.columns)}")
                
                # Count non-empty rows
                non_empty_rows = df.dropna(how='all').shape[0]
                print(f"Non-empty rows: {non_empty_rows}")
                
                # Show first few rows to understand structure
                print("\nFirst 10 rows:")
                print(df.head(10).to_string())
                
                # Try to identify product entries
                # Look for rows that might contain product data
                potential_products = 0
                
                # Check for rows with some data in multiple columns
                for idx, row in df.iterrows():
                    non_null_count = row.count()
                    if non_null_count >= 2:  # At least 2 non-null values
                        # Check if it's not just headers
                        has_text = any(isinstance(val, str) and len(str(val).strip()) > 0 for val in row if pd.notna(val))
                        has_numbers = any(isinstance(val, (int, float)) and pd.notna(val) for val in row)
                        
                        if has_text and (has_numbers or non_null_count >= 3):
                            potential_products += 1
                
                print(f"Potential product entries: {potential_products}")
                total_product_entries += potential_products
                
                # Show some sample data rows
                if not df.empty:
                    print("\nSample data rows (non-empty):")
                    sample_df = df.dropna(how='all').head(5)
                    if not sample_df.empty:
                        print(sample_df.to_string())
                
                # Check for common price list patterns
                text_columns = df.select_dtypes(include=['object']).columns
                numeric_columns = df.select_dtypes(include=[np.number]).columns
                
                print(f"\nText columns: {list(text_columns)}")
                print(f"Numeric columns: {list(numeric_columns)}")
                
                # Look for price-related keywords
                price_keywords = ['price', 'harga', 'cost', 'rate', 'amount', 'rp', 'rupiah']
                price_columns = []
                for col in df.columns:
                    col_str = str(col).lower()
                    if any(keyword in col_str for keyword in price_keywords):
                        price_columns.append(col)
                
                if price_columns:
                    print(f"Potential price columns: {price_columns}")
                
                # Look for product name patterns
                product_keywords = ['product', 'item', 'nama', 'barang', 'description', 'desc']
                product_columns = []
                for col in df.columns:
                    col_str = str(col).lower()
                    if any(keyword in col_str for keyword in product_keywords):
                        product_columns.append(col)
                
                if product_columns:
                    print(f"Potential product name columns: {product_columns}")
                
            except Exception as e:
                print(f"Error reading sheet '{sheet_name}': {str(e)}")
                
        print("\n" + "=" * 60)
        print(f"SUMMARY:")
        print(f"Total sheets: {len(sheet_names)}")
        print(f"Total potential product entries across all sheets: {total_product_entries}")
        
        # Additional analysis - try to read with different parameters
        print("\n" + "=" * 60)
        print("ADDITIONAL ANALYSIS - Different reading strategies:")
        
        for sheet_name in sheet_names:
            print(f"\nAnalyzing '{sheet_name}' with different strategies:")
            
            # Strategy 1: Skip potential header rows
            try:
                df_skip1 = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=1)
                print(f"  Skip 1 row: {df_skip1.dropna(how='all').shape[0]} non-empty rows")
            except:
                pass
                
            # Strategy 2: Skip more header rows
            try:
                df_skip2 = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=2)
                print(f"  Skip 2 rows: {df_skip2.dropna(how='all').shape[0]} non-empty rows")
            except:
                pass
                
            # Strategy 3: No header
            try:
                df_noheader = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                print(f"  No header: {df_noheader.dropna(how='all').shape[0]} non-empty rows")
            except:
                pass
        
    except Exception as e:
        print(f"Error analyzing file: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    file_path = "/Users/denisdomashenko/price_list_analyzer/DOC-20250428-WA0004..xlsx"
    
    if not Path(file_path).exists():
        print(f"File not found: {file_path}")
        sys.exit(1)
    
    analyze_excel_file(file_path)