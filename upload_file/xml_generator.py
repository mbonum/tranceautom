"""
XML generation utilities for Tranche Automation
Handles the generation of optimized XML output with 1-to-1 country-date mappings
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from xml.sax.saxutils import escape as xml_escape
from django.db.models import QuerySet

from .models import PianificazioneImport, Prodotto, PaesePianificazione
from .country_utils import DateNormalizer

logger = logging.getLogger(__name__)


class XMLPlanningGenerator:
    """
    Generates optimized XML planning files with 1-to-1 country-date mappings
    """
    
    def __init__(self, planning_id: int, username: str = "system"):
        self.planning_id = planning_id
        self.username = username
        self.planning = None
        self.products = None
        self._load_planning_data()
        
    def _load_planning_data(self):
        """Load planning data from database"""
        try:
            self.planning = PianificazioneImport.objects.get(id=self.planning_id)
            self.products = Prodotto.objects.filter(
                pianificazione=self.planning
            ).prefetch_related('pianificazioni_paesi').order_by('codice_forn')
            
            logger.info(f"Loaded planning {self.planning_id} with {self.products.count()} products")
            
        except PianificazioneImport.DoesNotExist:
            logger.error(f"Planning with ID {self.planning_id} not found")
            raise
            
    def generate_full_xml(self, tranche_name: Optional[str] = None) -> str:
        """
        Generate complete XML for all products or specific tranche
        
        Args:
            tranche_name: Optional tranche name to filter products
            
        Returns:
            Complete XML string
        """
        try:
            products_to_export = self.products
            
            if tranche_name:
                products_to_export = products_to_export.filter(tranche_name=tranche_name)
                
            xml_content = self._build_xml_structure(products_to_export, tranche_name)
            
            logger.info(f"Generated XML for {products_to_export.count()} products")
            return xml_content
            
        except Exception as e:
            logger.error(f"Error generating XML: {str(e)}", exc_info=True)
            raise
            
    def _build_xml_structure(self, products: QuerySet, tranche_name: Optional[str]) -> str:
        """Build the complete XML structure"""
        xml_lines = []
        
        # XML Header
        xml_lines.extend(self._generate_xml_header(tranche_name))
        
        # Products
        for product in products:
            product_xml = self._generate_product_xml(product)
            xml_lines.extend(product_xml)
            
        # XML Footer
        xml_lines.extend(self._generate_xml_footer())
        
        return "\n".join(xml_lines)
        
    def _generate_xml_header(self, tranche_name: Optional[str]) -> List[str]:
        """Generate XML header and metadata"""
        timestamp = datetime.now().isoformat()
        display_name = tranche_name or f"Planning_{self.planning_id}"
        
        return [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<ProductPlanning>',
            '  <Metadata>',
            f'    <GeneratedBy>{self._escape_xml(self.username)}</GeneratedBy>',
            f'    <GeneratedAt>{timestamp}</GeneratedAt>',
            f'    <PlanningName>{self._escape_xml(display_name)}</PlanningName>',
            f'    <PlanningId>{self.planning_id}</PlanningId>',
            '  </Metadata>'
        ]
        
    def _generate_xml_footer(self) -> List[str]:
        """Generate XML footer"""
        return ['</ProductPlanning>']
        
    def _generate_product_xml(self, product: Prodotto) -> List[str]:
        """Generate XML for a single product with optimized country-date mappings"""
        xml_lines = []
        
        # Product opening tag
        xml_lines.append('  <Product>')
        
        # Basic product information
        xml_lines.extend([
            f'    <ProductCode>{self._escape_xml(product.codice_forn)}</ProductCode>',
            f'    <Commerce>{self._escape_xml(product.commerce)}</Commerce>',
            f'    <MadeIn>{self._escape_xml(product.made_in)}</MadeIn>',
            f'    <Categories>{self._escape_xml(product.categorie)}</Categories>'
        ])
        
        # Planning section with optimized country availability
        planning_xml = self._generate_planning_section(product)
        xml_lines.extend(planning_xml)
        
        # Product closing tag
        xml_lines.append('  </Product>')
        
        return xml_lines
        
    def _generate_planning_section(self, product: Prodotto) -> List[str]:
        """Generate the planning section with 1-to-1 country-date mappings"""
        xml_lines = []
        
        # Get all country plannings for this product
        country_plannings = product.pianificazioni_paesi.all().order_by('codice_paese', 'data_disponibilita')
        
        if country_plannings.exists():
            xml_lines.append('    <Planning>')
            xml_lines.append('      <Availability>')
            
            # Generate optimized country availability entries
            optimized_entries = self._optimize_country_date_mappings(country_plannings)
            
            for entry in optimized_entries:
                xml_lines.append(
                    f'        <CountryAvailability country="{self._escape_xml(entry["country"])}" '
                    f'date="{self._escape_xml(entry["date"])}"/>'
                )
                
            xml_lines.append('      </Availability>')
            xml_lines.append('    </Planning>')
        else:
            # Empty planning section with comment
            xml_lines.extend([
                '    <Planning>',
                '      <Availability>',
                '        <!-- No country availability data -->',
                '      </Availability>',
                '    </Planning>'
            ])
            
        return xml_lines
        
    def _optimize_country_date_mappings(self, country_plannings: QuerySet) -> List[Dict[str, str]]:
        """
        Optimize country-date mappings to ensure 1-to-1 relationships
        
        For each country, select the most appropriate date based on business rules:
        1. Prefer earliest scheduled dates over ASAP/TBD
        2. For same dates, prefer more specific sources
        3. Ensure each country appears only once
        """
        country_date_map = {}
        
        for planning in country_plannings:
            country = planning.codice_paese
            # Use the enhanced formatting method from the model
            formatted_date = XMLDateFormatter.format_date_from_planning(planning)
            
            if country not in country_date_map:
                # First entry for this country
                country_date_map[country] = {
                    'date': formatted_date,
                    'priority': self._calculate_date_priority(planning),
                    'planning': planning
                }
            else:
                # Country already exists, check if we should override
                current_priority = country_date_map[country]['priority']
                new_priority = self._calculate_date_priority(planning)
                
                if new_priority > current_priority:
                    # Higher priority, override
                    country_date_map[country] = {
                        'date': formatted_date,
                        'priority': new_priority,
                        'planning': planning
                    }
                    logger.debug(f"Overriding {country}: {country_date_map[country]['date']} -> {formatted_date}")
                    
        # Convert to list format for XML generation
        result = []
        for country, data in sorted(country_date_map.items()):
            result.append({
                'country': country,
                'date': data['date']
            })
            
        logger.debug(f"Optimized {len(country_plannings)} plannings to {len(result)} country-date mappings")
        return result
        
    def _calculate_date_priority(self, planning: PaesePianificazione) -> int:
        """
        Calculate priority for date selection
        Higher number = higher priority
        """
        priority = 0
        
        # Priority by date type
        if planning.data_tipo == 'scheduled':
            priority += 100  # Scheduled dates have highest priority
        elif planning.data_tipo == 'immediate':
            priority += 50   # ASAP has medium priority
        else:  # 'tbd'
            priority += 10   # TBD has lowest priority
            
        # Priority by source type (inferred from source_group)
        source_group = planning.source_group.lower() if planning.source_group else ''
        
        if 'country_column' in source_group:
            priority += 20  # Country-specific columns have high priority
        elif 'visibility_rule' in source_group:
            priority += 10  # Visibility rules have medium priority
        else:
            priority += 5   # Other sources have low priority
            
        # Priority by date proximity (earlier dates get slight preference)
        try:
            if planning.data_disponibilita and planning.data_disponibilita != date(2030, 12, 31):
                days_from_now = (planning.data_disponibilita - date.today()).days
                if days_from_now >= 0:
                    # Slight preference for earlier dates (max 5 points)
                    priority += max(0, 5 - (days_from_now // 30))
        except Exception:
            pass
            
        return priority
        
    def _escape_xml(self, text: str) -> str:
        """Safely escape text for XML output"""
        if not text:
            return ""
        return xml_escape(str(text))


class XMLDateFormatter:
    """
    Utility class for formatting dates in XML output
    """
    
    @staticmethod
    def format_date_for_xml(date_obj: date, date_type: str) -> str:
        """
        Format date for XML output based on type and value
        Enhanced to use DateNormalizer from country_utils
        
        Args:
            date_obj: Date object from database
            date_type: Type of date ('immediate', 'scheduled', 'tbd')
            
        Returns:
            Formatted date string for XML
        """
        if not date_obj:
            return "TBD"
            
        # Handle special far-future date (used for ASAP/TBD)
        if date_obj == date(2030, 12, 31):
            if date_type == 'immediate':
                return "ASAP"
            else:
                return "TBD"
                
        # Format regular dates
        return date_obj.strftime('%Y-%m-%d')
    
    @staticmethod
    def format_date_from_planning(planning: PaesePianificazione) -> str:
        """
        Format date from a PaesePianificazione instance using the enhanced model method
        
        Args:
            planning: PaesePianificazione instance
            
        Returns:
            Formatted date string for XML
        """
        return planning.get_formatted_date_for_xml()
        
    @staticmethod
    def validate_xml_date(date_str: str) -> bool:
        """Validate that a date string is suitable for XML output"""
        if date_str in ['ASAP', 'TBD']:
            return True
            
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False


class XMLValidator:
    """
    Validates generated XML for correctness and completeness
    """
    
    @staticmethod
    def validate_xml_content(xml_content: str) -> Dict[str, Any]:
        """
        Validate XML content for common issues
        
        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []
        stats = {
            'products': 0,
            'country_availabilities': 0,
            'unique_countries': set(),
            'date_formats': set()
        }
        
        try:
            # Basic XML structure checks
            if not xml_content.strip().startswith('<?xml'):
                errors.append("Missing XML declaration")
                
            if '<ProductPlanning>' not in xml_content:
                errors.append("Missing ProductPlanning root element")
                
            # Count elements and collect stats
            import re
            
            # Count products
            product_matches = re.findall(r'<Product>', xml_content)
            stats['products'] = len(product_matches)
            
            # Count and analyze country availabilities
            availability_pattern = r'<CountryAvailability country="([^"]+)" date="([^"]+)"/>'
            availability_matches = re.findall(availability_pattern, xml_content)
            stats['country_availabilities'] = len(availability_matches)
            
            for country, date_str in availability_matches:
                stats['unique_countries'].add(country)
                stats['date_formats'].add(date_str)
                
                # Validate country codes
                if len(country) < 2 or len(country) > 3:
                    warnings.append(f"Unusual country code: {country}")
                    
                # Validate date formats
                if not XMLDateFormatter.validate_xml_date(date_str):
                    errors.append(f"Invalid date format: {date_str}")
                    
            # Check for duplicate country entries per product
            product_sections = xml_content.split('<Product>')
            for i, section in enumerate(product_sections[1:], 1):  # Skip first empty section
                countries_in_product = re.findall(r'country="([^"]+)"', section)
                if len(countries_in_product) != len(set(countries_in_product)):
                    duplicates = [c for c in set(countries_in_product) 
                                if countries_in_product.count(c) > 1]
                    errors.append(f"Product {i} has duplicate countries: {duplicates}")
                    
        except Exception as e:
            errors.append(f"XML validation error: {str(e)}")
            
        # Convert sets to lists for JSON serialization
        stats['unique_countries'] = list(stats['unique_countries'])
        stats['date_formats'] = list(stats['date_formats'])
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'stats': stats
        }


class XMLExportManager:
    """
    High-level manager for XML export operations
    """
    
    def __init__(self, planning_id: int):
        self.planning_id = planning_id
        self.generator = XMLPlanningGenerator(planning_id)
        
    def export_full_planning(self, username: str = "system") -> Dict[str, Any]:
        """
        Export complete planning to XML
        
        Returns:
            Dictionary with export results and metadata
        """
        try:
            # Generate XML
            xml_content = self.generator.generate_full_xml()
            
            # Validate XML
            validation_result = XMLValidator.validate_xml_content(xml_content)
            
            # Prepare response
            result = {
                'success': True,
                'xml_content': xml_content,
                'validation': validation_result,
                'metadata': {
                    'planning_id': self.planning_id,
                    'generated_by': username,
                    'generated_at': datetime.now().isoformat(),
                    'content_length': len(xml_content)
                }
            }
            
            if not validation_result['is_valid']:
                result['success'] = False
                logger.error(f"XML validation failed for planning {self.planning_id}: {validation_result['errors']}")
            else:
                logger.info(f"Successfully exported planning {self.planning_id} to XML")
                
            return result
            
        except Exception as e:
            logger.error(f"Error exporting planning {self.planning_id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'xml_content': None,
                'validation': None,
                'metadata': {
                    'planning_id': self.planning_id,
                    'generated_by': username,
                    'generated_at': datetime.now().isoformat()
                }
            }
            
    def export_tranche(self, tranche_name: str, username: str = "system") -> Dict[str, Any]:
        """
        Export specific tranche to XML
        
        Args:
            tranche_name: Name of the tranche to export
            username: User performing the export
            
        Returns:
            Dictionary with export results
        """
        try:
            # Generate XML for specific tranche
            xml_content = self.generator.generate_full_xml(tranche_name)
            
            # Validate XML
            validation_result = XMLValidator.validate_xml_content(xml_content)
            
            result = {
                'success': True,
                'xml_content': xml_content,
                'validation': validation_result,
                'metadata': {
                    'planning_id': self.planning_id,
                    'tranche_name': tranche_name,
                    'generated_by': username,
                    'generated_at': datetime.now().isoformat(),
                    'content_length': len(xml_content)
                }
            }
            
            if not validation_result['is_valid']:
                result['success'] = False
                
            return result
            
        except Exception as e:
            logger.error(f"Error exporting tranche {tranche_name} for planning {self.planning_id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'xml_content': None,
                'validation': None,
                'metadata': {
                    'planning_id': self.planning_id,
                    'tranche_name': tranche_name,
                    'generated_by': username,
                    'generated_at': datetime.now().isoformat()
                }
            }
