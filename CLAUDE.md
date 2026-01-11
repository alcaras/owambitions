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
- `viewer/index.html` - Self-contained HTML viewer (~195KB) with embedded CSS, JS, and data

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
│   ├── index.html               # Standalone viewer (generated)
│   ├── app.js                   # Viewer JavaScript (embedded in index.html)
│   ├── style.css                # Viewer styles (embedded in index.html)
│   └── data/
│       └── ambitions.json       # Extracted data (embedded in index.html)
└── Reference/                   # Game files (gitignored)
    └── XML/Infos/*.xml
```

## Development Notes

- The viewer is self-contained - CSS, JS, and JSON are embedded in index.html
- No build step needed for viewer changes (but re-run parser to regenerate)
- Parser uses only Python standard library (xml.etree, json, pathlib)
- Tested with Old World base game + Pharaohs of the Nile DLC
