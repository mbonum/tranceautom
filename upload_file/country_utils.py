#!/usr/bin/env python3
"""
Country and Date Utilities for Tranche Automation
Integrates the working logic from generate_product_countries.py and generate_product_countries_v2.py
"""

import re
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class CountryManager:
    """
    Manages the complete list of countries and country-related operations
    """
    
    # Complete list of countries from e-commerce (from your working scripts)
    ALL_COUNTRIES = [
        'AL', 'AM', 'AT', 'AZ', 'BA', 'BE', 'BG', 'BH', 'BR', 'BY', 'CH', 'CN', 'CO', 'CY', 'CZ', 
        'DE', 'DK', 'EE', 'ES', 'FL', 'FR', 'GB', 'GE', 'GR', 'HK', 'HR', 'HU', 'IE', 'IL', 
        'IT', 'JO', 'JP', 'KW', 'KZ', 'LB', 'LT', 'LU', 'LV', 'MA', 'MD', 'MK', 'MO', 'MT', 
        'MX', 'NL', 'PL', 'PT', 'QA', 'RO', 'RS', 'RU', 'SA', 'SE', 'SI', 'SK', 'TN', 'TR', 
        'TW', 'UA', 'UK', 'US', 'UZ', 'XK'
    ]
    
    @classmethod
    def get_all_countries(cls) -> List[str]:
        """
        Returns the complete list of supported countries
        """
        return cls.ALL_COUNTRIES.copy()
    
    @classmethod
    def is_valid_country(cls, country_code: str) -> bool:
        """
        Check if a country code is valid
        """
        return country_code.upper() in cls.ALL_COUNTRIES
    
    @classmethod
    def validate_countries(cls, countries: List[str]) -> Dict[str, bool]:
        """
        Validate a list of country codes
        
        Returns:
            Dict mapping country_code -> is_valid
        """
        return {country: cls.is_valid_country(country) for country in countries}


class TrancheDateConverter:
    """
    Converts tranche numbers and names to specific dates
    Based on the working logic from generate_product_countries.py
    """
    
    # Month names for date formatting
    MONTH_NAMES = [
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ]
    
    @classmethod
    def convert_tranche_to_date(cls, tranche: str) -> str:
        """
        Converts a tranche number/name to a formatted date string
        
        Logic from generate_product_countries.py:
        - AAP -> Dec. 31, 2030 (ASAP)
        - Totale complessivo -> Dec. 31, 2030
        - 1-12 -> months 2025 (Jan 15 2025 - Dec 15 2025)
        - 13-24 -> months 2026 (Jan 15 2026 - Dec 15 2026)
        - >24 -> 2027
        
        Args:
            tranche: Tranche number or name (string)
            
        Returns:
            Formatted date string like "Jan. 15, 2025"
        """
        if not tranche:
            return 'Dec. 31, 2030'
            
        tranche_str = str(tranche).strip()
        
        if tranche_str.upper() in ['AAP', 'ASAP']:
            return 'Dec. 31, 2030'  # ASAP -> default date
        elif tranche_str.upper() in ['TOTALE COMPLESSIVO', 'TOTAL', 'TBD']:
            return 'Dec. 31, 2030'  # TBD -> default date
        
        try:
            tranche_num = int(tranche_str)
            
            if 1 <= tranche_num <= 12:
                # Tranche 1-12 = months 2025
                year = 2025
                month = tranche_num
            elif 13 <= tranche_num <= 24:
                # Tranche 13-24 = months 2026
                year = 2026
                month = tranche_num - 12
            else:
                # Default for tranche > 24
                year = 2027
                month = min(tranche_num - 24, 12) if tranche_num > 24 else 1
            
            # Ensure month is valid
            month = max(1, min(month, 12))
            month_name = cls.MONTH_NAMES[month - 1]
            return f"{month_name}. 15, {year}"
            
        except ValueError:
            logger.warning(f"Could not parse tranche number: {tranche_str}")
            return 'Dec. 31, 2030'
    
    @classmethod
    def convert_tranche_to_iso_date(cls, tranche: str) -> str:
        """
        Converts tranche to ISO date format (YYYY-MM-DD)
        
        Args:
            tranche: Tranche number or name
            
        Returns:
            ISO date string like "2025-01-15"
        """
        formatted_date = cls.convert_tranche_to_date(tranche)
        return cls.parse_formatted_date_to_iso(formatted_date)
    
    @classmethod
    def parse_formatted_date_to_iso(cls, formatted_date: str) -> str:
        """
        Converts formatted date string to ISO format
        
        Args:
            formatted_date: Date like "Jan. 15, 2025"
            
        Returns:
            ISO date string like "2025-01-15"
        """
        if not formatted_date:
            return '2030-12-31'
            
        try:
            # Parse "Jan. 15, 2025" format
            # Remove dots and extra spaces
            clean_date = formatted_date.replace('.', '').strip()
            
            # Try to parse with datetime
            date_obj = datetime.strptime(clean_date, '%b %d, %Y')
            return date_obj.strftime('%Y-%m-%d')
            
        except ValueError:
            logger.warning(f"Could not parse date: {formatted_date}")
            return '2030-12-31'


class CountryColumnParser:
    """
    Parses country information from Excel headers and cells
    Integrates logic from both scripts
    """
    
    @classmethod
    def identify_country_columns(cls, headers: List[str]) -> Dict[str, Dict]:
        """
        Identifies columns that contain country information
        Based on identify_country_columns() from generate_product_countries_v2.py
        
        Args:
            headers: List of column headers
            
        Returns:
            Dict mapping header_name -> {column_index, countries, countries_with_dates}
        """
        logger.info(f"🔍 Identifying country columns from {len(headers)} headers...")
        country_columns = {}
        all_countries = CountryManager.get_all_countries()
        
        for idx, header in enumerate(headers):
            if not header or header != header:  # Check for NaN
                continue
                
            header_str = str(header).strip()
            
            # Extract countries and dates from header
            countries_with_dates = cls._extract_countries_with_dates_from_header(header_str, all_countries)
            
            if countries_with_dates:
                country_columns[header_str] = {
                    'column_index': idx,
                    'countries': list(countries_with_dates.keys()),
                    'countries_with_dates': countries_with_dates,
                    'group_header': header_str
                }
                logger.info(f"   ✅ Column {idx}: '{header_str}' -> {list(countries_with_dates.keys())}")
        
        logger.info(f"   📊 Found {len(country_columns)} country columns")
        return country_columns
    
    @classmethod
    def _extract_countries_with_dates_from_header(cls, header: str, all_countries: List[str]) -> Dict[str, str]:
        """
        Extracts countries with their dates from a header string
        
        Supports formats like:
        - "AL (Dec. 31, 2030)"
        - "AM (Dec. 31, 2030) AZ (Dec. 31, 2030)"
        - "AL-BG-BY" (without dates)
        
        Args:
            header: Header string
            all_countries: List of valid country codes
            
        Returns:
            Dict mapping country_code -> date_string
        """
        countries_with_dates = {}
        
        # Pattern for country with date in parentheses: COUNTRY (Date)
        country_date_pattern = r'([A-Z]{2,3})\s*\(([^)]+)\)'
        matches = re.findall(country_date_pattern, header.upper())
        
        for country_code, date_part in matches:
            if country_code in all_countries:
                # Parse and normalize the date
                normalized_date = cls._parse_date_from_header(date_part.strip())
                countries_with_dates[country_code] = normalized_date
                logger.debug(f"      📅 Extracted: {country_code} -> {normalized_date}")
            else:
                logger.warning(f"Unknown country code in header: {country_code}")
        
        # Fallback: Look for countries without dates
        if not countries_with_dates:
            countries_only = cls._extract_countries_from_header(header, all_countries)
            # DON'T assign default dates here - let the data cells provide the dates
            for country in countries_only:
                countries_with_dates[country] = None  # No default date - will be filled from data cells
                logger.debug(f"      Country found in header: {country} (no date yet)")
        
        return countries_with_dates
    
    @classmethod
    def _parse_date_from_header(cls, date_str: str) -> str:
        """
        Parses and normalizes a date from header string
        
        Examples:
        - "Dec. 31, 2030" -> "2030-12-31"
        - "JAN. 15, 2025" -> "2025-01-15"
        
        Args:
            date_str: Date string from header
            
        Returns:
            ISO date string (YYYY-MM-DD)
        """
        date_str = date_str.strip().upper()
        
        # Month mapping
        month_mapping = {
            'JAN': '01', 'JANUARY': '01',
            'FEB': '02', 'FEBRUARY': '02',
            'MAR': '03', 'MARCH': '03',
            'APR': '04', 'APRIL': '04',
            'MAY': '05',
            'JUN': '06', 'JUNE': '06',
            'JUL': '07', 'JULY': '07',
            'AUG': '08', 'AUGUST': '08',
            'SEP': '09', 'SEPTEMBER': '09',
            'OCT': '10', 'OCTOBER': '10',
            'NOV': '11', 'NOVEMBER': '11',
            'DEC': '12', 'DECEMBER': '12'
        }
        
        # Pattern for "Dec. 31, 2030" or "DEC 31, 2030"
        pattern = r'([A-Z]{3,9})\.?\s*(\d{1,2}),?\s*(\d{4})'
        match = re.search(pattern, date_str)
        
        if match:
            month_str, day, year = match.groups()
            if month_str in month_mapping:
                month_num = month_mapping[month_str]
                day_padded = day.zfill(2)
                return f"{year}-{month_num}-{day_padded}"
        
        # If parsing fails, return original but log warning
        logger.warning(f"Could not parse date from header: '{date_str}'")
        return date_str
    
    @classmethod
    def _extract_countries_from_header(cls, header: str, all_countries: List[str]) -> List[str]:
        """
        Extracts country codes from header (fallback method without dates)
        
        Examples:
        - "AL-BG-BY-EY" -> ["AL", "BG", "BY"]
        - "AE AM AZ BA" -> ["AE", "AM", "AZ", "BA"]
        
        Args:
            header: Header string
            all_countries: List of valid country codes
            
        Returns:
            List of valid country codes found
        """
        countries = []
        
        # Split by common separators
        parts = re.split(r'[-_\s,;|]+', header.upper())
        
        for part in parts:
            part = part.strip()
            # Check if it's a valid country code (2-3 characters, alphabetic)
            if len(part) >= 2 and len(part) <= 3 and part.isalpha():
                if part in all_countries:
                    countries.append(part)
                else:
                    logger.warning(f"Unknown country code in header: {part}")
                    
        return countries


class CountryDateExtractor:
    """
    Extracts country-date information from Excel rows
    Integrates logic from extract_country_dates_from_row() in generate_product_countries_v2.py
    """
    
    @classmethod
    def extract_country_dates_from_row(cls, row_data: List[Any], country_columns: Dict[str, Dict], 
                                      headers: List[str]) -> Dict[str, str]:
        """
        Extracts dates for countries from a single product row
        
        Args:
            row_data: Single row of data from Excel
            country_columns: Country column mapping from identify_country_columns()
            headers: Column headers
            
        Returns:
            Dict mapping country_code -> date_string
        """
        country_dates = {}
        all_countries = CountryManager.get_all_countries()
        
        # For each country column, get the value (which should be the date)
        for header_name, col_info in country_columns.items():
            col_idx = col_info['column_index']
            
            # Check if we have dates from header or need to get from cell
            if 'countries_with_dates' in col_info:
                header_dates = col_info['countries_with_dates']
                
                # Check if we have actual dates or just None placeholders
                has_real_dates = any(date is not None for date in header_dates.values())
                
                if has_real_dates:
                    # Use dates from header
                    for country, header_date in header_dates.items():
                        if header_date is not None:
                            country_dates[country] = header_date
                            logger.debug(f"      -> {country}: {header_date} (from header)")
                else:
                    # No dates in header, get from cell and apply to all countries
                    if col_idx < len(row_data):
                        cell_value = row_data[col_idx]
                        if cell_value is not None and str(cell_value).strip():
                            date_value = str(cell_value).strip()
                            
                            # Apply this date to all countries in this group
                            for country in header_dates.keys():
                                if country:  # Skip None countries
                                    country_dates[country] = date_value
                                    logger.debug(f"      -> {country}: {date_value} (from cell)")
            
            # Legacy fallback for old format
            elif col_idx < len(row_data):
                cell_value = row_data[col_idx]
                if cell_value is not None and str(cell_value).strip():
                    date_value = str(cell_value).strip()
                    
                    # Apply this date to all countries in this group
                    for country in col_info.get('countries', []):
                        country_dates[country] = date_value
                        logger.debug(f"      -> {country}: {date_value} (from cell legacy)")
        
        # DON'T automatically assign dates to countries not found in columns
        # Only assign default date if explicitly requested
        # This prevents unwanted "Dec. 31, 2030" assignments
        
        return country_dates


class DateNormalizer:
    """
    Normalizes dates from various formats to standard formats
    """
    
    @classmethod
    def normalize_date_value(cls, raw_date: str) -> str:
        """
        Normalizes a date value from Excel to a standard format
        
        Args:
            raw_date: Raw date string from Excel
            
        Returns:
            Normalized date string
        """
        if not raw_date:
            return 'TBD'
            
        raw_date = str(raw_date).strip().upper()
        
        # Handle special cases
        if raw_date in ['AAP', 'ASAP']:
            return 'ASAP'
        elif raw_date in ['TBD', 'TBC', '']:
            return 'TBD'
        else:
            # For now, return as-is
            # Could add more sophisticated date parsing here
            return raw_date
    
    @classmethod
    def determine_date_type(cls, normalized_date: str) -> str:
        """
        Determines the type of date for Django model
        
        Args:
            normalized_date: Normalized date string
            
        Returns:
            Date type: 'immediate', 'scheduled', or 'tbd'
        """
        if normalized_date == 'ASAP':
            return 'immediate'
        elif normalized_date == 'TBD':
            return 'tbd'
        else:
            return 'scheduled'
