#!/usr/bin/env python3
"""
Final accurate product count analysis
"""

import pandas as pd
import numpy as np

def count_actual_products(file_path):
    """
    Count actual products by parsing the structured data correctly
    """
    print(f"Final Product Count Analysis: {file_path}")
    print("=" * 60)
    
    # Read the data starting from row 11 (where headers are) with proper headers
    df = pd.read_excel(file_path, sheet_name='Sheet1', skiprows=10, header=0)
    
    print(f"Data shape after proper parsing: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print()
    
    # Remove completely empty rows
    df_clean = df.dropna(how='all')
    print(f"Rows after removing empty: {df_clean.shape[0]}")
    
    # Count actual product rows (rows with valid data in all key columns)
    product_count = 0
    category_count = 0
    
    categories = []
    products = []
    
    print("\nAnalyzing data structure:")
    print("-" * 40)
    
    for idx, row in df_clean.iterrows():
        no_val = row.iloc[0] if len(row) > 0 else None
        desc_val = row.iloc[1] if len(row) > 1 else None
        unit_val = row.iloc[2] if len(row) > 2 else None
        price_val = row.iloc[3] if len(row) > 3 else None
        
        # Skip header row
        if str(desc_val).lower() == 'description':
            continue
            
        # Check if this is a category header (only description filled, no number/price)
        if (pd.notna(desc_val) and str(desc_val).strip() and 
            (pd.isna(no_val) or str(no_val).strip() == '') and
            (pd.isna(price_val) or str(price_val).strip() == '')):
            category_count += 1
            categories.append(str(desc_val).strip())
            print(f"Category {category_count}: {desc_val}")
            continue
        
        # Check if this is a product row (has number, description, unit, price)
        if (pd.notna(desc_val) and str(desc_val).strip() and
            pd.notna(price_val) and str(price_val).strip()):
            product_count += 1
            products.append({
                'no': no_val,
                'description': desc_val,
                'unit': unit_val,
                'price': price_val
            })
            
            if product_count <= 10:  # Show first 10 products
                print(f"Product {product_count:3d}: {no_val} | {desc_val} | {unit_val} | {price_val}")
    
    print(f"\n{'='*60}")
    print(f"FINAL RESULTS:")
    print(f"{'='*60}")
    print(f"Total categories found: {category_count}")
    print(f"Total products found: {product_count}")
    print(f"Categories: {categories}")
    
    # Show sample of products by category
    print(f"\nSample products by category:")
    current_category = None
    category_products = {}
    
    for idx, row in df_clean.iterrows():
        desc_val = row.iloc[1] if len(row) > 1 else None
        price_val = row.iloc[3] if len(row) > 3 else None
        
        if str(desc_val).lower() == 'description':
            continue
            
        # Category
        if (pd.notna(desc_val) and str(desc_val).strip() and 
            (pd.isna(price_val) or str(price_val).strip() == '')):
            current_category = str(desc_val).strip()
            category_products[current_category] = []
            
        # Product
        elif (pd.notna(desc_val) and str(desc_val).strip() and
              pd.notna(price_val) and str(price_val).strip() and
              current_category):
            category_products[current_category].append(str(desc_val).strip())
    
    for category, prods in category_products.items():
        print(f"\n{category}: {len(prods)} products")
        for i, prod in enumerate(prods[:3]):  # Show first 3 products
            print(f"  - {prod}")
        if len(prods) > 3:
            print(f"  ... and {len(prods) - 3} more")
    
    return product_count, category_count

if __name__ == "__main__":
    file_path = "/Users/denisdomashenko/price_list_analyzer/DOC-20250428-WA0004..xlsx"
    count_actual_products(file_path)