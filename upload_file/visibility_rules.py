"""
E-commerce visibility rules processor
Complete mapping of visibility rules and applicable countries based on official documentation
"""

import re
import logging
import pandas as pd
from typing import List, Dict, Set, Optional  # , Union

logger = logging.getLogger(__name__)


class EcommerceVisibilityProcessor:
    """
    Advanced processor for e-commerce visibility rules
    Based on official Intimissimi documentation
    """

    # Complete list of all possible countries
    ALL_COUNTRIES = [
        "AL",
        "AM",
        "AT",
        "AZ",
        "BA",
        "BE",
        "BG",
        "BH",
        "BR",
        "BY",
        "CH",
        "CN",
        "CO",
        "CY",
        "CZ",
        "DE",
        "DK",
        "EE",
        "ES",
        "FL",
        "FR",
        "GB",
        "GE",
        "GR",
        "HK",
        "HR",
        "HU",
        "IE",
        "IL",
        "IT",
        "JO",
        "JP",
        "KW",
        "KZ",
        "LB",
        "LT",
        "LU",
        "LV",
        "MA",
        "MD",
        "MK",
        "MO",
        "MT",
        "MX",
        "NL",
        "PL",
        "PT",
        "QA",
        "RO",
        "RS",
        "RU",
        "SA",
        "SE",
        "SI",
        "SK",
        "TN",
        "TR",
        "TW",
        "UA",
        "UK",
        "US",
        "UZ",
        "XK",
    ]

    # Country aliases for pattern matching
    COUNTRY_ALIASES = {
        "OLANDA": "NL",
        "GIAPPONE": "JP",
        "TAIWAN": "TW",
        "FLORIDA": "FL",
        "ITALIA": "IT",
        "MUNDO": "MONDO",  # Common typo
    }

    def __init__(self):
        self.all_countries_set = set(self.ALL_COUNTRIES)

    def process_visibility_rule(
        self, rule_text: str, product_info: Dict = None
    ) -> Set[str]:
        """
        Process a visibility rule and return the set of allowed countries

        Args:
            rule_text (str): The visibility rule text
            product_info (Dict): Additional product information (size, cup, etc.)

        Returns:
            Set[str]: Set of country codes where the product should be available
        """
        if not rule_text or rule_text.strip() == "":
            return set()

        rule_text = rule_text.strip().upper()
        # logger.info(f"Processing visibility rule: {rule_text}")

        try:
            # Handle exact matches first
            exact_countries = self._handle_exact_rules(rule_text)
            if exact_countries is not None:
                return exact_countries

            # Handle complex rules
            return self._parse_complex_rule(rule_text, product_info)

        except Exception as e:
            logger.error(f"Error processing visibility rule '{rule_text}': {e}")
            return set()

    def _handle_exact_rules(self, rule_text: str) -> Optional[Set[str]]:
        """Handle exact rule matches"""

        exact_rules = {
            "MONDO": self.all_countries_set,
            "WORLD": self.all_countries_set,
            "ESTERO": self.all_countries_set - {"IT"},
            "OLANDA": {"NL"},
            "ITALIA": {"IT"},
            "ALCUNI PV INTUOMO": self.all_countries_set,
            "INTUOMO": self.all_countries_set - {"FL"},
            "MONDO MENO FL": self.all_countries_set - {"FL"},
            "ESTERO+100PV ITA": self.all_countries_set,
            "INTUOMO (NO E-COMMERCE)": set(),  # No e-commerce
        }

        return exact_rules.get(rule_text)

    def _parse_complex_rule(
        self, rule_text: str, product_info: Dict = None
    ) -> Set[str]:
        """Parse complex visibility rules"""

        # Start with all countries by default
        result_countries = self.all_countries_set.copy()

        # Handle MONDO MENO (World except) patterns
        if "MONDO MENO" in rule_text or "MONDO-" in rule_text:
            result_countries = self._handle_mondo_meno(rule_text)

        # Handle ESTERO patterns
        elif "ESTERO" in rule_text:
            result_countries = self._handle_estero_patterns(rule_text)

        # Handle specific country lists
        elif self._contains_country_list(rule_text):
            result_countries = self._extract_country_list(rule_text)

        # Handle IT+ patterns (specific countries)
        elif "IT+" in rule_text or any(
            f"{country}+" in rule_text for country in self.ALL_COUNTRIES
        ):
            result_countries = self._handle_specific_countries(rule_text)

        # Apply additional conditions
        result_countries = self._apply_conditions(
            rule_text, result_countries, product_info
        )

        # logger.info(f"Rule '{rule_text}' → {len(result_countries)} countries: {sorted(result_countries)}")
        return result_countries

    def _handle_mondo_meno(self, rule_text: str) -> Set[str]:
        """Handle 'MONDO MENO' (World except) patterns"""

        # Extract excluded countries
        excluded = set()

        # Pattern: MONDO-CN or MONDO MENO CN
        patterns = [
            r"MONDO[-\s]?MENO[\s]+([\w\-\s]+)",
            r"MONDO-([\w\-]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, rule_text)
            if match:
                excluded_text = match.group(1)
                excluded.update(self._parse_country_codes(excluded_text))
                break

        # Special cases
        if "CN-HK-JP-MO" in rule_text:
            excluded.update({"CN", "HK", "JP", "MO"})
        if "ES-DE-UK-FR-HK-OLANDA-GIAPPONE-TAIWAN-USA" in rule_text:
            excluded.update({"ES", "DE", "UK", "FR", "HK", "NL", "JP", "TW", "US"})
        if "ITALIA-CN-HK-JP-MO" in rule_text:
            excluded.update({"IT", "CN", "HK", "JP", "MO"})
        if "BR-CO" in rule_text:
            excluded.update({"BR", "CO"})
        if "AT-CH" in rule_text:
            excluded.update({"AT", "CH"})

        return self.all_countries_set - excluded

    def _handle_estero_patterns(self, rule_text: str) -> Set[str]:
        """Handle ESTERO (Foreign) patterns"""

        # Start with all countries except IT
        result = self.all_countries_set - {"IT"}

        # Check for additional exclusions
        if "MENO CN-HK-JP-MO" in rule_text:
            result -= {"CN", "HK", "JP", "MO"}
        elif "MENO AT-CH" in rule_text:
            result -= {"AT", "CH"}

        # Check for IT inclusion due to some shops
        if any(
            phrase in rule_text
            for phrase in [
                "PV ITALIA",
                "SOLO DONNA ITALIA",
                "VIP ITALIA",
                "SELEZIONE PV ITALIA",
                "100PV ITA",
            ]
        ):
            result.add("IT")

        return result

    def _handle_specific_countries(self, rule_text: str) -> Set[str]:
        """Handle specific country patterns like IT+RO+SI+JP"""

        # Extract countries from patterns like "IT+RO+SI+JP"
        countries = set()

        # Pattern: COUNTRY+ or COUNTRY-
        country_pattern = r"\b([A-Z]{2,3})\+?"
        matches = re.findall(country_pattern, rule_text)

        for match in matches:
            if match in self.ALL_COUNTRIES:
                countries.add(match)

        # Handle specific known patterns
        if "BR (14 pv) - ES (10 pv) - FR - PT (12 pv) - TR- UK - US" in rule_text:
            countries.update({"BR", "ES", "FR", "PT", "TR", "UK", "US"})

        return countries

    def _contains_country_list(self, rule_text: str) -> bool:
        """Check if rule contains a specific country list"""

        # Look for patterns that indicate specific country lists
        patterns = [
            r"\b[A-Z]{2,3}[\s\-\+]+[A-Z]{2,3}",  # Country codes with separators
            r"\([^)]*pv[^)]*\)",  # Patterns with "pv" in parentheses
        ]

        return any(re.search(pattern, rule_text) for pattern in patterns)

    def _extract_country_list(self, rule_text: str) -> Set[str]:
        """Extract specific country list from rule text"""

        countries = set()

        # Extract all potential country codes
        potential_codes = re.findall(r"\b([A-Z]{2,3})\b", rule_text)

        for code in potential_codes:
            if code in self.ALL_COUNTRIES:
                countries.add(code)
            elif code in self.COUNTRY_ALIASES:
                countries.add(self.COUNTRY_ALIASES[code])

        return countries

    def _apply_conditions(
        self, rule_text: str, countries: Set[str], product_info: Dict = None
    ) -> Set[str]:
        """Apply conditional logic based on product info"""

        # Handle size-specific conditions
        if product_info and "taglia" in product_info:
            size = product_info["taglia"]

            # Size 1 specific rules
            if "TG 1" in rule_text and "SOLO CN-HK-JP-MO" in rule_text:
                if size == "1":
                    return {"CN", "HK", "JP", "MO"}
                else:
                    return countries - {"CN", "HK", "JP", "MO"}

            # XS specific rules
            if "TG XS" in rule_text:
                if size == "XS":
                    if "ESTERO" in rule_text:
                        return countries - {"IT"}
                    elif "CN-HK-JP-MO" in rule_text:
                        return {"CN", "HK", "JP", "MO"}

        # Handle cup-specific conditions
        if product_info and any(key in product_info for key in ["coppa", "cup"]):
            if "COPPE D SOLO ESTERO" in rule_text:
                cup = product_info.get("coppa", product_info.get("cup", ""))
                if cup == "D":
                    return countries - {"IT"}

        # Handle no e-commerce rules
        if "NO E-COMMERCE" in rule_text:
            return set()

        return countries

    def _parse_country_codes(self, text: str) -> Set[str]:
        """Parse country codes from text"""

        countries = set()

        # Replace aliases
        for alias, code in self.COUNTRY_ALIASES.items():
            text = text.replace(alias, code)

        # Extract country codes
        codes = re.findall(r"\b([A-Z]{2,3})\b", text.upper())

        for code in codes:
            if code in self.ALL_COUNTRIES:
                countries.add(code)

        return countries

    def get_visibility_statistics(self, rules_data: List[str]) -> Dict:
        """Get statistics about visibility rules usage"""

        stats = {
            "total_rules": len(rules_data),
            "unique_rules": len(set(rules_data)),
            "rule_frequency": {},
            "country_coverage": {country: 0 for country in self.ALL_COUNTRIES},
        }

        for rule in rules_data:
            if rule:
                rule = rule.strip()
                stats["rule_frequency"][rule] = stats["rule_frequency"].get(rule, 0) + 1

                # Calculate country coverage
                countries = self.process_visibility_rule(rule)
                for country in countries:
                    stats["country_coverage"][country] += 1

        return stats


def apply_visibility_rules_to_products(
    products_df, processor: EcommerceVisibilityProcessor = None
):
    """
    Apply visibility rules to products DataFrame and update country availability

    Args:
        products_df: DataFrame with products and ecommerce_visibility column
        processor: EcommerceVisibilityProcessor instance

    Returns:
        DataFrame with updated country columns based on visibility rules
    """

    if processor is None:
        processor = EcommerceVisibilityProcessor()

    logger.info(f"🔄 Applying visibility rules to {len(products_df)} products")

    # Find the correct E-commerce Visibility column name
    visibility_col = None
    possible_names = [
        "E-COMMERCE VISIBILITY (COUNTRIES)",
        "E-commerce Visibility",
        "ecommerce_visibility",
        "E-COMMERCE VISIBILITY",
        "ECOMMERCE VISIBILITY",
    ]

    for col_name in possible_names:
        if col_name in products_df.columns:
            visibility_col = col_name
            break

    if not visibility_col:
        logger.warning(
            "⚠️ No E-commerce Visibility column found. Available columns: "
            + ", ".join(products_df.columns.tolist())
        )
        return products_df

    logger.info(f"📋 Using visibility column: '{visibility_col}'")

    # Track statistics
    products_with_rules = 0
    countries_populated = 0

    # Process each product
    for idx, row in products_df.iterrows():
        visibility_rule = row.get(visibility_col, "")

        if (
            visibility_rule
            and str(visibility_rule).strip()
            and str(visibility_rule).strip() != "nan"
        ):
            products_with_rules += 1

            # Get allowed countries based on visibility rule
            allowed_countries = processor.process_visibility_rule(
                str(visibility_rule).strip(),
                {
                    "taglia": row.get("Taglia", ""),
                    "coppa": row.get("Coppa", ""),  # If you have cup info
                },
            )

            # logger.debug(f"Product {idx}: Rule '{visibility_rule}' → {len(allowed_countries)} countries")

            # Update country columns based on visibility rules
            for country in processor.ALL_COUNTRIES:
                country_col = f"country_{country}"
                if country_col in products_df.columns:
                    current_value = products_df.at[idx, country_col]

                    if country in allowed_countries:
                        # Keep existing value or set AAP if empty
                        if (
                            pd.isna(current_value)
                            or str(current_value).strip() == ""
                            or str(current_value).strip() == "nan"
                        ):
                            products_df.at[idx, country_col] = "AAP"
                            countries_populated += 1
                    else:
                        # Clear country if not allowed by visibility rules
                        if (
                            not pd.isna(current_value)
                            and str(current_value).strip() != ""
                        ):
                            products_df.at[idx, country_col] = ""

    logger.info("✅ Visibility rules applied successfully:")
    logger.info(f"   📊 Products with rules: {products_with_rules}/{len(products_df)}")
    logger.info(f"   🌍 Countries populated: {countries_populated}")

    return products_df


# Integration function for Django
def integrate_visibility_processor():
    """
    Integration function to add visibility processing to Django country processor
    """

    from .django_country_processor import DjangoCountryProcessor

    # Add visibility processing method to existing processor
    def process_with_visibility(self, df, import_record):
        """Enhanced processing with visibility rules"""

        # Apply visibility rules before saving to database
        processor = EcommerceVisibilityProcessor()
        df_with_visibility = apply_visibility_rules_to_products(df, processor)

        # Continue with normal database saving
        return self._save_to_database(df_with_visibility, import_record)

    # Monkey patch the method
    DjangoCountryProcessor.process_with_visibility = process_with_visibility
