#!/usr/bin/env python3
"""
Old World Ambition Parser

Parses Old World game XML files and generates a JSON file for the web viewer.
"""

import xml.etree.ElementTree as ET
import json
import re
import os
from pathlib import Path
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
REFERENCE_DIR = PROJECT_DIR / "Reference" / "XML" / "Infos"
OUTPUT_FILE = PROJECT_DIR / "viewer" / "data" / "ambitions.json"


# Ambition class names (derived from game data analysis)
AMBITION_CLASS_NAMES = {
    1: "Laws",
    2: "Theologies",
    3: "Cities",
    4: "Tribes",
    5: "Production",
    6: "Stockpiles",
    7: "Workers & Rural",
    8: "Rural Improvements",
    9: "Wonders",
    10: "Culture",
    11: "Rural Specialists",
    12: "Urban Specialists",
    13: "Projects",
    14: "Diplomacy",
    15: "Religion",
    16: "Technology",
    17: "Combat",
    18: "Promotions",
    19: "Units",
    20: "Unique Units",
    21: "Leaders",
    22: "Exploration",
    23: "Trade",
    24: "Luxuries",
    25: "Conquest",
    26: "Population",
    27: "Urban Buildings",
    28: "Religious Buildings",
    29: "Urban Development",
    30: "Espionage",
    31: "Defense",
    39: "Repairs",
    40: "Lifestyle",
}

# Event-only ambitions (subjectWeight=0) and their source events
# These can only be obtained through specific in-game events, not random selection
EVENT_ONLY_AMBITIONS = {
    "GOAL_LOSE_A_CITY": {
        "eventName": "Strength and Weakness",
        "dlc": "Behind the Throne",
        "trigger": "Leader must be Insane, 3+ upset families"
    },
    "GOAL_FURIOUS_FAMILY": {
        "eventName": "Strength and Weakness",
        "dlc": "Behind the Throne",
        "trigger": "Leader must be Insane, 3+ upset families"
    },
    "GOAL_TO_BE_KING": {
        "eventName": "To Be A King/Queen",
        "dlc": None,
        "trigger": "Regent ruling with Rightful Heir alive"
    },
    "GOAL_THE_GREAT": {
        "eventName": "The Road to Glory",
        "dlc": None,
        "trigger": "Young leader (under 30) with 2+ dead ancestors, on succession"
    },
    "GOAL_DESTROY_RIVALS": {
        "eventName": "Rivals event chain (Let the Land Burn / No Surrender)",
        "dlc": None,
        "trigger": "At war, breach enemy city, part of Rivals chain"
    },
    "GOAL_KILL_CHARACTER": {
        "eventName": "[Character's] Mark",
        "dlc": "Behind the Throne",
        "trigger": "Child of leader (teen+), angry foreign leader nearby, have spymaster"
    },
    "GOAL_HARVEST_WINE": {
        "eventName": "A Refined Palate",
        "dlc": "Behind the Throne",
        "trigger": "Leader has high Charisma, unclaimed wine within 5 tiles"
    },
    "GOAL_TAKE_HANGING_GARDENS": {
        "eventName": "The Jewel of [Nation]",
        "dlc": "Behind the Throne",
        "trigger": "Another nation owns the Hanging Gardens"
    },
    "GOAL_TAKE_CITY": {
        "eventName": "Various conquest/rivalry events",
        "dlc": None,
        "trigger": "Rivalry or conquest event chains"
    },
    "GOAL_STATE_RELIGION_SPECIFIC": {
        "eventName": "The Tutor Kartir",
        "dlc": "Sacred and Profane",
        "trigger": "Character studying, Zoroastrian city, Kartir tutor"
    },
    "GOAL_EIGHT_RELIGION_SPREAD_SPECIFIC": {
        "eventName": "In Heaven as on Earth",
        "dlc": "Sacred and Profane",
        "trigger": "Augustine character, Christianity, after High Synod mission"
    },
    "GOAL_FOUR_RELIGION_SPREAD_SPECIFIC": {
        "eventName": "Religion events",
        "dlc": "Sacred and Profane",
        "trigger": "Religion-specific event chains"
    },
    "GOAL_2000_EACH_YIELD": {
        "eventName": None,
        "dlc": None,
        "trigger": "Unused/placeholder goal"
    },
}


def parse_xml_file(filepath):
    """Parse an XML file and return the root element."""
    try:
        tree = ET.parse(filepath)
        return tree.getroot()
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None


def build_text_lookup():
    """Build a lookup dictionary for all text entries across text-*.xml files."""
    texts = {}

    # Find all text files
    text_files = list(REFERENCE_DIR.glob("text-*.xml"))

    for filepath in text_files:
        root = parse_xml_file(filepath)
        if root is None:
            continue

        for entry in root.findall("Entry"):
            ztype = entry.find("zType")
            en_us = entry.find("en-US")

            if ztype is not None and ztype.text and en_us is not None and en_us.text:
                # Store the English text, handling the tilde notation (singular~plural)
                text = en_us.text
                # Take the first variant before tilde
                if "~" in text:
                    text = text.split("~")[0]
                texts[ztype.text] = text

    return texts


def build_type_lookup(filename, name_field="Name"):
    """Build a lookup of type IDs to their name text keys."""
    lookup = {}
    filepath = REFERENCE_DIR / filename

    if not filepath.exists():
        return lookup

    root = parse_xml_file(filepath)
    if root is None:
        return lookup

    for entry in root.findall("Entry"):
        ztype = entry.find("zType")
        name = entry.find(name_field)

        if ztype is not None and ztype.text and name is not None and name.text:
            lookup[ztype.text] = name.text

    return lookup


def resolve_link(text, texts, type_lookups):
    """Resolve link() references in text."""
    if not text:
        return text

    def replace_link(match):
        ref = match.group(1)
        # Remove any numeric suffix like ",1"
        ref = ref.split(",")[0]

        # Try to find the name for this reference
        for lookup in type_lookups.values():
            if ref in lookup:
                text_key = lookup[ref]
                if text_key in texts:
                    resolved = texts[text_key]
                    # Take first variant
                    if "~" in resolved:
                        resolved = resolved.split("~")[0]
                    return resolved

        # If not found, just strip the prefix and format nicely
        for prefix in ["LAW_", "TECH_", "IMPROVEMENT_", "YIELD_", "SPECIALIST_",
                       "FAMILYCLASS_", "THEOLOGY_", "RELIGION_", "UNIT_",
                       "PROJECT_", "DIPLOMACY_", "STAT_"]:
            if ref.startswith(prefix):
                return ref[len(prefix):].replace("_", " ").title()

        return ref

    # Replace all link() patterns
    result = re.sub(r"link\(([^)]+)\)", replace_link, text)
    return result


def parse_pair_list(element):
    """Parse a list of Pair elements into a list of dicts."""
    pairs = []
    if element is None:
        return pairs

    for pair in element.findall("Pair"):
        zindex = pair.find("zIndex")
        ivalue = pair.find("iValue")

        if zindex is not None and zindex.text:
            pairs.append({
                "type": zindex.text,
                "value": int(ivalue.text) if ivalue is not None and ivalue.text else 0
            })

    return pairs


def parse_value_list(element):
    """Parse a list of zValue elements into a list of strings."""
    values = []
    if element is None:
        return values

    for zvalue in element.findall("zValue"):
        if zvalue.text:
            values.append(zvalue.text)

    return values


def get_text(element, tag, default=None):
    """Get text content of a child element."""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text
    return default


def get_int(element, tag, default=0):
    """Get integer content of a child element."""
    child = element.find(tag)
    if child is not None and child.text:
        try:
            return int(child.text)
        except ValueError:
            return default
    return default


def get_bool(element, tag, default=False):
    """Get boolean content of a child element (0/1)."""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text == "1"
    return default


def format_type_name(type_id):
    """Convert a type ID to a readable name."""
    if not type_id:
        return ""

    # Remove common prefixes
    for prefix in ["GOAL_", "LAW_", "TECH_", "IMPROVEMENT_", "YIELD_", "SPECIALIST_",
                   "FAMILYCLASS_", "THEOLOGY_", "RELIGION_", "UNIT_", "PROJECT_",
                   "DIPLOMACY_", "STAT_", "EFFECTCITY_", "CULTURE_", "SUBJECT_",
                   "IMPROVEMENTCLASS_", "RESOURCE_", "OPINIONFAMILY_", "NATION_"]:
        if type_id.startswith(prefix):
            type_id = type_id[len(prefix):]
            break

    return type_id.replace("_", " ").title()


def parse_goals():
    """Parse goal.xml and extract all ambition data."""
    goals_file = REFERENCE_DIR / "goal.xml"
    root = parse_xml_file(goals_file)

    if root is None:
        print("Failed to parse goal.xml")
        return []

    # Build text lookup
    print("Building text lookup...")
    texts = build_text_lookup()
    print(f"  Loaded {len(texts)} text entries")

    # Build type lookups for resolving references
    print("Building type lookups...")
    type_lookups = {
        "law": build_type_lookup("law.xml"),
        "tech": build_type_lookup("tech.xml"),
        "improvement": build_type_lookup("improvement.xml"),
        "specialist": build_type_lookup("specialist.xml"),
        "familyClass": build_type_lookup("familyClass.xml"),
        "religion": build_type_lookup("religion.xml"),
        "yield": build_type_lookup("yield.xml"),
        "unit": build_type_lookup("unit.xml"),
        "project": build_type_lookup("project.xml"),
        "nation": build_type_lookup("nation.xml"),
    }

    for name, lookup in type_lookups.items():
        print(f"  {name}: {len(lookup)} entries")

    # Parse goals
    print("Parsing goals...")
    goals = []

    entries = root.findall("Entry")
    for i, entry in enumerate(entries):
        # Skip the template entry (first one with empty zType)
        ztype = get_text(entry, "zType")
        if not ztype:
            continue

        # Skip scenario-specific goals
        if get_bool(entry, "bScenario"):
            continue

        # Skip disabled goals
        if get_bool(entry, "bDisabled"):
            continue

        # Get basic info
        name_key = get_text(entry, "Name", "")
        raw_name = texts.get(name_key, "")
        name = resolve_link(raw_name, texts, type_lookups) if raw_name else format_type_name(ztype)

        # Get short name if available
        short_name_key = get_text(entry, "ShortName", "")
        short_name = ""
        if short_name_key:
            raw_short = texts.get(short_name_key, "")
            short_name = resolve_link(raw_short, texts, type_lookups)

        # Get help text if available
        help_key = get_text(entry, "HelpText", "")
        help_text = ""
        if help_key:
            raw_help = texts.get(help_key, "")
            help_text = resolve_link(raw_help, texts, type_lookups)

        ambition_class = get_int(entry, "iAmbitionClass", 0)

        goal = {
            "id": ztype,
            "name": name,
            "shortName": short_name,
            "helpText": help_text,
            "ambitionClass": ambition_class,
            "ambitionClassName": AMBITION_CLASS_NAMES.get(ambition_class, f"Class {ambition_class}"),
            "minTier": get_int(entry, "iMinTier", 1),
            "maxTier": get_int(entry, "iMaxTier", 10),
            "subjectWeight": get_int(entry, "iSubjectWeight", 0),
            "dlc": get_text(entry, "GameContentRequired"),
            "requirements": {},
            "filters": {},
            "flags": {}
        }

        # Tech prerequisites
        tech_prereq = get_text(entry, "TechPrereq")
        if tech_prereq:
            goal["filters"]["techPrereq"] = tech_prereq
            goal["filters"]["techPrereqName"] = format_type_name(tech_prereq)

        tech_obsolete = get_text(entry, "TechObsolete")
        if tech_obsolete:
            goal["filters"]["techObsolete"] = tech_obsolete
            goal["filters"]["techObsoleteName"] = format_type_name(tech_obsolete)

        # Nation prerequisite
        nation_prereq = get_text(entry, "NationPrereq")
        if nation_prereq:
            goal["filters"]["nationPrereq"] = nation_prereq
            goal["filters"]["nationPrereqName"] = format_type_name(nation_prereq)

        # Family class preferences
        family_classes = parse_value_list(entry.find("aeFamilyClass"))
        if family_classes:
            goal["filters"]["familyClasses"] = family_classes
            goal["filters"]["familyClassNames"] = [format_type_name(fc) for fc in family_classes]

        # Religion preferences
        religions = parse_value_list(entry.find("aeReligion"))
        if religions:
            goal["filters"]["religions"] = religions
            goal["filters"]["religionNames"] = [format_type_name(r) for r in religions]

        # Invalid game options
        invalid_options = parse_value_list(entry.find("aeInvalidGameOptions"))
        if invalid_options:
            goal["filters"]["invalidGameOptions"] = invalid_options

        # Requirements - Law
        start_law = get_text(entry, "StartLaw")
        if start_law:
            goal["requirements"]["type"] = "law"
            goal["requirements"]["law"] = start_law
            goal["requirements"]["lawName"] = format_type_name(start_law)

        # Requirements - Theology
        theology = get_text(entry, "EstablishTheology")
        if theology:
            goal["requirements"]["type"] = "theology"
            goal["requirements"]["theology"] = theology
            goal["requirements"]["theologyName"] = format_type_name(theology)

        # Requirements - Simple counts
        simple_counts = [
            ("iCities", "cities", "Cities"),
            ("iConnectedCities", "connectedCities", "Connected Cities"),
            ("iPopulation", "population", "Population"),
            ("iLegitimacy", "legitimacy", "Legitimacy"),
            ("iWonders", "wonders", "Wonders"),
            ("iLaws", "laws", "Laws"),
            ("iCitizens", "citizens", "Citizens"),
            ("iSpecialists", "specialists", "Specialists"),
            ("iLuxuries", "luxuries", "Luxuries"),
            ("iSentLuxuries", "sentLuxuries", "Luxuries Sent"),
            ("iMilitaryUnits", "militaryUnits", "Military Units"),
            ("iMaxLevelUnits", "maxLevelUnits", "Max Level Units"),
            ("iUrbanTiles", "urbanTiles", "Urban Tiles"),
            ("iUrbanImprovements", "urbanImprovements", "Urban Improvements"),
            ("iRevealLand", "revealLand", "Land Revealed"),
            ("iRevealWater", "revealWater", "Water Revealed"),
            ("iGeneralCount", "generals", "Generals"),
            ("iExplorerCount", "explorers", "Explorers"),
            ("iGovernorCount", "governors", "Governors"),
            ("iAgentCount", "agents", "Agents"),
            ("iAgentNetworks", "agentNetworks", "Agent Networks"),
            ("iWorldReligionHolyCities", "holyCities", "Holy Cities"),
        ]

        for xml_field, json_field, display_name in simple_counts:
            value = get_int(entry, xml_field, 0)
            if value > 0:
                if "type" not in goal["requirements"]:
                    goal["requirements"]["type"] = "count"
                goal["requirements"][json_field] = value

        # Requirements - Typed counts (Pair lists)
        typed_counts = [
            ("aiYieldProducedData", "yieldProduced", "Yield Produced"),
            ("aiYieldSoldData", "yieldSold", "Yield Sold"),
            ("aiYieldRate", "yieldRate", "Yield/Turn"),
            ("aiYieldCount", "yieldStockpile", "Yield Stockpile"),
            ("aiImprovementCount", "improvements", "Improvements"),
            ("aiImprovementClassCount", "improvementClasses", "Improvement Classes"),
            ("aiSpecialistCount", "specialists", "Specialists"),
            ("aiUnitCount", "units", "Units"),
            ("aiUnitTraitCount", "unitTraits", "Unit Traits"),
            ("aiProjectCount", "projects", "Projects"),
            ("aiLuxuryCount", "luxuriesHooked", "Luxuries Hooked"),
            ("aiDiplomacyCount", "diplomacy", "Diplomacy"),
            ("aiStatCountData", "stats", "Statistics"),
            ("aiCultureCount", "culture", "Culture"),
            ("aiCultureWonders", "cultureWonders", "Culture Wonders"),
            ("aiTribesKilledData", "tribesKilled", "Tribes Killed"),
            ("aiMissionsCompletedData", "missionsCompleted", "Missions"),
        ]

        for xml_field, json_field, display_name in typed_counts:
            pairs = parse_pair_list(entry.find(xml_field))
            if pairs:
                if "type" not in goal["requirements"]:
                    goal["requirements"]["type"] = "typed_count"
                # Format the pairs with readable names
                formatted = []
                for p in pairs:
                    formatted.append({
                        "type": p["type"],
                        "typeName": format_type_name(p["type"]),
                        "value": p["value"]
                    })
                goal["requirements"][json_field] = formatted

        # Requirements - Tech list
        techs_acquired = parse_value_list(entry.find("aeTechsAcquired"))
        if techs_acquired:
            goal["requirements"]["type"] = "techs"
            goal["requirements"]["techs"] = techs_acquired
            goal["requirements"]["techNames"] = [format_type_name(t) for t in techs_acquired]

        # Requirements - Sub goals
        sub_goals = parse_value_list(entry.find("aeSubGoals"))
        if sub_goals:
            goal["requirements"]["subGoals"] = sub_goals

        # Boolean requirements
        if get_bool(entry, "bStateReligion"):
            goal["requirements"]["stateReligion"] = True
        if get_bool(entry, "bAllHolyCities"):
            goal["requirements"]["allHolyCities"] = True

        # Flags
        goal["flags"]["victoryEligible"] = get_bool(entry, "bVictoryEligible")
        goal["flags"]["blockComplete"] = get_bool(entry, "bBlockComplete")
        goal["flags"]["global"] = get_bool(entry, "bGlobal")

        # Diplomacy requirement
        diplomacy_all = get_text(entry, "DiplomacyAll")
        if diplomacy_all:
            goal["requirements"]["diplomacyAll"] = diplomacy_all
            goal["requirements"]["diplomacyAllName"] = format_type_name(diplomacy_all)

        # Family opinion requirement
        min_opinion = get_text(entry, "MinOpinionFamily")
        if min_opinion:
            goal["requirements"]["minOpinionFamily"] = min_opinion
            goal["requirements"]["minOpinionFamilyName"] = format_type_name(min_opinion)

        # Event-only ambitions (subjectWeight=0)
        if ztype in EVENT_ONLY_AMBITIONS:
            event_info = EVENT_ONLY_AMBITIONS[ztype]
            goal["eventSource"] = {
                "eventName": event_info["eventName"],
                "eventDlc": event_info["dlc"],
                "trigger": event_info["trigger"]
            }

        goals.append(goal)

    print(f"  Parsed {len(goals)} goals")
    return goals


def parse_family_classes():
    """Parse family class data for the filter UI."""
    filepath = REFERENCE_DIR / "familyClass.xml"
    root = parse_xml_file(filepath)

    if root is None:
        return {}

    texts = build_text_lookup()
    families = {}

    for entry in root.findall("Entry"):
        ztype = get_text(entry, "zType")
        if not ztype:
            continue

        name_key = get_text(entry, "Name", "")
        name = texts.get(name_key, format_type_name(ztype))
        if "~" in name:
            name = name.split("~")[0]

        families[ztype] = {
            "id": ztype,
            "name": name
        }

    return families


def parse_families():
    """Parse family data to get nation-to-familyClass mappings."""
    filepath = REFERENCE_DIR / "family.xml"
    root = parse_xml_file(filepath)

    if root is None:
        return [], {}

    texts = build_text_lookup()
    families = []
    nation_family_classes = {}  # nation -> set of family classes

    for entry in root.findall("Entry"):
        ztype = get_text(entry, "zType")
        if not ztype:
            continue

        name_key = get_text(entry, "Name", "")
        name = texts.get(name_key, format_type_name(ztype))
        if "~" in name:
            name = name.split("~")[0]

        family_class = get_text(entry, "FamilyClass")

        # Parse the nation associations
        ab_nation = entry.find("abNation")
        nations_list = []
        if ab_nation is not None:
            for pair in ab_nation.findall("Pair"):
                zindex = pair.find("zIndex")
                bvalue = pair.find("bValue")
                if zindex is not None and zindex.text and bvalue is not None and bvalue.text == "1":
                    nations_list.append(zindex.text)
                    # Track family class per nation
                    if zindex.text not in nation_family_classes:
                        nation_family_classes[zindex.text] = set()
                    if family_class:
                        nation_family_classes[zindex.text].add(family_class)

        families.append({
            "id": ztype,
            "name": name,
            "familyClass": family_class,
            "nations": nations_list
        })

    return families, nation_family_classes


def parse_nations():
    """Parse nation data for the filter UI."""
    filepath = REFERENCE_DIR / "nation.xml"
    root = parse_xml_file(filepath)

    if root is None:
        return {}

    texts = build_text_lookup()

    # Get nation -> family class mapping from family.xml
    _, nation_family_classes = parse_families()

    nations = {}

    for entry in root.findall("Entry"):
        ztype = get_text(entry, "zType")
        if not ztype:
            continue

        # Skip disabled nations
        if get_bool(entry, "bDisabled"):
            continue

        # Get name from GenderedName field
        name_key = get_text(entry, "GenderedName", "")
        name = texts.get(name_key, format_type_name(ztype))
        if "~" in name:
            name = name.split("~")[0]

        # Get DLC requirement
        dlc = get_text(entry, "GameContentRequired")

        # Get family classes for this nation
        family_classes = list(nation_family_classes.get(ztype, set()))

        nations[ztype] = {
            "id": ztype,
            "name": name,
            "dlc": dlc,
            "familyClasses": family_classes
        }

    return nations


def generate_standalone_html(data):
    """Generate a standalone HTML file with embedded CSS, JS, and data."""

    html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Old World Ambition Viewer</title>
    <style>
/* Reset and base styles */
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #1a1a2e; color: #eee; line-height: 1.6; min-height: 100vh;
}
.container { max-width: 1400px; margin: 0 auto; padding: 20px; }
.main-layout { display: flex; gap: 20px; }
.sidebar { width: 280px; flex-shrink: 0; }
.content { flex: 1; min-width: 0; }
@media (max-width: 900px) { .main-layout { flex-direction: column; } .sidebar { width: 100%; } }
header { text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #333; }
header h1 { color: #d4af37; font-size: 2rem; margin-bottom: 5px; }
.subtitle { color: #888; font-size: 0.95rem; }
.filters { background: #252540; border-radius: 8px; padding: 15px; position: sticky; top: 20px; }
.filter-group { margin-bottom: 15px; }
.filter-group:last-child { margin-bottom: 0; }
.filter-group label { display: block; margin-bottom: 5px; font-size: 0.85rem; color: #aaa; font-weight: 500; }
.filter-group select, .filter-group input[type="text"] {
    width: 100%; padding: 8px 12px; border: 1px solid #444; border-radius: 4px;
    background: #1a1a2e; color: #eee; font-size: 0.95rem;
}
.filter-group select:focus, .filter-group input[type="text"]:focus { outline: none; border-color: #d4af37; }
.families-filter { flex: 2; }
.checkbox-group { display: flex; flex-wrap: wrap; gap: 8px; }
.checkbox-group label {
    display: inline-flex; align-items: center; gap: 5px; padding: 5px 10px;
    background: #1a1a2e; border: 1px solid #444; border-radius: 4px;
    cursor: pointer; font-size: 0.85rem; transition: all 0.2s;
}
.checkbox-group label:hover { border-color: #666; }
.checkbox-group label.checked { background: #3d3d5c; border-color: #d4af37; }
.checkbox-group label.unavailable { opacity: 0.4; cursor: not-allowed; }
.checkbox-group input[type="checkbox"] { display: none; }
.tier-range { display: flex; align-items: center; gap: 10px; }
.tier-range select { width: 70px; }
.tier-range span { color: #888; }
.filter-info { display: flex; justify-content: space-between; align-items: center; margin-top: 15px; padding-top: 15px; border-top: 1px solid #333; }
#result-count { font-size: 0.9rem; color: #888; }
.checkbox-label { display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 0.9rem; color: #888; }
.completed-buttons { display: flex; flex-wrap: wrap; gap: 5px; }
.completed-btn { padding: 5px 10px; border: 1px solid #444; border-radius: 4px; background: #1a1a2e; color: #aaa; cursor: pointer; font-size: 0.85rem; transition: all 0.2s; }
.completed-btn:hover { border-color: #666; }
.completed-btn.active { background: #d4af37; color: #1a1a2e; border-color: #d4af37; font-weight: 600; }
.national-section { margin-top: 30px; padding-top: 20px; border-top: 2px solid #d4af37; }
.national-section h2 { color: #d4af37; font-size: 1.2rem; margin-bottom: 15px; }
.ambition-card.national { border-left-color: #d4af37; border-left-width: 6px; }
.result-header { margin-bottom: 15px; color: #888; font-size: 0.9rem; }
.ambitions-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 30px; }
.ambition-card {
    background: #252540; border-radius: 8px; padding: 15px;
    border-left: 4px solid #d4af37; transition: all 0.2s;
}
.ambition-card:hover { background: #2d2d4a; }
.ambition-card.unavailable { opacity: 0.5; border-left-color: #555; }
.ambition-card.unavailable .ambition-name { color: #888; }
.ambition-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.ambition-name { font-size: 1.1rem; font-weight: 600; color: #fff; }
.ambition-meta { display: flex; gap: 8px; align-items: center; }
.tier-badge { background: #d4af37; color: #1a1a2e; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
.category-badge { background: #3d3d5c; color: #aaa; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
.ambition-details { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }
.family-tags { display: flex; flex-wrap: wrap; gap: 5px; }
.family-tag { background: #1a1a2e; border: 1px solid #444; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; color: #bbb; }
.family-tag.active { border-color: #d4af37; color: #d4af37; }
.tech-prereq, .tech-obsolete, .nation-prereq { font-size: 0.85rem; padding: 2px 8px; border-radius: 4px; }
.tech-prereq { background: #2a4a2a; color: #8f8; }
.tech-obsolete { background: #4a2a2a; color: #f88; }
.nation-prereq { background: #2a2a4a; color: #88f; }
.event-source { margin-top: 10px; padding: 8px; background: #2d1f3d; border: 1px solid #6b3fa0; border-radius: 4px; font-size: 0.85rem; }
.event-only-badge { display: inline-block; background: #6b3fa0; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-right: 8px; }
.event-name { display: block; color: #c9a0dc; margin-top: 5px; }
.event-trigger { display: block; color: #a88fbc; margin-top: 3px; font-style: italic; }
.requirements { margin-top: 10px; padding-top: 10px; border-top: 1px solid #333; font-size: 0.9rem; color: #aaa; }
.requirements strong { color: #d4af37; }
.dlc-badge { background: #4a3a2a; color: #da8; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; margin-left: 8px; }
.legend { background: #252540; border-radius: 8px; padding: 20px; }
.legend h3 { color: #d4af37; margin-bottom: 15px; font-size: 1rem; }
.legend-content { display: flex; flex-direction: column; gap: 10px; }
.legend-item { display: flex; align-items: center; gap: 15px; font-size: 0.9rem; color: #888; }
.legend-item > span:first-child { flex-shrink: 0; }
.loading { text-align: center; padding: 40px; color: #888; }
@media (max-width: 768px) {
    .container { padding: 15px; }
    header h1 { font-size: 1.5rem; }
    .filter-row { flex-direction: column; gap: 15px; }
    .filter-group { min-width: 100%; }
    .ambition-header { flex-direction: column; gap: 8px; }
    .ambition-meta { order: -1; }
}
.ambition-card[data-class="1"] { border-left-color: #e6b422; }
.ambition-card[data-class="2"] { border-left-color: #9b59b6; }
.ambition-card[data-class="3"] { border-left-color: #3498db; }
.ambition-card[data-class="4"] { border-left-color: #e74c3c; }
.ambition-card[data-class="5"] { border-left-color: #2ecc71; }
.ambition-card[data-class="6"] { border-left-color: #f39c12; }
.ambition-card[data-class="7"] { border-left-color: #1abc9c; }
.ambition-card[data-class="8"] { border-left-color: #27ae60; }
.ambition-card[data-class="9"] { border-left-color: #8e44ad; }
.ambition-card[data-class="10"] { border-left-color: #e91e63; }
.ambition-card[data-class="11"] { border-left-color: #009688; }
.ambition-card[data-class="12"] { border-left-color: #673ab7; }
.ambition-card[data-class="13"] { border-left-color: #ff5722; }
.ambition-card[data-class="14"] { border-left-color: #03a9f4; }
.ambition-card[data-class="15"] { border-left-color: #9c27b0; }
.ambition-card[data-class="16"] { border-left-color: #00bcd4; }
.ambition-card[data-class="17"] { border-left-color: #f44336; }
.ambition-card[data-class="18"] { border-left-color: #ff9800; }
.ambition-card[data-class="19"] { border-left-color: #795548; }
.ambition-card[data-class="20"] { border-left-color: #607d8b; }
.ambition-card[data-class="21"] { border-left-color: #4caf50; }
.ambition-card[data-class="22"] { border-left-color: #00bcd4; }
.ambition-card[data-class="23"] { border-left-color: #ff9800; }
.ambition-card[data-class="24"] { border-left-color: #e91e63; }
.ambition-card[data-class="25"] { border-left-color: #f44336; }
.ambition-card[data-class="26"] { border-left-color: #4caf50; }
.ambition-card[data-class="27"] { border-left-color: #9e9e9e; }
.ambition-card[data-class="28"] { border-left-color: #9c27b0; }
.ambition-card[data-class="29"] { border-left-color: #607d8b; }
.ambition-card[data-class="30"] { border-left-color: #212121; }
.ambition-card[data-class="31"] { border-left-color: #795548; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Old World Ambition Viewer</h1>
            <p class="subtitle">Understand which ambitions you can get and when</p>
        </header>

        <div class="main-layout">
            <aside class="sidebar">
                <section class="filters">
                    <div class="filter-group">
                        <label for="nation-select">Nation</label>
                        <select id="nation-select">
                            <option value="">Any Nation</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label>Your Families</label>
                        <div id="family-checkboxes" class="checkbox-group"></div>
                    </div>
                    <div class="filter-group">
                        <label>Accepted Ambitions</label>
                        <div class="completed-buttons" id="completed-buttons">
                            <button class="completed-btn active" data-count="all">All</button>
                            <button class="completed-btn" data-count="0">0</button>
                            <button class="completed-btn" data-count="1">1</button>
                            <button class="completed-btn" data-count="2">2</button>
                            <button class="completed-btn" data-count="3">3</button>
                            <button class="completed-btn" data-count="4">4</button>
                            <button class="completed-btn" data-count="5">5</button>
                            <button class="completed-btn" data-count="6">6</button>
                            <button class="completed-btn" data-count="7">7</button>
                            <button class="completed-btn" data-count="8">8</button>
                            <button class="completed-btn" data-count="9">9</button>
                        </div>
                    </div>
                    <div class="filter-group">
                        <label for="class-select">Category</label>
                        <select id="class-select">
                            <option value="">All Categories</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label for="search-input">Search</label>
                        <input type="text" id="search-input" placeholder="Search...">
                    </div>
                    <div class="filter-group">
                        <label class="checkbox-label">
                            <input type="checkbox" id="show-unavailable"> Show unavailable
                        </label>
                    </div>
                </section>
            </aside>
            <main class="content">
                <div class="result-header">
                    <span id="result-count">0 ambitions</span>
                </div>
                <div id="ambitions-list" class="ambitions-list"></div>
            </main>
        </div>

        <section class="legend">
            <h3>Understanding Ambitions</h3>
            <div class="legend-content">
                <div class="legend-item">
                    <span class="tier-badge">T1-2</span>
                    <span>Tier range the ambition can appear at</span>
                </div>
                <div class="legend-item">
                    <span class="family-tag">Landowners</span>
                    <span>Family preference - matching families get priority, but any goal can still be offered</span>
                </div>
                <div class="legend-item">
                    <span class="tech-prereq">Requires: Forestry</span>
                    <span>Tech prerequisite - must research this tech first</span>
                </div>
                <div class="legend-item">
                    <span class="tech-obsolete">Obsolete: Rhetoric</span>
                    <span>Tech obsolete - no longer available after researching this tech</span>
                </div>
            </div>
        </section>
    </div>

    <script>
let data = null;
let selectedNation = '';
let selectedFamilies = new Set();
let completedCount = 'all'; // 'all' or 0-9

const nationSelect = document.getElementById('nation-select');
const familyCheckboxes = document.getElementById('family-checkboxes');
const completedButtons = document.getElementById('completed-buttons');
const classSelect = document.getElementById('class-select');
const searchInput = document.getElementById('search-input');
const showUnavailable = document.getElementById('show-unavailable');
const resultCount = document.getElementById('result-count');
const ambitionsList = document.getElementById('ambitions-list');

// Load data from JSON file
async function loadData() {
    try {
        ambitionsList.innerHTML = '<div class="loading">Loading ambitions...</div>';
        const response = await fetch('data/ambitions.json');
        data = await response.json();
        initializeUI();
        filterAndRender();
    } catch (error) {
        console.error('Failed to load data:', error);
        ambitionsList.innerHTML = '<div class="loading">Failed to load ambition data.</div>';
    }
}

function initializeUI() {
    const nations = Object.values(data.nations).filter(n => !n.dlc).sort((a, b) => a.name.localeCompare(b.name));
    const dlcNations = Object.values(data.nations).filter(n => n.dlc).sort((a, b) => a.name.localeCompare(b.name));

    nations.forEach(nation => {
        const option = document.createElement('option');
        option.value = nation.id;
        option.textContent = nation.name;
        nationSelect.appendChild(option);
    });

    if (dlcNations.length > 0) {
        const optgroup = document.createElement('optgroup');
        optgroup.label = 'DLC Nations';
        dlcNations.forEach(nation => {
            const option = document.createElement('option');
            option.value = nation.id;
            option.textContent = nation.name + ' (' + nation.dlc + ')';
            optgroup.appendChild(option);
        });
        nationSelect.appendChild(optgroup);
    }

    Object.entries(data.ambitionClasses).sort((a, b) => a[1].localeCompare(b[1])).forEach(([id, name]) => {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = name;
        classSelect.appendChild(option);
    });

    updateFamilyCheckboxes();
    setupCompletedButtons();
    nationSelect.addEventListener('change', handleNationChange);
    classSelect.addEventListener('change', filterAndRender);
    searchInput.addEventListener('input', debounce(filterAndRender, 200));
    showUnavailable.addEventListener('change', filterAndRender);
}

function setupCompletedButtons() {
    completedButtons.querySelectorAll('.completed-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            completedButtons.querySelectorAll('.completed-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            completedCount = btn.dataset.count;
            filterAndRender();
        });
    });
}

function updateFamilyCheckboxes() {
    familyCheckboxes.innerHTML = '';
    const families = Object.values(data.familyClasses).sort((a, b) => a.name.localeCompare(b.name));
    let availableFamilies = new Set();
    if (selectedNation && data.nations[selectedNation]) {
        data.nations[selectedNation].familyClasses.forEach(fc => availableFamilies.add(fc));
    }

    families.forEach(family => {
        const label = document.createElement('label');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = family.id;
        const isAvailable = !selectedNation || availableFamilies.has(family.id);
        if (!isAvailable) {
            label.classList.add('unavailable');
            checkbox.disabled = true;
            selectedFamilies.delete(family.id);
        }
        if (selectedFamilies.has(family.id)) {
            checkbox.checked = true;
            label.classList.add('checked');
        }
        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) { selectedFamilies.add(family.id); label.classList.add('checked'); }
            else { selectedFamilies.delete(family.id); label.classList.remove('checked'); }
            filterAndRender();
        });
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(family.name));
        familyCheckboxes.appendChild(label);
    });
}

function handleNationChange(e) {
    selectedNation = e.target.value;
    updateFamilyCheckboxes();
    filterAndRender();
}

function filterAndRender() {
    const selectedClass = classSelect.value;
    const searchTerm = searchInput.value.toLowerCase().trim();
    const showUnavail = showUnavailable.checked;

    // Calculate tier from completed count
    let tierFilter = null;
    if (completedCount !== 'all') {
        tierFilter = parseInt(completedCount) + 1; // tier = completed + 1
    }

    // Separate national vs regular ambitions
    const nationalAmbitions = data.ambitions.filter(a => a.flags?.victoryEligible && a.minTier === 10);
    const regularAmbitions = data.ambitions.filter(a => !(a.flags?.victoryEligible && a.minTier === 10));

    const filterAmbitions = (ambitions) => ambitions.filter(ambition => {
        // Filter by tier (if specific count selected)
        if (tierFilter !== null) {
            if (ambition.minTier > tierFilter || ambition.maxTier < tierFilter) return false;
        }
        // Filter by class
        if (selectedClass && ambition.ambitionClass !== parseInt(selectedClass)) return false;
        // Filter by search term
        if (searchTerm) {
            const searchableText = [ambition.name, ambition.ambitionClassName, ambition.helpText || '',
                ...(ambition.filters?.familyClassNames || [])].join(' ').toLowerCase();
            if (!searchableText.includes(searchTerm)) return false;
        }
        return true;
    });

    const filteredRegular = filterAmbitions(regularAmbitions);
    const filteredNational = filterAmbitions(nationalAmbitions);

    const processAmbitions = (ambitions) => {
        const withAvailability = ambitions.map(ambition => {
            const availability = checkAvailability(ambition);
            return { ...ambition, availability };
        });
        withAvailability.sort((a, b) => {
            if (a.availability.available !== b.availability.available) return a.availability.available ? -1 : 1;
            if (a.minTier !== b.minTier) return a.minTier - b.minTier;
            return a.name.localeCompare(b.name);
        });
        return showUnavail ? withAvailability : withAvailability.filter(a => a.availability.available);
    };

    const finalRegular = processAmbitions(filteredRegular);
    const finalNational = processAmbitions(filteredNational);

    const availableRegular = filteredRegular.filter(a => checkAvailability(a).available).length;
    const availableNational = filteredNational.filter(a => checkAvailability(a).available).length;

    let tierText = tierFilter ? ' at Tier ' + tierFilter : '';
    resultCount.textContent = availableRegular + ' available' + tierText + ' (' + filteredRegular.length + ' total) + ' + availableNational + ' national';

    renderAmbitions(finalRegular, finalNational);
}

function checkAvailability(ambition) {
    const result = { available: true, reasons: [] };
    const filters = ambition.filters || {};
    if (filters.nationPrereq && selectedNation && filters.nationPrereq !== selectedNation) {
        result.available = false;
        result.reasons.push('Requires ' + filters.nationPrereqName);
    }
    if (filters.familyClasses && filters.familyClasses.length > 0 && selectedFamilies.size > 0) {
        const hasMatchingFamily = filters.familyClasses.some(fc => selectedFamilies.has(fc));
        if (!hasMatchingFamily) {
            result.available = false;
            result.reasons.push('Preferred by: ' + filters.familyClassNames.join(', '));
        }
    }
    return result;
}

function renderAmbitions(regular, national) {
    if (regular.length === 0 && national.length === 0) {
        ambitionsList.innerHTML = '<div class="loading">No ambitions match your filters.</div>';
        return;
    }

    const renderCard = (ambition, isNational = false) => {
        const filters = ambition.filters || {};
        const requirements = ambition.requirements || {};
        const isAvailable = ambition.availability.available;
        const unavailClass = isAvailable ? '' : 'unavailable';

        let familyTags = '';
        if (filters.familyClassNames && filters.familyClassNames.length > 0) {
            familyTags = filters.familyClassNames.map((name, i) => {
                const familyId = filters.familyClasses[i];
                const isActive = selectedFamilies.has(familyId);
                return '<span class="family-tag ' + (isActive ? 'active' : '') + '">' + name + '</span>';
            }).join('');
        }

        let techInfo = '';
        if (filters.techPrereqName) techInfo += '<span class="tech-prereq">Requires: ' + filters.techPrereqName + '</span>';
        if (filters.techObsoleteName) techInfo += '<span class="tech-obsolete">Obsolete: ' + filters.techObsoleteName + '</span>';
        if (filters.nationPrereqName) techInfo += '<span class="nation-prereq">' + filters.nationPrereqName + ' only</span>';

        let reqText = formatRequirements(requirements);
        let dlcBadge = ambition.dlc ? '<span class="dlc-badge">' + ambition.dlc + '</span>' : '';

        let eventInfo = '';
        if (ambition.eventSource && ambition.eventSource.eventName) {
            const eventDlc = ambition.eventSource.eventDlc ? ' (' + ambition.eventSource.eventDlc + ')' : '';
            eventInfo = '<div class="event-source">' +
                '<span class="event-only-badge">Event Only</span>' +
                '<span class="event-name">Event: "' + ambition.eventSource.eventName + '"' + eventDlc + '</span>' +
                '<span class="event-trigger">Trigger: ' + ambition.eventSource.trigger + '</span>' +
            '</div>';
        } else if (ambition.eventSource) {
            eventInfo = '<div class="event-source">' +
                '<span class="event-only-badge">Unavailable</span>' +
                '<span class="event-trigger">' + ambition.eventSource.trigger + '</span>' +
            '</div>';
        }

        const nationalClass = isNational ? ' national' : '';
        return '<div class="ambition-card ' + unavailClass + nationalClass + '" data-class="' + ambition.ambitionClass + '">' +
            '<div class="ambition-header">' +
                '<span class="ambition-name">' + ambition.name + dlcBadge + '</span>' +
                '<div class="ambition-meta">' +
                    '<span class="tier-badge">T' + ambition.minTier + (ambition.minTier !== ambition.maxTier ? '-' + ambition.maxTier : '') + '</span>' +
                    '<span class="category-badge">' + ambition.ambitionClassName + '</span>' +
                '</div>' +
            '</div>' +
            '<div class="ambition-details">' +
                (familyTags ? '<div class="family-tags">' + familyTags + '</div>' : '') +
                techInfo +
            '</div>' +
            eventInfo +
            (reqText ? '<div class="requirements">' + reqText + '</div>' : '') +
        '</div>';
    };

    let html = regular.map(a => renderCard(a, false)).join('');

    if (national.length > 0) {
        html += '<div class="national-section"><h2>National Ambitions (Victory)</h2>' +
                national.map(a => renderCard(a, true)).join('') + '</div>';
    }

    ambitionsList.innerHTML = html;
}

function formatRequirements(req) {
    if (!req || Object.keys(req).length === 0) return '';
    const parts = [];
    if (req.lawName) parts.push('Enact <strong>' + req.lawName + '</strong>');
    if (req.theologyName) parts.push('Establish <strong>' + req.theologyName + '</strong>');
    if (req.cities) parts.push('Control <strong>' + req.cities + '</strong> cities');
    if (req.connectedCities) parts.push('Have <strong>' + req.connectedCities + '</strong> connected cities');
    if (req.population) parts.push('Reach <strong>' + req.population + '</strong> population');
    if (req.wonders) parts.push('Build <strong>' + req.wonders + '</strong> wonders');
    if (req.laws) parts.push('Enact <strong>' + req.laws + '</strong> laws');
    if (req.militaryUnits) parts.push('Have <strong>' + req.militaryUnits + '</strong> military units');
    if (req.stateReligion) parts.push('Have a <strong>State Religion</strong>');

    ['yieldProduced', 'yieldRate', 'yieldStockpile', 'improvements', 'specialists', 'units', 'projects'].forEach(field => {
        if (req[field] && Array.isArray(req[field])) {
            req[field].forEach(item => parts.push('<strong>' + item.value + '</strong> ' + item.typeName));
        }
    });
    if (req.techNames && req.techNames.length > 0) {
        parts.push('Research: <strong>' + req.techNames.join('</strong> and <strong>') + '</strong>');
    }
    return parts.join(' | ');
}

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    };
}

document.addEventListener('DOMContentLoaded', loadData);
    </script>
</body>
</html>'''

    # No longer embedding data - it's fetched from data/ambitions.json
    return html_template


def main():
    print("Old World Ambition Parser")
    print("=" * 40)

    # Check reference directory exists
    if not REFERENCE_DIR.exists():
        print(f"Error: Reference directory not found at {REFERENCE_DIR}")
        print("Make sure the game files are copied to the Reference folder.")
        return 1

    # Parse data
    goals = parse_goals()
    family_classes = parse_family_classes()
    nations = parse_nations()

    print(f"\nParsed {len(family_classes)} family classes")
    print(f"Parsed {len(nations)} nations")

    # Build output
    output = {
        "version": "1.0",
        "generatedAt": datetime.now().isoformat(),
        "ambitionClasses": AMBITION_CLASS_NAMES,
        "familyClasses": family_classes,
        "nations": nations,
        "ambitions": goals
    }

    # Ensure output directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON output
    print(f"\nWriting JSON to {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Generate standalone HTML
    standalone_html = generate_standalone_html(output)
    standalone_file = PROJECT_DIR / "viewer" / "index.html"
    print(f"Writing standalone HTML to {standalone_file}")
    with open(standalone_file, "w", encoding="utf-8") as f:
        f.write(standalone_html)

    print("Done!")
    return 0


if __name__ == "__main__":
    exit(main())
