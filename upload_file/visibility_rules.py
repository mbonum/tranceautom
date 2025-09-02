"""
E-commerce visibility rules
Complete mapping of visibility rules and applicable countries
"""

class VisibilityRules:
    """
    Class containing all e-commerce visibility rules
    """
    
    # Complete list of all possible countries
    ALL_COUNTRIES = [
        'AL', 'AM', 'AT', 'AZ', 'BA', 'BE', 'BG', 'BH', 'BR', 'BY', 'CH', 'CN', 'CO', 'CY', 'CZ', 
        'DE', 'DK', 'EE', 'ES', 'FL', 'FR', 'GB', 'GE', 'GR', 'HK', 'HR', 'HU', 'IE', 'IL', 
        'IT', 'JO', 'JP', 'KW', 'KZ', 'LB', 'LT', 'LU', 'LV', 'MA', 'MD', 'MK', 'MO', 'MT', 
        'MX', 'NL', 'PL', 'PT', 'QA', 'RO', 'RS', 'RU', 'SA', 'SE', 'SI', 'SK', 'TN', 'TR', 
        'TW', 'UA', 'UK', 'US', 'UZ', 'XK'
    ]
    
    # Complete visibility rules
    RULES = {
        
        # === BASE RULES ===
        "ESTERO": {
            "type": "exclude",
            "countries": ["IT"],
            "description": "All countries, except IT"
        },
        
        "MONDO": {
            "type": "include", 
            "countries": "ALL",
            "description": "All countries"
        },
        
        "WORLD": {
            "type": "include",
            "countries": "ALL", 
            "description": "All countries"
        },
        
        "OLANDA": {
            "type": "include",
            "countries": ["NL"],
            "description": "Only Holland"
        },
        
        "ITALIA": {
            "type": "include",
            "countries": ["IT"],
            "description": "Only Italy"
        },
        
        # === WORLD EXCEPT RULES ===
        "MONDO-CN": {
            "type": "exclude",
            "countries": ["CN"],
            "description": "All countries, except CN"
        },
        
        "MONDO-CN-HK-JP-MO": {
            "type": "exclude", 
            "countries": ["CN", "HK", "JP", "MO"],
            "description": "All countries, except for CN, HK, JP, MO"
        },
        
        "MONDO-ES-DE-UK-FR-HK-OLANDA-GIAPPONE-TAIWAN-USA": {
            "type": "exclude",
            "countries": ["ES", "DE", "UK", "FR", "HK", "NL", "JP", "TW", "US"],
            "description": "All countries, except ES, DE, UK, FR, HK, NL, JP, TW, US"
        },
        
        "MONDO MENO FL": {
            "type": "exclude", 
            "countries": ["FL"],
            "description": "All countries, except Florida"
        },
        
        "MONDO MENO ITALIA-CN-HK-JP-MO": {
            "type": "exclude",
            "countries": ["IT", "CN", "HK", "JP", "MO"],
            "description": "All countries except IT, CN, HK, JP, MO"
        },
        
        "MONDO MENO ITALIA - CN": {
            "type": "exclude",
            "countries": ["IT", "CN"], 
            "description": "All countries except IT and CN"
        },
        
        "MONDO MENO CN-HK-JP-MO": {
            "type": "exclude",
            "countries": ["CN", "HK", "JP", "MO"],
            "description": "All countries except CN, HK, JP, MO"
        },
        
        "MONDO MENO BR-CN-HK-JP-MO": {
            "type": "exclude",
            "countries": ["BR", "CN", "HK", "JP", "MO"],
            "description": "All countries except BR, CN, HK, JP, MO"
        },
        
        "MONDO MENO BR-CO": {
            "type": "exclude",
            "countries": ["BR", "CO"], 
            "description": "All countries except BR and CO"
        },
        
        "MONDO MENO ITA TRAD": {
            "type": "exclude",
            "countries": ["IT"],
            "description": "World less italian traditional shops (yes ecommerce)"
        },
        
        "MONDO MENO DEPT JP": {
            "type": "include",
            "countries": "ALL",
            "description": "All countries (items not in 4 Japan department stores but available in other JP shops + online)"
        },
        
        # === INTUOMO RULES ===
        "INTUOMO": {
            "type": "exclude",
            "countries": ["FL"], 
            "description": "All countries, except Florida"
        },
        
        "ALCUNI PV INTUOMO": {
            "type": "include",
            "countries": "ALL",
            "description": "All countries"
        },
        
        "INTUOMO (no e-commerce)": {
            "type": "include",
            "countries": [],
            "description": "Only Intimissimi Uomo shops, no e-commerce"
        },
        
        "INTUOMO - UK": {
            "type": "exclude",
            "countries": ["UK"],
            "description": "All countries excluding UK"
        },
        
        # === FOREIGN WITH ADDITIONS RULES ===
        "ESTERO + PV ITALIA COPPE MENO CN-HK-JP-MO": {
            "type": "exclude", 
            "countries": ["CN", "HK", "JP", "MO"],
            "description": "All countries, because some shops in IT will have this item"
        },
        
        "ESTERO + PV SOLO DONNA ITALIA": {
            "type": "include",
            "countries": "ALL",
            "description": "All countries, because some shops in IT will have this item"
        },
        
        "ESTERO MENO CN-HK-JP-MO + PV ITALIA COPPE": {
            "type": "exclude",
            "countries": ["CN", "HK", "JP", "MO"],
            "description": "All countries except CN, HK, JP, MO (activate for IT too because some shops have this item)"
        },
        
        "ESTERO MENO CN-HK-JP-MO": {
            "type": "exclude", 
            "countries": ["IT", "CN", "HK", "JP", "MO"],
            "description": "All countries except IT, CN, HK, JP, MO"
        },
        
        "ESTERO MENO AT-CH": {
            "type": "exclude",
            "countries": ["IT", "AT", "CH"],
            "description": "Foreign countries without AT/CH"
        },
        
        "ESTERO+100PV ITA": {
            "type": "include", 
            "countries": "ALL",
            "description": "Foreign countries + IT (unlock for all countries)"
        },
        
        # === COUNTRY-SPECIFIC RULES ===
        "BR (14 pv) - ES (10 pv) - FR - PT (12 pv) - TR- UK - US": {
            "type": "include",
            "countries": ["BR", "ES", "FR", "PT", "TR", "UK", "US"],
            "description": "Unlock for BR, ES, FR, PT, TR, UK, US"
        },
        
        "AT+AZ+FR+MT+RO+TR+UK+USA+SELEZIONE PV ITALIA": {
            "type": "include",
            "countries": ["AT", "AZ", "FR", "MT", "RO", "TR", "UK", "US", "IT"],
            "description": "Unlock for AT+AZ+FR+MT+RO+TR+UK+USA and IT (selezione pv Italia)"
        },
        
        "IT-AL-AT-CH Ticino-CZ-HR-RO-RS-SI-SK": {
            "type": "include", 
            "countries": ["IT", "AL", "AT", "CH", "CZ", "HR", "RO", "RS", "SI", "SK"],
            "description": "Sold in IT, AL, AT, CH, CZ, HR, RO, RS, SI, SK"
        },
        
        "IT+ RO+ SI+JP+ ECOMM.DE-CZ-PL+ECOMM. USA": {
            "type": "include",
            "countries": ["IT", "RO", "SI", "JP", "DE", "CZ", "PL", "US"],
            "description": "Shop and ecomm in IT-RO-SI-JP, only ecomm in DE-CZ-PL-US"
        },
        
        # === RULES WITH SPECIAL CONDITIONS ===
        "MONDO - TG 1 SOLO CN-HK-JP-MO": {
            "type": "include",
            "countries": "ALL", 
            "description": "All countries, but size 1 only for CN-HK-JP-MO",
            "conditions": {"size_restrictions": {"size_1": ["CN", "HK", "JP", "MO"]}}
        },
        
        "MONDO (TG XS ESTERO)": {
            "type": "include",
            "countries": "ALL",
            "description": "All countries; XS is for all except IT",
            "conditions": {"size_restrictions": {"XS": "ESTERO"}}
        },
        
        "MONDO - TG 5-6 NO CN-HK-JP-MO": {
            "type": "include", 
            "countries": "ALL",
            "description": "All countries; size 5 and 6 IS NOT for CN, HK, JP, MO",
            "conditions": {"size_restrictions": {"size_5_6_excluded": ["CN", "HK", "JP", "MO"]}}
        },
        
        "MONDO (tg XS CN-HK-JP-MO)": {
            "type": "include",
            "countries": "ALL", 
            "description": "All countries; size XS is only for CN, HK, JP, MO",
            "conditions": {"size_restrictions": {"XS_only": ["CN", "HK", "JP", "MO"]}}
        },
        
        "MONDO - NO XK - 1C SOLO CN-HK-JP-MO": {
            "type": "exclude",
            "countries": ["XK"],
            "description": "All countries, not for Kosovo; 1c is only for CN, HK, JP, MO",
            "conditions": {"size_restrictions": {"1c_only": ["CN", "HK", "JP", "MO"]}}
        },
        
        "MONDO MENO BR-CO (CN-HK-JP-MO NO 4B)": {
            "type": "exclude", 
            "countries": ["BR", "CO"],
            "description": "All countries, except BR and CO; CN, HK, JP, MO don't have size 4B",
            "conditions": {"size_restrictions": {"4B_excluded": ["CN", "HK", "JP", "MO"]}}
        },
        
        "MONDO (CN-HK-JP-MO NO 4)": {
            "type": "include",
            "countries": "ALL",
            "description": "All countries, size 4 not for CN, HK, JP, MO",
            "conditions": {"size_restrictions": {"size_4_excluded": ["CN", "HK", "JP", "MO"]}}
        },
        
        "MONDO - COPPE D SOLO ESTERO": {
            "type": "include",
            "countries": "ALL", 
            "description": "Activate for all countries, cup D is only for Estero (all not IT)",
            "conditions": {"size_restrictions": {"cup_D": "ESTERO"}}
        },
        
        "MONDO - TG 1 ESTERO eccetto BR": {
            "type": "include",
            "countries": "ALL",
            "description": "Unlock for all countries but unlock size 1 only for foreign countries without BR", 
            "conditions": {"size_restrictions": {"size_1_estero_no_BR": True}}
        },
        
        "MONDO MENO ITA TRAD.; tg XXL INTU+EC": {
            "type": "include", 
            "countries": "ALL",
            "description": "Unlock for all countries",
            "conditions": {"size_restrictions": {"XXL_intuomo_ecomm": True}}
        },
        
        # === COMPLEX RULES WITH SIZES ===
        "MONDO - TG 0C E 0D SOLO ESTERO E PV SOLO DONNA ITALIA - 1C SOLO ESTERO (0C-CD-1C NO BR)": {
            "type": "include",
            "countries": "ALL",
            "description": "Activate for all countries. 0C and 0D are for Estero and some shops in IT. 1C is just for Estero. 0C, 0D and 1C not for BR",
            "conditions": {
                "size_restrictions": {
                    "0C_0D": "ESTERO_AND_IT_DONNA_SHOPS",
                    "1C": "ESTERO_ONLY", 
                    "0C_0D_1C_excluded": ["BR"]
                }
            }
        },
        
        "MONDO MENO BR-CN-HK-JP-MO; tg 0C-0D solo Estero + pv solo Donna Italia; 1C SOLO ESTERO": {
            "type": "exclude",
            "countries": ["BR", "CN", "HK", "JP", "MO"],
            "description": "Activate for all countries except CN, HK, JP, MO. Sizes 0C and 0D are just for ESTERO and some stores in IT. 1C size is only for ESTERO",
            "conditions": {
                "size_restrictions": {
                    "0C_0D": "ESTERO_AND_IT_DONNA_SHOPS",
                    "1C": "ESTERO_ONLY"
                }
            }
        },
        
        # === TEMPORAL RULES ===
        "ITALIA (MONDO fino al 17/05)": {
            "type": "include",
            "countries": ["IT"],
            "description": "Item was meant to be active for Mondo till 17.5., and after that it should be active only in Italy",
            "conditions": {"temporal": "MONDO_UNTIL_17_05_THEN_IT_ONLY"}
        },
        
        "ITALIA (Esaurimento CN-HK-JP)": {
            "type": "include", 
            "countries": ["IT", "CN", "HK", "JP"],
            "description": "Item is available in IT. It's also available in CN, HK, JP but once availability in warehouses is over, they will no longer restock",
            "conditions": {"temporal": "CN_HK_JP_UNTIL_STOCK_DEPLETION"}
        },
        
        # === SPECIAL RULES ===
        "MONDO (Italia solo alcuni pv)": {
            "type": "include",
            "countries": "ALL",
            "description": "Activate for all countries because IF SOME STORES will have this item, you need to unlock it for the web"
        },
        
        "MONDO MENO CN - ALCUNI PV RU": {
            "type": "exclude", 
            "countries": ["CN"],
            "description": "All countries, and RU too because SOME SHOPS in RU will have this item. CN - do not activate"
        },
        
        "MONDO MENO CN-HK-JP (sì IBB8)": {
            "type": "exclude",
            "countries": ["CN", "HK", "JP"],
            "description": "All countries except CN, HK, JP. But JP is available in IBB8 shop - UNLOCK FOR JP also",
            "conditions": {"shop_specific": {"IBB8": ["JP"]}}
        }
    }
    
    @classmethod
    def get_allowed_countries(cls, rule_text):
        """
        Returns the list of allowed countries for a visibility rule
        
        Args:
            rule_text (str): The visibility rule text
            
        Returns:
            list: List of allowed country codes
        """
        if not rule_text:
            return []
        
        # Clean the rule text
        rule_clean = rule_text.strip().upper()
        
        # Look for an exact match
        if rule_clean in cls.RULES:
            rule = cls.RULES[rule_clean]
            
            if rule["type"] == "include":
                if rule["countries"] == "ALL":
                    return cls.ALL_COUNTRIES.copy()
                else:
                    return rule["countries"].copy()
                    
            elif rule["type"] == "exclude":
                excluded = rule["countries"]
                return [country for country in cls.ALL_COUNTRIES if country not in excluded]
        
        # If no exact match found, try pattern matching
        return cls._try_pattern_matching(rule_clean)
    
    @classmethod
    def _try_pattern_matching(cls, rule_text):
        """
        Try pattern matching for non-exact rules
        """
        rule_lower = rule_text.lower()
        
        # Common patterns
        if "mondo" in rule_lower and "meno" not in rule_lower and "except" not in rule_lower:
            return cls.ALL_COUNTRIES.copy()
        
        if "estero" in rule_lower and "meno" not in rule_lower:
            return [country for country in cls.ALL_COUNTRIES if country != "IT"]
        
        # If unable to interpret, return empty list
        return []
    
    @classmethod
    def get_rule_description(cls, rule_text):
        """
        Returns the description of a rule
        """
        if not rule_text:
            return "No rule specified"
        
        rule_clean = rule_text.strip().upper()
        
        if rule_clean in cls.RULES:
            return cls.RULES[rule_clean]["description"]
        
        return f"Unknown rule: {rule_text}"
    
    @classmethod
    def has_special_conditions(cls, rule_text):
        """
        Checks if a rule has special conditions (sizes, shops, etc.)
        """
        if not rule_text:
            return False
        
        rule_clean = rule_text.strip().upper()
        
        if rule_clean in cls.RULES:
            return "conditions" in cls.RULES[rule_clean]
        
        return False
    
    @classmethod
    def get_special_conditions(cls, rule_text):
        """
        Returns the special conditions of a rule
        """
        if not rule_text:
            return {}
        
        rule_clean = rule_text.strip().upper()
        
        if rule_clean in cls.RULES and "conditions" in cls.RULES[rule_clean]:
            return cls.RULES[rule_clean]["conditions"]
        
        return {}
    
    @classmethod
    def list_all_rules(cls):
        """
        Returns all available rules
        """
        return list(cls.RULES.keys())
    
    @classmethod
    def get_rule_stats(cls):
        """
        Returns statistics about the rules
        """
        total_rules = len(cls.RULES)
        include_rules = len([r for r in cls.RULES.values() if r["type"] == "include"])
        exclude_rules = len([r for r in cls.RULES.values() if r["type"] == "exclude"])
        rules_with_conditions = len([r for r in cls.RULES.values() if "conditions" in r])
        
        return {
            "total_rules": total_rules,
            "include_rules": include_rules, 
            "exclude_rules": exclude_rules,
            "rules_with_conditions": rules_with_conditions,
            "total_countries": len(cls.ALL_COUNTRIES)
        }


# === UTILITY FUNCTIONS ===

def parse_visibility_rule(rule_text):
    """
    Utility function to parse a visibility rule
    
    Args:
        rule_text (str): Rule text
        
    Returns:
        dict: Dictionary with allowed countries and description
    """
    allowed_countries = VisibilityRules.get_allowed_countries(rule_text)
    description = VisibilityRules.get_rule_description(rule_text)
    has_conditions = VisibilityRules.has_special_conditions(rule_text)
    conditions = VisibilityRules.get_special_conditions(rule_text)
    
    return {
        "rule_text": rule_text,
        "allowed_countries": allowed_countries,
        "description": description, 
        "has_special_conditions": has_conditions,
        "special_conditions": conditions,
        "allowed_countries_count": len(allowed_countries)
    }


def test_visibility_rules():
    """
    Test function to verify the rules
    """
    print("=== TEST VISIBILITY RULES ===")
    
    # Test some rules
    test_rules = [
        "MONDO",
        "ESTERO", 
        "MONDO-CN-HK-JP-MO",
        "OLANDA",
        "MONDO MENO BR-CN-HK-JP-MO"
    ]
    
    for rule in test_rules:
        result = parse_visibility_rule(rule)
        print(f"\nRule: {rule}")
        print(f"Description: {result['description']}")
        print(f"Allowed countries ({result['allowed_countries_count']}): {result['allowed_countries'][:10]}...")
        if result['has_special_conditions']:
            print(f"Special conditions: {result['special_conditions']}")
    
    # Statistics
    stats = VisibilityRules.get_rule_stats()
    print("\n=== STATS ===")
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    test_visibility_rules()
