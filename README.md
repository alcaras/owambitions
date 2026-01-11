# Old World Ambition Viewer

A standalone HTML viewer that helps Old World players understand which ambitions they can get based on their nation, families, and current game state.

**[View the Ambition Viewer](https://yourusername.github.io/owambitions/viewer/index.html)** *(update URL after deploying)*

## What This Does

When playing Old World, players are offered ambitions to choose from. This viewer helps answer:
- Which ambitions are available at my current tier?
- Which families prefer which ambitions?
- What are the requirements for each ambition?
- When do National Ambitions appear?

## Key Game Mechanics

### Tier Calculation
Your ambition tier equals the number of ambitions you've accepted plus one:
```
tier = accepted_ambitions + 1
```
This counts both active and completed ambitions. For example:
- Start of game: 0 accepted = Tier 1
- After accepting first ambition: 1 accepted = Tier 2
- And so on up to Tier 10

### Family Preferences
Family class (Landowners, Clerics, etc.) is a **priority-based tie-breaker**, not a probability modifier. When the game selects which ambitions to offer:
1. It finds all valid ambitions for your current tier
2. Ambitions matching your family's preference get priority in selection
3. But any valid ambition can still be offered

### National Ambitions
National Ambitions are special tier-10 ambitions with the `victoryEligible` flag. They appear when:
- You reach Tier 10 (9 accepted ambitions)
- You reach **70% victory progress**

They are separated into their own section in the viewer.

## Project Structure

```
owambitions/
├── parser/
│   └── parse.py          # Extracts data from game XML files
├── viewer/
│   ├── index.html        # Standalone HTML viewer (generated)
│   └── data/
│       └── ambitions.json  # Extracted ambition data
├── Reference/            # Game files (not in repo, see .gitignore)
├── SPEC.md              # Technical specification
└── README.md            # This file
```

## Regenerating the Data

If the game updates or you want to regenerate the viewer:

1. **Copy game files**: Copy the `Reference` folder from your Old World installation to this project root:
   ```
   # macOS Steam location:
   ~/Library/Application Support/Steam/steamapps/common/Old World/Reference/
   ```

2. **Run the parser**:
   ```bash
   cd parser
   python parse.py
   ```
   This generates:
   - `viewer/data/ambitions.json` - Raw JSON data
   - `viewer/index.html` - Standalone HTML viewer with embedded data

3. **Commit and push** the updated `viewer/` folder (Reference/ is gitignored)

## Viewer Features

- **Nation Selection**: Filter ambitions by nation-specific requirements
- **Family Checkboxes**: See which ambitions your families prefer
- **Accepted Ambitions**: Filter by tier (0-9 accepted ambitions)
- **Category Filter**: Filter by ambition class (Military, Economic, etc.)
- **Search**: Full-text search across ambition names and requirements
- **Show Unavailable**: Toggle to see ambitions that don't match your filters
- **National Ambitions**: Separate section for victory-eligible tier-10 ambitions

## Data Sources

The parser extracts data from these game XML files:
- `goal.xml` - Ambition definitions (328 total)
- `text-infos.xml` / `text-helptext.xml` - Display text
- `nation.xml` - Nations and their properties
- `family.xml` - Family classes and nation associations
- `familyClass.xml` - Family class definitions
- `law.xml`, `tech.xml`, `improvement.xml`, etc. - Cross-references

## Technical Notes

- The viewer is a single self-contained HTML file (~195KB) with embedded CSS, JS, and JSON data
- No server required - works directly from file:// or any static host
- DLC content is marked but included
- Scenario-only content is excluded

## License

This is a fan-made tool for Old World by Mohawk Games. Game data belongs to Mohawk Games/Hooded Horse.
