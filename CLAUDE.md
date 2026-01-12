# CLAUDE.md

This file documents how this project was built and provides context for future development.

## Project Overview

**Old World Ambition Viewer** - A tool to help Old World players understand which ambitions they can get based on their nation, families, and current game state.

Live at: https://alcaras.github.io/owambitions/

## What Was Built

### 1. Parser (`parser/parse.py`)

A Python script that extracts ambition data from Old World's game files:

**Input**: Game XML files from `Reference/XML/Infos/` directory:
- `goal.xml` - 328 ambition definitions
- `text-infos.xml`, `text-helptext.xml` - Display text and descriptions
- `nation.xml`, `family.xml`, `familyClass.xml` - Nations and family mappings
- `law.xml`, `tech.xml`, `improvement.xml`, etc. - Cross-references for requirements

**Output**:
- `viewer/data/ambitions.json` - Structured JSON with all ambition data
- `viewer/index.html` - HTML viewer that fetches JSON at runtime

**Key parsing logic**:
- Resolves text references (e.g., `TEXT_AMBITION_BUILD_LIBRARY` → "Build a Library")
- Maps nations to their available family classes via `family.xml` abNation pairs
- Extracts requirements: laws, techs, cities, population, yields, etc.
- Marks DLC content, excludes scenario-only ambitions

### 2. Viewer (`viewer/index.html`)

A standalone HTML viewer that works without a server:

**Features**:
- **Nation selector**: Filters by nation-specific requirements, shows available families
- **Family checkboxes**: Highlight ambitions preferred by selected families
- **Accepted Ambitions buttons (0-9)**: Filter by tier based on game progress
- **Category filter**: Filter by ambition class (Military, Economic, etc.)
- **Search**: Full-text search across names and requirements
- **Show Unavailable toggle**: See filtered-out ambitions
- **National Ambitions section**: Separate display for victory-eligible tier-10 ambitions

**Layout**: Sidebar with filters on left, scrollable ambition cards on right

### 3. GitHub Pages Deployment

- `.github/workflows/deploy.yml` - Deploys `viewer/` folder to GitHub Pages on push
- `.gitignore` - Excludes `Reference/` folder (game files not in repo)

## Key Game Mechanics Discovered

Research into Old World's source code (`Reference/Source/`) revealed:

### Tier Calculation
```csharp
// From PlayerGoal.cs
int iMinTier = (countNumAmbitions() + 1);
```
Tier = number of accepted ambitions + 1. Counts both active and completed.

### Family Preferences
Family class is a **priority-based tie-breaker**, not probability:
```csharp
// From PlayerGoal.cs - isBetterGoal()
bFamilyClassGoal = infos().goal(eLoopGoal).maeFamilyClass.Contains(game().getFamilyClass(eLoopFamily));
```
Goals matching family class get selection priority, but any valid goal can be offered.

### National Ambitions
- Appear at Tier 10 with `bVictoryEligible` flag
- Triggered at 70% victory progress (`NATIONAL_AMBITION_OFFER_THRESHOLD_PERCENT` in `globalsInt.xml`)

### Event-Only Ambitions
Some ambitions have `subjectWeight=0`, meaning they cannot be randomly offered - they can only be assigned through specific in-game events. The parser includes hardcoded event source data for these 13 ambitions:

| Goal ID | Event Name | DLC | Trigger |
|---------|------------|-----|---------|
| GOAL_LOSE_A_CITY | Strength and Weakness | Behind the Throne | Leader must be Insane, 3+ upset families |
| GOAL_FURIOUS_FAMILY | Strength and Weakness | Behind the Throne | Leader must be Insane, 3+ upset families |
| GOAL_TO_BE_KING | To Be A King/Queen | Base | Regent ruling with Rightful Heir alive |
| GOAL_THE_GREAT | The Road to Glory | Base | Young leader (under 30) with 2+ dead ancestors |
| GOAL_DESTROY_RIVALS | Rivals chain | Base | At war, breach enemy city |
| GOAL_KILL_CHARACTER | [Character's] Mark | Behind the Throne | Child of leader, angry foreign leader nearby |
| GOAL_HARVEST_WINE | A Refined Palate | Behind the Throne | Leader has high Charisma, unclaimed wine nearby |
| GOAL_TAKE_HANGING_GARDENS | The Jewel of [Nation] | Behind the Throne | Another nation owns Hanging Gardens |
| GOAL_TAKE_CITY | Various events | Base/BTT | Rivalry or conquest chains |
| GOAL_STATE_RELIGION_SPECIFIC | The Tutor Kartir | Sacred and Profane | Zoroastrian city, Kartir tutor |
| GOAL_EIGHT_RELIGION_SPREAD_SPECIFIC | In Heaven as on Earth | Sacred and Profane | Augustine, Christianity, High Synod |
| GOAL_FOUR_RELIGION_SPREAD_SPECIFIC | Religion events | Sacred and Profane | Religion-specific chains |
| GOAL_2000_EACH_YIELD | (none) | - | Unused/placeholder |

Event source data is stored in `EVENT_ONLY_AMBITIONS` dict in `parse.py` and included in JSON output as `eventSource` field.

## How to Update

1. Copy `Reference/` folder from Old World installation to project root
2. Run `python parser/parse.py`
3. Commit and push - GitHub Actions deploys automatically

## File Structure

```
owambitions/
├── .github/workflows/deploy.yml  # GitHub Pages deployment
├── .gitignore                    # Excludes Reference/
├── CLAUDE.md                     # This file
├── README.md                     # User-facing documentation
├── SPEC.md                       # Technical specification of XML structure
├── parser/
│   └── parse.py                  # XML parser and HTML generator
├── viewer/
│   ├── index.html               # Viewer (generated, fetches JSON at runtime)
│   ├── app.js                   # Viewer JavaScript (standalone version)
│   ├── style.css                # Viewer styles (standalone version)
│   └── data/
│       └── ambitions.json       # Extracted data (fetched by viewer)
└── Reference/                   # Game files (gitignored)
    └── XML/Infos/*.xml
```

## Development Notes

- The viewer fetches `data/ambitions.json` at runtime (not embedded)
- CSS and JS are embedded in index.html, but JSON is separate for easier maintenance
- Category dropdown is sorted alphabetically
- No build step needed for viewer changes (but re-run parser to regenerate)
- Parser uses only Python standard library (xml.etree, json, pathlib)
- Tested with Old World base game + Behind the Throne + Sacred and Profane DLCs
