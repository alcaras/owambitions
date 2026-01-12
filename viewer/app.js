/**
 * Old World Ambition Viewer
 *
 * Helps players understand which ambitions they can get based on their
 * nation, families, and current game state.
 */

let data = null;
let selectedNation = '';
let selectedFamilies = new Set();

// DOM elements
const nationSelect = document.getElementById('nation-select');
const familyCheckboxes = document.getElementById('family-checkboxes');
const tierMin = document.getElementById('tier-min');
const tierMax = document.getElementById('tier-max');
const classSelect = document.getElementById('class-select');
const searchInput = document.getElementById('search-input');
const showUnavailable = document.getElementById('show-unavailable');
const resultCount = document.getElementById('result-count');
const ambitionsList = document.getElementById('ambitions-list');

/**
 * Load the ambition data from JSON
 */
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

/**
 * Initialize UI elements with data
 */
function initializeUI() {
    // Populate nation dropdown
    const nations = Object.values(data.nations)
        .filter(n => !n.dlc) // Base game nations first
        .sort((a, b) => a.name.localeCompare(b.name));

    const dlcNations = Object.values(data.nations)
        .filter(n => n.dlc)
        .sort((a, b) => a.name.localeCompare(b.name));

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
            option.textContent = `${nation.name} (${nation.dlc})`;
            nationSelect.appendChild(option);
        });
    }

    // Populate category dropdown (alphabetically)
    const classes = Object.entries(data.ambitionClasses)
        .sort((a, b) => a[1].localeCompare(b[1]));

    classes.forEach(([id, name]) => {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = name;
        classSelect.appendChild(option);
    });

    // Populate family checkboxes
    updateFamilyCheckboxes();

    // Event listeners
    nationSelect.addEventListener('change', handleNationChange);
    tierMin.addEventListener('change', filterAndRender);
    tierMax.addEventListener('change', filterAndRender);
    classSelect.addEventListener('change', filterAndRender);
    searchInput.addEventListener('input', debounce(filterAndRender, 200));
    showUnavailable.addEventListener('change', filterAndRender);
}

/**
 * Update family checkboxes based on selected nation
 */
function updateFamilyCheckboxes() {
    familyCheckboxes.innerHTML = '';

    const families = Object.values(data.familyClasses)
        .sort((a, b) => a.name.localeCompare(b.name));

    // Get available families for selected nation
    let availableFamilies = new Set();
    if (selectedNation && data.nations[selectedNation]) {
        data.nations[selectedNation].familyClasses.forEach(fc => {
            availableFamilies.add(fc);
        });
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
            // Uncheck if was selected but now unavailable
            selectedFamilies.delete(family.id);
        }

        if (selectedFamilies.has(family.id)) {
            checkbox.checked = true;
            label.classList.add('checked');
        }

        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                selectedFamilies.add(family.id);
                label.classList.add('checked');
            } else {
                selectedFamilies.delete(family.id);
                label.classList.remove('checked');
            }
            filterAndRender();
        });

        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(family.name));
        familyCheckboxes.appendChild(label);
    });
}

/**
 * Handle nation selection change
 */
function handleNationChange(e) {
    selectedNation = e.target.value;
    updateFamilyCheckboxes();
    filterAndRender();
}

/**
 * Filter ambitions and render the list
 */
function filterAndRender() {
    if (!data) return;

    const minTier = parseInt(tierMin.value);
    const maxTier = parseInt(tierMax.value);
    const selectedClass = classSelect.value;
    const searchTerm = searchInput.value.toLowerCase().trim();
    const showUnavail = showUnavailable.checked;

    // Filter ambitions
    const filtered = data.ambitions.filter(ambition => {
        // Filter by tier
        if (ambition.maxTier < minTier || ambition.minTier > maxTier) {
            return false;
        }

        // Filter by class
        if (selectedClass && ambition.ambitionClass !== parseInt(selectedClass)) {
            return false;
        }

        // Filter by search term
        if (searchTerm) {
            const searchableText = [
                ambition.name,
                ambition.ambitionClassName,
                ambition.helpText || '',
                ...(ambition.filters?.familyClassNames || []),
            ].join(' ').toLowerCase();

            if (!searchableText.includes(searchTerm)) {
                return false;
            }
        }

        return true;
    });

    // Determine availability for each ambition
    const ambitionsWithAvailability = filtered.map(ambition => {
        const availability = checkAvailability(ambition);
        return { ...ambition, availability };
    });

    // Sort: available first, then by tier (low to high), then by name
    ambitionsWithAvailability.sort((a, b) => {
        // Available first
        if (a.availability.available !== b.availability.available) {
            return a.availability.available ? -1 : 1;
        }
        // Then by min tier
        if (a.minTier !== b.minTier) {
            return a.minTier - b.minTier;
        }
        // Then by name
        return a.name.localeCompare(b.name);
    });

    // Filter out unavailable if checkbox not checked
    const finalList = showUnavail
        ? ambitionsWithAvailability
        : ambitionsWithAvailability.filter(a => a.availability.available);

    // Update result count
    const availableCount = ambitionsWithAvailability.filter(a => a.availability.available).length;
    resultCount.textContent = `${availableCount} available of ${filtered.length} ambitions`;

    // Render
    renderAmbitions(finalList);
}

/**
 * Check if an ambition is available based on current selections
 */
function checkAvailability(ambition) {
    const result = {
        available: true,
        reasons: []
    };

    const filters = ambition.filters || {};

    // Check nation prerequisite
    if (filters.nationPrereq && selectedNation) {
        if (filters.nationPrereq !== selectedNation) {
            result.available = false;
            result.reasons.push(`Requires ${filters.nationPrereqName}`);
        }
    }

    // Check family class preferences
    // An ambition is "available" if at least one of its preferred families matches selected families
    // If no families selected, all are potentially available
    if (filters.familyClasses && filters.familyClasses.length > 0 && selectedFamilies.size > 0) {
        const hasMatchingFamily = filters.familyClasses.some(fc => selectedFamilies.has(fc));
        if (!hasMatchingFamily) {
            result.available = false;
            result.reasons.push(`Preferred by: ${filters.familyClassNames.join(', ')}`);
        }
    }

    return result;
}

/**
 * Render the ambitions list
 */
function renderAmbitions(ambitions) {
    if (ambitions.length === 0) {
        ambitionsList.innerHTML = '<div class="loading">No ambitions match your filters.</div>';
        return;
    }

    ambitionsList.innerHTML = ambitions.map(ambition => {
        const filters = ambition.filters || {};
        const requirements = ambition.requirements || {};
        const flags = ambition.flags || {};

        const isAvailable = ambition.availability.available;
        const unavailClass = isAvailable ? '' : 'unavailable';

        // Build family tags
        let familyTags = '';
        if (filters.familyClassNames && filters.familyClassNames.length > 0) {
            familyTags = filters.familyClassNames.map(name => {
                const familyId = filters.familyClasses[filters.familyClassNames.indexOf(name)];
                const isActive = selectedFamilies.has(familyId);
                return `<span class="family-tag ${isActive ? 'active' : ''}">${name}</span>`;
            }).join('');
        }

        // Build tech/nation info
        let techInfo = '';
        if (filters.techPrereqName) {
            techInfo += `<span class="tech-prereq">Requires: ${filters.techPrereqName}</span>`;
        }
        if (filters.techObsoleteName) {
            techInfo += `<span class="tech-obsolete">Obsolete: ${filters.techObsoleteName}</span>`;
        }
        if (filters.nationPrereqName) {
            techInfo += `<span class="nation-prereq">${filters.nationPrereqName} only</span>`;
        }

        // Build requirements text
        let reqText = formatRequirements(requirements);

        // DLC badge
        let dlcBadge = ambition.dlc ? `<span class="dlc-badge">${ambition.dlc}</span>` : '';

        return `
            <div class="ambition-card ${unavailClass}" data-class="${ambition.ambitionClass}">
                <div class="ambition-header">
                    <span class="ambition-name">${ambition.name}${dlcBadge}</span>
                    <div class="ambition-meta">
                        <span class="tier-badge">T${ambition.minTier}${ambition.minTier !== ambition.maxTier ? '-' + ambition.maxTier : ''}</span>
                        <span class="category-badge">${ambition.ambitionClassName}</span>
                    </div>
                </div>
                <div class="ambition-details">
                    ${familyTags ? `<div class="family-tags">${familyTags}</div>` : ''}
                    ${techInfo}
                </div>
                ${reqText ? `<div class="requirements">${reqText}</div>` : ''}
            </div>
        `;
    }).join('');
}

/**
 * Format requirements into readable text
 */
function formatRequirements(req) {
    if (!req || Object.keys(req).length === 0) return '';

    const parts = [];

    // Simple requirements
    if (req.lawName) parts.push(`Enact <strong>${req.lawName}</strong>`);
    if (req.theologyName) parts.push(`Establish <strong>${req.theologyName}</strong>`);
    if (req.cities) parts.push(`Control <strong>${req.cities}</strong> cities`);
    if (req.connectedCities) parts.push(`Have <strong>${req.connectedCities}</strong> connected cities`);
    if (req.population) parts.push(`Reach <strong>${req.population}</strong> population`);
    if (req.legitimacy) parts.push(`Reach <strong>${req.legitimacy}</strong> legitimacy`);
    if (req.wonders) parts.push(`Build <strong>${req.wonders}</strong> wonders`);
    if (req.laws) parts.push(`Enact <strong>${req.laws}</strong> laws`);
    if (req.militaryUnits) parts.push(`Have <strong>${req.militaryUnits}</strong> military units`);
    if (req.stateReligion) parts.push(`Have a <strong>State Religion</strong>`);
    if (req.diplomacyAllName) parts.push(`<strong>${req.diplomacyAllName}</strong> with all nations`);

    // Typed counts
    const typedFields = ['yieldProduced', 'yieldRate', 'yieldStockpile', 'improvements',
                         'specialists', 'units', 'projects', 'techs'];

    typedFields.forEach(field => {
        if (req[field]) {
            if (Array.isArray(req[field])) {
                req[field].forEach(item => {
                    parts.push(`<strong>${item.value}</strong> ${item.typeName}`);
                });
            }
        }
    });

    // Tech list
    if (req.techNames && req.techNames.length > 0) {
        parts.push(`Research: <strong>${req.techNames.join('</strong> and <strong>')}</strong>`);
    }

    return parts.join(' | ');
}

/**
 * Debounce helper
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize on load
document.addEventListener('DOMContentLoaded', loadData);
