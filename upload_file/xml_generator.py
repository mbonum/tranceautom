"""
XML Generator for Tranche Automation
Generates XML files for PIM system integration
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from typing import Dict, List
import logging

from .models import PianificazioneImport, Prodotto, PaesePianificazione

logger = logging.getLogger(__name__)


class XMLGenerator:
    """
    XML Generator for planning data
    """
    
    def __init__(self):
        self.namespace = "http://tranche-automation.com/planning/v1"
    
    def generate_planning_xml(self, pianificazione: PianificazioneImport) -> str:
        """
        Generate complete XML for a planning import
        
        Args:
            pianificazione: PianificazioneImport instance
            
        Returns:
            str: Formatted XML content
        """
        try:
            logger.info(f"Generating XML for planning {pianificazione.id}")
            
            # Root element
            root = ET.Element("PlanningExport")
            root.set("xmlns", self.namespace)
            root.set("version", "1.0")
            root.set("generated", datetime.now().isoformat())
            
            # Metadata
            metadata = ET.SubElement(root, "Metadata")
            ET.SubElement(metadata, "SourceFile").text = pianificazione.source_file_name
            ET.SubElement(metadata, "ImportId").text = str(pianificazione.id)
            ET.SubElement(metadata, "ImportDate").text = pianificazione.imported_at.isoformat()
            ET.SubElement(metadata, "ImportedBy").text = pianificazione.imported_by.username
            ET.SubElement(metadata, "Status").text = pianificazione.status
            ET.SubElement(metadata, "TotalProducts").text = str(pianificazione.total_products)
            ET.SubElement(metadata, "TotalCountries").text = str(pianificazione.total_countries)
            
            # Products
            products_element = ET.SubElement(root, "Products")
            
            # Get all products with related country information
            prodotti = pianificazione.get_all_products().prefetch_related('paesi_pianificazione')
            
            for prodotto in prodotti:
                product_element = self._create_product_element(prodotto)
                products_element.append(product_element)
            
            # Countries Summary
            countries_summary = ET.SubElement(root, "CountriesSummary")
            self._add_countries_summary(countries_summary, pianificazione)
            
            # Format XML
            xml_string = self._prettify_xml(root)
            
            logger.info(f"XML generated successfully: {len(prodotti)} products")
            return xml_string
            
        except Exception as e:
            logger.error(f"Error generating XML: {str(e)}")
            raise
    
    def _create_product_element(self, prodotto: Prodotto) -> ET.Element:
        """
        Create XML element for a single product
        """
        product = ET.Element("Product")
        product.set("id", str(prodotto.id))
        product.set("rowNumber", str(prodotto.row_number))
        
        # Basic product information
        identification = ET.SubElement(product, "Identification")
        ET.SubElement(identification, "ChiaveArticolo").text = prodotto.chiave_articolo or ""
        ET.SubElement(identification, "SKU").text = prodotto.sku or ""
        ET.SubElement(identification, "Articolo").text = prodotto.articolo or ""
        ET.SubElement(identification, "Colore").text = prodotto.colore or ""
        ET.SubElement(identification, "Taglia").text = prodotto.taglia or ""
        ET.SubElement(identification, "Descrizione").text = prodotto.descrizione or ""
        
        # Categorization information
        categorization = ET.SubElement(product, "Categorization")
        ET.SubElement(categorization, "Serie").text = prodotto.serie or ""
        ET.SubElement(categorization, "Merceologia").text = prodotto.merceologia or ""
        ET.SubElement(categorization, "Tranche").text = prodotto.n_tranche or ""
        ET.SubElement(categorization, "Stagione").text = prodotto.stagione or ""
        ET.SubElement(categorization, "Categorie").text = prodotto.categorie or ""
        
        # Supplier information
        supplier = ET.SubElement(product, "Supplier")
        ET.SubElement(supplier, "Fornitore").text = prodotto.fornitore or ""
        ET.SubElement(supplier, "CodiceForn").text = prodotto.codice_forn or ""
        ET.SubElement(supplier, "MadeIn").text = prodotto.made_in or ""
        
        # Main dates
        dates = ET.SubElement(product, "Dates")
        ET.SubElement(dates, "DataInizioConsegna").text = prodotto.data_inizio_consegna or ""
        ET.SubElement(dates, "DataSpedizioneReale").text = prodotto.data_spedizione_reale or ""
        ET.SubElement(dates, "DataConsegnaFornitore").text = prodotto.data_consegna_fornitore or ""
        
        # Country information
        countries = ET.SubElement(product, "Countries")
        
        # Add data for each country
        for paese_data in prodotto.paesi_pianificazione.all():
            country_element = ET.SubElement(countries, "Country")
            country_element.set("code", paese_data.codice_paese)
            country_element.set("available", str(paese_data.is_available).lower())
            
            ET.SubElement(country_element, "AvailabilityType").text = paese_data.data_tipo
            ET.SubElement(country_element, "AvailabilityValue").text = paese_data.availability_value or ""
            
            if paese_data.data_disponibilita:
                ET.SubElement(country_element, "AvailabilityDate").text = paese_data.data_disponibilita.isoformat()
            
            ET.SubElement(country_element, "SourceColumn").text = paese_data.source_column or ""
        
        # Additional metadata
        metadata = ET.SubElement(product, "AdditionalData")
        ET.SubElement(metadata, "ImpiantiPer").text = prodotto.impianti_per or ""
        ET.SubElement(metadata, "NoteUfficio").text = prodotto.note_ufficio or ""
        ET.SubElement(metadata, "EcommerceVisibility").text = prodotto.ecommerce_visibility or ""
        ET.SubElement(metadata, "ConcatenaMagazzino").text = prodotto.concatena_magazzino or ""
        
        return product
    
    def _add_countries_summary(self, countries_summary: ET.Element, pianificazione: PianificazioneImport):
        """
        Add countries summary
        """
        # Count products by country
        from django.db import models
        
        country_stats = PaesePianificazione.objects.filter(
            prodotto__pianificazione=pianificazione
        ).values('codice_paese').annotate(
            total_products=models.Count('prodotto', distinct=True),
            available_products=models.Count('prodotto', filter=models.Q(is_available=True), distinct=True),
            aap_products=models.Count('prodotto', filter=models.Q(data_tipo='as_available'), distinct=True),
            dated_products=models.Count('prodotto', filter=models.Q(data_tipo='data_specifica'), distinct=True)
        ).order_by('codice_paese')
        
        for stat in country_stats:
            country = ET.SubElement(countries_summary, "CountrySummary")
            country.set("code", stat['codice_paese'])
            
            ET.SubElement(country, "TotalProducts").text = str(stat['total_products'])
            ET.SubElement(country, "AvailableProducts").text = str(stat['available_products'])
            ET.SubElement(country, "AAPProducts").text = str(stat['aap_products'])
            ET.SubElement(country, "DatedProducts").text = str(stat['dated_products'])
    
    def _prettify_xml(self, element: ET.Element) -> str:
        """
        Format XML in a readable way
        """
        rough_string = ET.tostring(element, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')
    
    def generate_country_specific_xml(self, pianificazione: PianificazioneImport, country_codes: List[str]) -> str:
        """
        Generate XML for specific countries
        
        Args:
            pianificazione: PianificazioneImport instance
            country_codes: List of country codes to include
            
        Returns:
            str: Filtered XML content
        """
        try:
            logger.info(f"Generating XML for countries: {country_codes}")
            
            # Get only products with data for requested countries
            prodotti = pianificazione.get_all_products().filter(
                paesi_pianificazione__codice_paese__in=country_codes,
                paesi_pianificazione__is_available=True
            ).distinct().prefetch_related('paesi_pianificazione')
            
            # Root element
            root = ET.Element("CountrySpecificExport")
            root.set("countries", ",".join(country_codes))
            root.set("generated", datetime.now().isoformat())
            
            # Metadata
            metadata = ET.SubElement(root, "Metadata")
            ET.SubElement(metadata, "SourceFile").text = pianificazione.source_file_name
            ET.SubElement(metadata, "FilteredCountries").text = ",".join(country_codes)
            ET.SubElement(metadata, "FilteredProducts").text = str(prodotti.count())
            
            # Products (only for selected countries)
            products_element = ET.SubElement(root, "Products")
            
            for prodotto in prodotti:
                product_element = self._create_product_element(prodotto)
                
                # Filter only requested countries
                countries_elem = product_element.find("Countries")
                if countries_elem is not None:
                    # Remove non-requested countries
                    for country_elem in countries_elem.findall("Country"):
                        if country_elem.get("code") not in country_codes:
                            countries_elem.remove(country_elem)
                
                products_element.append(product_element)
            
            return self._prettify_xml(root)
            
        except Exception as e:
            logger.error(f"Error generating XML for countries {country_codes}: {str(e)}")
            raise
