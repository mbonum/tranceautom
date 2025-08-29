"""
Simple Country Processor - Clean and Final Solution
Creates one final CSV with country columns and dates - no intermediate files
"""

import pandas as pd
import os
from typing import Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_countries_list() -> list:
    """
    Get the complete list of countries as specified by user.
    
    Returns:
        list: List of all country codes
    """
    return [
        'AL', 'AM', 'AT', 'AZ', 'BA', 'BE', 'BG', 'BH', 'BR', 'BY', 'CH', 'CN', 'CO', 'CY', 'CZ', 
        'DE', 'DK', 'EE', 'ES', 'FL', 'FR', 'GB', 'GE', 'GR', 'HK', 'HR', 'HU', 'IE', 'IL', 
        'IT', 'JO', 'JP', 'KW', 'KZ', 'LB', 'LT', 'LU', 'LV', 'MA', 'MD', 'MK', 'MO', 'MT', 
        'MX', 'NL', 'PL', 'PT', 'QA', 'RO', 'RS', 'RU', 'SA', 'SE', 'SI', 'SK', 'TN', 'TR', 
        'TW', 'UA', 'UK', 'US', 'UZ', 'XK'
    ]


def get_country_group_mapping() -> dict:
    """
    Map column patterns to their respective countries.
    
    Returns:
        dict: Mapping of column patterns to country lists
    """
    return {
        'ALBGBYCYEEGEGRHRILLBLTLVMDMKRORSRUSITRXK': ['AL', 'BG', 'BY', 'CY', 'EE', 'GE', 'GR', 'HR', 'IL', 'LB', 'LT', 'LV', 'MD', 'MK', 'RO', 'RS', 'RU', 'SI', 'TR', 'XK'],
        'AEAMAZBABHCNHKIEITJOKWKZMTQASAUAUZ': ['AE', 'AM', 'AZ', 'BA', 'BH', 'CN', 'HK', 'IE', 'IT', 'JO', 'KW', 'KZ', 'MT', 'QA', 'SA', 'UA', 'UZ'],
        'ESFRPT': ['ES', 'FR', 'PT'],
        'ATBECHCZDEDKHULUMAMXNLPLSESKTNUKUS': ['AT', 'BE', 'CH', 'CZ', 'DE', 'DK', 'HU', 'LU', 'MA', 'MX', 'NL', 'PL', 'SE', 'SK', 'TN', 'UK', 'US'],
        'ESIE': ['ES', 'IE'],
        'BECZDEDKFRPLUK': ['BE', 'CZ', 'DE', 'DK', 'FR', 'PL', 'UK'],
        'ATCHSE': ['AT', 'CH', 'SE']
    }


def load_and_clean_excel_data(excel_file: str) -> pd.DataFrame:
    """
    Load and clean data directly from Excel file.
    
    Args:
        excel_file (str): Path to Excel file
        
    Returns:
        pd.DataFrame: Cleaned DataFrame
    """
    try:
        logger.info(f"Loading Excel file: {excel_file}")
        
        # Load the PIANIFICAZIONE sheet
        df = pd.read_excel(excel_file, sheet_name="PIANIFICAZIONE")
        
        # Find the header row (row with most non-null values)
        non_null_counts = df.notna().sum(axis=1)
        header_row = non_null_counts.idxmax()
        
        logger.info(f"Header row identified at index: {header_row}")
        
        # Use the header row as column names and take data from next row onwards
        if header_row > 0:
            new_columns = df.iloc[header_row].fillna('').astype(str).tolist()
            df = df.iloc[header_row + 1:].reset_index(drop=True)
            df.columns = new_columns
        
        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]
        
        # Remove completely empty rows and columns
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Remove only real test data (not AAP which is a valid date value)
        # Only remove rows that are clearly test data in product identification columns
        test_indicators = ['TEST', 'PROVA', 'DUMMY']
        mask = pd.Series(True, index=df.index)
        
        # Only check specific columns that might contain test data, not date columns
        test_check_columns = [col for col in df.columns if any(keyword in col.lower() for keyword in ['sku', 'articolo', 'descrizione']) and df[col].dtype == 'object']
        
        for col in test_check_columns:
            for indicator in test_indicators:
                col_mask = ~df[col].astype(str).str.contains(indicator, case=False, na=False)
                mask = mask & col_mask
        
        df = df[mask]
        
        logger.info(f"Data cleaned - Final shape: {df.shape}")
        
        return df
    
    except Exception as e:
        logger.error(f"Error loading Excel data: {str(e)}")
        return pd.DataFrame()


def create_country_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create individual country columns with their respective dates.
    
    Args:
        df (pd.DataFrame): Input DataFrame with grouped country columns
        
    Returns:
        pd.DataFrame: DataFrame with individual country columns
    """
    try:
        logger.info("Creating individual country columns...")
        
        # Get the mapping
        country_mapping = get_country_group_mapping()
        all_countries = get_countries_list()
        
        # Identify the core product columns (non-country columns)
        country_group_columns = []
        for col in df.columns:
            # Check for country patterns in column names (with dashes instead of just the pattern)
            col_clean = col.replace('-', '').replace(' ', '').upper()
            for pattern in country_mapping.keys():
                if pattern in col_clean or any(country_code in col for country_code in ['AL-BG', 'AE-AM', 'ES-FR', 'AT-BE', 'BE-CZ', 'AT-CH']):
                    country_group_columns.append(col)
                    break
        
        logger.info(f"Found country group columns: {country_group_columns}")
        
        # Core product columns (everything except country group columns)
        core_columns = [col for col in df.columns if col not in country_group_columns]
        
        # Start with core product data
        result_df = df[core_columns].copy()
        
        # Add individual country columns
        for country_code in sorted(all_countries):
            result_df[f"country_{country_code}"] = None
        
        # Fill country columns with dates from appropriate group columns
        for index, row in df.iterrows():
            for group_col in country_group_columns:
                if group_col in df.columns and pd.notna(row[group_col]):
                    date_value = row[group_col]
                    
                    # Map column to countries based on its pattern
                    countries_for_this_col = []
                    
                    if 'AL-BG' in group_col:  # AL-BG-BY-CY-EE-GE-GR-HR-IL-LB-LT-LV-MD-MK-RO-RS-RU-SI-TR-XK
                        countries_for_this_col = ['AL', 'BG', 'BY', 'CY', 'EE', 'GE', 'GR', 'HR', 'IL', 'LB', 'LT', 'LV', 'MD', 'MK', 'RO', 'RS', 'RU', 'SI', 'TR', 'XK']
                    elif 'AE-AM' in group_col:  # AE-AM-AZ-BA-BH-CN-HK-IE-IT-JO-KW-KZ-MT-QA-SA-UA-UZ
                        countries_for_this_col = ['AE', 'AM', 'AZ', 'BA', 'BH', 'CN', 'HK', 'IE', 'IT', 'JO', 'KW', 'KZ', 'MT', 'QA', 'SA', 'UA', 'UZ']
                    elif 'ES-FR-PT' in group_col:  # ES-FR-PT
                        countries_for_this_col = ['ES', 'FR', 'PT']
                    elif 'AT-BE-CH' in group_col and 'AT-CH-SE' not in group_col:  # AT-BE-CH-CZ-DE-DK-HU-LU-MA-MX-NL-PL-SE-SK-TN-UK-US
                        countries_for_this_col = ['AT', 'BE', 'CH', 'CZ', 'DE', 'DK', 'HU', 'LU', 'MA', 'MX', 'NL', 'PL', 'SE', 'SK', 'TN', 'UK', 'US']
                    elif 'ES-IE' in group_col:  # ES-IE
                        countries_for_this_col = ['ES', 'IE']
                    elif 'BE-CZ-DE' in group_col:  # BE-CZ-DE-DK-FR-PL-UK
                        countries_for_this_col = ['BE', 'CZ', 'DE', 'DK', 'FR', 'PL', 'UK']
                    elif 'AT-CH-SE' in group_col:  # AT-CH-SE
                        countries_for_this_col = ['AT', 'CH', 'SE']
                    
                    # Set the date for all countries in this group
                    for country in countries_for_this_col:
                        if country in all_countries:
                            result_df.loc[index, f"country_{country}"] = date_value
        
        logger.info(f"Country columns created - New shape: {result_df.shape}")
        logger.info(f"Added {len(all_countries)} country columns")
        
        return result_df
    
    except Exception as e:
        logger.error(f"Error creating country columns: {str(e)}")
        return df


def save_final_csv(df: pd.DataFrame, output_file: str) -> bool:
    """
    Save the final DataFrame as CSV.
    
    Args:
        df (pd.DataFrame): DataFrame to save
        output_file (str): Output file path
        
    Returns:
        bool: True if successful
    """
    try:
        # Use comma separator to avoid issues with semicolons
        df.to_csv(output_file, index=False, encoding='utf-8', sep=',')
        logger.info(f"Final CSV saved: {output_file}")
        logger.info(f"Final data shape: {df.shape}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error saving CSV: {str(e)}")
        return False


def process_excel_to_final_csv(excel_file: str, output_file: str = "pianificazione_final_clean.csv") -> bool:
    """
    Complete process: Excel to final clean CSV with country columns.
    
    Args:
        excel_file (str): Input Excel file path
        output_file (str): Output CSV file path
        
    Returns:
        bool: True if successful
    """
    try:
        logger.info("=== STARTING COMPLETE EXCEL TO FINAL CSV PROCESS ===")
        
        # Step 1: Load and clean Excel data
        df = load_and_clean_excel_data(excel_file)
        if df.empty:
            logger.error("Failed to load data from Excel")
            return False
        
        # Step 2: Create country columns
        df_with_countries = create_country_columns(df)
        
        # Step 3: Save final CSV
        success = save_final_csv(df_with_countries, output_file)
        
        if success:
            logger.info("=== PROCESS COMPLETED SUCCESSFULLY ===")
            logger.info(f"Input: {excel_file}")
            logger.info(f"Output: {output_file}")
            logger.info(f"Products processed: {len(df_with_countries)}")
            logger.info(f"Countries added: {len(get_countries_list())}")
        
        return success
    
    except Exception as e:
        logger.error(f"Error in complete process: {str(e)}")
        return False


def analyze_final_data(csv_file: str) -> dict:
    """
    Analyze the final CSV data.
    
    Args:
        csv_file (str): Path to final CSV file
        
    Returns:
        dict: Analysis results
    """
    try:
        df = pd.read_csv(csv_file)
        
        # Count non-null values for each country
        country_columns = [col for col in df.columns if col.startswith('country_')]
        country_stats = {}
        
        for col in country_columns:
            country_code = col.replace('country_', '')
            non_null_count = df[col].notna().sum()
            country_stats[country_code] = non_null_count
        
        analysis = {
            'total_products': len(df),
            'total_countries': len(country_columns),
            'country_coverage': country_stats,
            'top_countries': dict(sorted(country_stats.items(), key=lambda x: x[1], reverse=True)[:10])
        }
        
        return analysis
    
    except Exception as e:
        logger.error(f"Error analyzing data: {str(e)}")
        return {}


def main():
    excel_file = "Pianificazione_MARE25.xlsx"     # ← Input automatico
    output_file = "pianificazione_final_clean.csv"  # ← Output automatico
    
    # Controlla se il file Excel esiste
    if not os.path.exists(excel_file):
        print(f"❌ Excel file not found: {excel_file}")
        return
    
    # Elabora Excel → CSV pulito e completo
    success = process_excel_to_final_csv(excel_file, output_file)
    
    if success:
        print(f"✅ SUCCESS! Final CSV created: {output_file}")
        # + statistiche automatiche


if __name__ == "__main__":
    main()
