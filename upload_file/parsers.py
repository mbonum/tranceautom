"""
Excel parsing utilities for Tranche Automation
Handles complex parsing of Excel headers and visibility columns
Enhanced with country_utils integration
"""

import re
import logging
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from .visibility_rules import VisibilityRules
from .country_utils import CountryManager, CountryColumnParser, TrancheDateConverter, DateNormalizer

logger = logging.getLogger(__name__)


class ExcelHeaderParser:
    """
    Parses Excel headers to identify country columns, date columns, and visibility rules
    """
    
    # Common patterns for country group headers
    COUNTRY_PATTERNS = [
        r'E-COMMERCE\s+VISIBILITY.*',
        r'.*STANDARD.*',
        r'.*WK.*',
        r'.*3WKS.*'
    ]
    
    def __init__(self):
        # Use the standardized country list from country_utils
        self.VALID_COUNTRY_CODES = set(CountryManager.get_all_countries())
        self.country_mappings = {}
        self.visibility_columns = []
        self.product_columns = []
        
    def parse_headers(self, headers: List[str]) -> Dict[str, Any]:
        """
        Main method to parse Excel headers and categorize columns
        
        Args:
            headers: List of header strings from Excel
            
        Returns:
            Dictionary with parsed header information
        """
        print(f"🔍 DEBUG HEADER PARSING: Analyzing {len(headers)} headers")
        
        result = {
            'country_mappings': {},
            'visibility_columns': [],
            'product_columns': [],
            'unknown_columns': []
        }
        
        for idx, header in enumerate(headers):
            if not header or pd.isna(header):
                continue
                
            header_str = str(header).strip()
            
            # Check if it's a country column
            country_info = self._parse_country_column(header_str, idx)
            if country_info:
                print(f"✅ COUNTRY COLUMN {idx}: '{header_str}' -> {country_info['countries']}")
                result['country_mappings'][idx] = country_info
                continue
                
            # Check if it's a visibility column
            if self._is_visibility_column(header_str):
                print(f"✅ VISIBILITY COLUMN {idx}: '{header_str}'")
                result['visibility_columns'].append(idx)
                continue
                
            # Check if it's a product data column
            if self._is_product_column(header_str):
                result['product_columns'].append({
                    'index': idx,
                    'name': header_str,
                    'type': self._get_product_column_type(header_str)
                })
                continue
                
            # Unknown column
            result['unknown_columns'].append({
                'index': idx,
                'name': header_str
            })
            
        print(f"🎯 PARSING SUMMARY:")
        print(f"   - Country mappings: {len(result['country_mappings'])}")
        print(f"   - Visibility columns: {len(result['visibility_columns'])}")
        print(f"   - Product columns: {len(result['product_columns'])}")
        print(f"   - Unknown columns: {len(result['unknown_columns'])}")
        
        logger.info(f"Parsed headers: {len(result['country_mappings'])} country columns, "
                   f"{len(result['visibility_columns'])} visibility columns, "
                   f"{len(result['product_columns'])} product columns")
                   
        return result
    
    def _parse_country_column(self, header: str, index: int) -> Optional[Dict[str, Any]]:
        """
        Parse a potential country column header using the enhanced country_utils logic
        
        Returns country information if this is a country column, None otherwise
        """
        # Use the enhanced country column parser from country_utils
        all_countries = CountryManager.get_all_countries()
        countries_with_dates = CountryColumnParser._extract_countries_with_dates_from_header(header, all_countries)
        
        if countries_with_dates:
            return {
                'group_header': header,
                'countries_with_dates': countries_with_dates,
                'countries': list(countries_with_dates.keys()),  # Mantieni backward compatibility
                'column_index': index,
                'type': 'country_date'
            }
            
        return None
    
    def _extract_countries_with_dates_from_header(self, header: str) -> Dict[str, str]:
        """
        Extract country codes with their dates from header string
        DEPRECATED: Use CountryColumnParser._extract_countries_with_dates_from_header instead
        
        Examples:
        "AL (Dec. 31, 2030)" -> {"AL": "2030-12-31"}
        "AM (Dec. 31, 2030) AZ (Dec. 31, 2030)" -> {"AM": "2030-12-31", "AZ": "2030-12-31"}
        """
        # Delegate to the enhanced implementation in country_utils
        all_countries = CountryManager.get_all_countries()
        return CountryColumnParser._extract_countries_with_dates_from_header(header, all_countries)
    
    def _parse_date_from_header(self, date_str: str) -> str:
        """
        Parse date from header string and normalize it
        DEPRECATED: Use CountryColumnParser._parse_date_from_header instead
        
        Examples:
        "Dec. 31, 2030" -> "2030-12-31"
        "JAN. 15, 2025" -> "2025-01-15"
        """
        # Delegate to the enhanced implementation in country_utils
        return CountryColumnParser._parse_date_from_header(date_str)

    def _extract_countries_from_header(self, header: str) -> List[str]:
        """
        Extract country codes from a header string (LEGACY METHOD)
        DEPRECATED: Use CountryColumnParser._extract_countries_from_header instead
        
        Examples:
        "AL-BG-BY-EY" -> ["AL", "BG", "BY", "EY"]
        "AE-AM-AZ-BA" -> ["AE", "AM", "AZ", "BA"]
        """
        # Delegate to the enhanced implementation in country_utils
        all_countries = CountryManager.get_all_countries()
        return CountryColumnParser._extract_countries_from_header(header, all_countries)
    
    def _is_visibility_column(self, header: str) -> bool:
        """
        Check if this is a visibility rules column
        """
        visibility_keywords = [
            'visibility', 'visibilità', 'regole', 'rules',
            'mondo', 'estero', 'italia', 'olanda'
        ]
        
        header_lower = header.lower()
        return any(keyword in header_lower for keyword in visibility_keywords)
    
    def _is_product_column(self, header: str) -> bool:
        """
        Check if this is a product data column
        """
        product_keywords = [
            'codice', 'forn', 'commerce', 'made', 'in', 
            'categorie', 'categoria', 'sku', 'product'
        ]
        
        header_lower = header.lower()
        return any(keyword in header_lower for keyword in product_keywords)
    
    def _get_product_column_type(self, header: str) -> str:
        """
        Determine the type of product column
        """
        header_lower = header.lower()
        
        if 'codice' in header_lower or 'forn' in header_lower:
            return 'product_code'
        elif 'commerce' in header_lower:
            return 'commerce'
        elif 'made' in header_lower or 'in' in header_lower:
            return 'made_in'
        elif 'categori' in header_lower:
            return 'categories'
        else:
            return 'other'


class VisibilityColumnParser:
    """
    Parses complex visibility column values to extract country-date mappings
    """
    
    def __init__(self):
        self.date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # 2025-06-12
            r'\d{2}/\d{2}/\d{4}',  # 12/06/2025
            r'\d{2}\.\d{2}\.\d{4}', # 12.06.2025
            r'AAP',  # As Soon As Possible
            r'TBD',  # To Be Determined
        ]
        
    def parse_complex_visibility(self, cell_value: Any) -> Dict[str, Any]:
        """
        Parse a complex visibility cell value
        
        Args:
            cell_value: The cell value from Excel (could be string, number, etc.)
            
        Returns:
            Dictionary with parsed country-date information
        """
        if not cell_value or pd.isna(cell_value):
            return {'countries': {}, 'raw_value': str(cell_value)}
            
        value_str = str(cell_value).strip()
        
        result = {
            'countries': {},
            'raw_value': value_str,
            'parsing_method': 'unknown'
        }
        
        # Try different parsing methods
        
        # Method 1: Simple country list (no dates)
        countries_only = self._parse_countries_only(value_str)
        if countries_only:
            result['countries'] = {country: 'AAP' for country in countries_only}
            result['parsing_method'] = 'countries_only'
            return result
            
        # Method 2: Country:Date pairs
        country_date_pairs = self._parse_country_date_pairs(value_str)
        if country_date_pairs:
            result['countries'] = country_date_pairs
            result['parsing_method'] = 'country_date_pairs'
            return result
            
        # Method 3: Single date for all countries
        single_date_result = self._parse_single_date_for_countries(value_str)
        if single_date_result:
            result['countries'] = single_date_result
            result['parsing_method'] = 'single_date'
            return result
            
        logger.warning(f"Could not parse visibility value: {value_str}")
        return result
    
    def _parse_countries_only(self, value: str) -> List[str]:
        """
        Parse a simple list of countries without dates
        
        Example: "AL-BG-BY-EY-LF-GR-HR"
        """
        countries = []
        parts = re.split(r'[-_\s,;|]+', value.upper())
        
        for part in parts:
            part = part.strip()
            if len(part) >= 2 and len(part) <= 3 and part.isalpha():
                if part in VisibilityRules.ALL_COUNTRIES:
                    countries.append(part)
                    
        return countries
    
    def _parse_country_date_pairs(self, value: str) -> Dict[str, str]:
        """
        Parse country:date pairs
        
        Example: "AL:2025-06-12,BG:AAP,IT:2025-07-01"
        """
        result = {}
        
        # Look for patterns like "COUNTRY:DATE"
        pairs = re.findall(r'([A-Z]{2,3})\s*[:=]\s*([A-Z0-9\-/\.]+)', value.upper())
        
        for country, date_str in pairs:
            if country in VisibilityRules.ALL_COUNTRIES:
                result[country] = self._normalize_date(date_str)
                
        return result
    
    def _parse_single_date_for_countries(self, value: str) -> Dict[str, str]:
        """
        Parse a single date that applies to multiple countries
        
        Example: "AAP" or "2025-06-12"
        """
        # Check if the entire value is a date
        normalized_date = self._normalize_date(value)
        if normalized_date:
            # Extract countries from context or return empty
            # This method would need additional context about which countries to apply to
            return {}
            
        return {}
    
    def _normalize_date(self, date_str: str) -> str:
        """
        Normalize various date formats to a standard format
        Enhanced to use DateNormalizer from country_utils
        """
        # Use the enhanced date normalizer from country_utils
        return DateNormalizer.normalize_date_value(date_str)


class CountryDateExtractor:
    """
    Utility class to extract and validate country-date information
    """
    
    @staticmethod
    def merge_country_sources(visibility_countries: Dict[str, str], 
                            column_countries: Dict[str, str]) -> Dict[str, str]:
        """
        Merge country information from visibility rules and column data
        
        Args:
            visibility_countries: Countries from visibility rules
            column_countries: Countries from individual columns
            
        Returns:
            Merged dictionary with country->date mappings
        """
        result = {}
        
        # Start with visibility countries
        result.update(visibility_countries)
        
        # Override with specific column data where available
        for country, date_val in column_countries.items():
            if country in result:
                # Column data takes precedence
                result[country] = date_val
            else:
                # Add new country from column data
                result[country] = date_val
                
        return result
    
    @staticmethod
    def validate_country_date_mapping(mapping: Dict[str, str]) -> Tuple[bool, List[str]]:
        """
        Validate a country-date mapping
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        for country, date_val in mapping.items():
            # Validate country code
            if country not in VisibilityRules.ALL_COUNTRIES:
                errors.append(f"Invalid country code: {country}")
                
            # Validate date format
            if date_val not in ['AAP', 'TBD']:
                try:
                    datetime.strptime(date_val, '%Y-%m-%d')
                except ValueError:
                    errors.append(f"Invalid date format for {country}: {date_val}")
                    
        return len(errors) == 0, errors


class DateNormalizer:
    """
    Utility class for date normalization and formatting
    """
    
    @staticmethod
    def normalize_excel_date(value: Any) -> str:
        """
        Normalize various Excel date formats to YYYY-MM-DD
        """
        if pd.isna(value):
            return 'TBD'
            
        value_str = str(value).strip().upper()
        
        # Handle special cases
        if value_str in ['AAP', 'ASAP']:
            return 'AAP'
        if value_str in ['TBD', 'TO BE DETERMINED', '']:
            return 'TBD'
            
        # Try to parse as pandas datetime
        try:
            if isinstance(value, (datetime, date)):
                return value.strftime('%Y-%m-%d')
                
            parsed_date = pd.to_datetime(value, errors='coerce')
            if not pd.isna(parsed_date):
                return parsed_date.strftime('%Y-%m-%d')
        except Exception:
            pass
            
        # Fallback
        logger.warning(f"Could not normalize date: {value}")
        return 'TBD'
    
    @staticmethod
    def format_date_for_xml(date_str: str) -> str:
        """
        Format date for XML output
        """
        if date_str in ['AAP', 'ASAP']:
            return 'ASAP'
        elif date_str == 'TBD':
            return 'TBD'
        else:
            return date_str  # Assume already in YYYY-MM-DD format
