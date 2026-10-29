
"use strict";

// Use the same FastAPI server that serves the library page.
const API = window.location.origin;

const $ = id => document.getElementById(id);

let components = [];
let selectedCategory = "all";

// Human-readable labels for catalogue categories.
const categoryLabels = {
  actuator: "Actuators",
  mechanical: "Mechanical",
  power: "Power",
  structure: "Structure",
  sensor: "Sensors",
  electrical: "Electrical",
  robotics: "Robotics",
  aerospace: "Aerospace",
  space: "Space"
};

// Display useful component specifications without assuming every
// component has the same fields.
function getSpecs(component) {
  const specs = [];

  if (Number.isFinite(Number(component.mass_kg))) {
    specs.push(`Mass: ${Number(component.mass_kg)} kg`);
  }

  if (component.max_torque_nm !== undefined) {
    specs.push(`Torque: ${component.max_torque_nm} Nm`);
  }

  if (component.radius_m !== undefined) {
    specs.push(`Radius: ${component.radius_m} m`);
  }

  if (component.voltage_v !== undefined) {
    specs.push(`Voltage: ${component.voltage_v} V`);
  }

  if (component.range_m !== undefined) {
    specs.push(`Range: ${component.range_m} m`);
  }

  return specs;
}

// Build category options from the actual catalogue.
function buildCategoryFilters() {
  const categories = [...new Set(
    components.map(c => c.category).filter(Boolean)
  )].sort();

  const select = $("category-filter");

  select.replaceChildren(new Option("All categories", "all"));

  categories.forEach(category => {
    select.add(new Option(
      categoryLabels[category] || category,
      category
    ));
  });

  const chips = $("category-chips");
  chips.replaceChildren();

  // The chips provide a quicker alternative to the dropdown.
  ["all", ...categories].forEach(category => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "chip";
    button.textContent = category === "all"
      ? "All"
      : categoryLabels[category] || category;

    button.classList.toggle("active", category === selectedCategory);

    button.addEventListener("click", () => {
      selectedCategory = category;
      $("category-filter").value = category;
      render();
    });

    chips.append(button);
  });
}

// Search across component names, IDs, categories, descriptions and tags.
function matchesSearch(component, query) {
  const searchable = [
    component.id,
    component.name,
    component.category,
    component.description,
    component.library,
    component.spec_status,
    ...(component.tags || [])
  ].join(" ").toLowerCase();

  return searchable.includes(query);
}

// Create each card using DOM methods to avoid inserting catalogue text
// directly as HTML.
function createCard(component) {
  const card = document.createElement("article");
  card.className = "component-card";

  const top = document.createElement("div");
  top.className = "card-top";

  const category = document.createElement("span");
  category.className = "category";
  category.textContent =
    categoryLabels[component.category] || component.category || "Other";

  const badge = document.createElement("span");
  badge.className = "badge";
  badge.textContent = component.library === "space"
    ? "SPACE LIBRARY"
    : (component.spec_status || "UNSPECIFIED").toUpperCase();

  top.append(category, badge);

  const title = document.createElement("h3");
  title.textContent = component.name || component.id;

  const description = document.createElement("p");
  description.textContent =
    component.description || "No description provided.";

  const specs = document.createElement("div");
  specs.className = "specs";

  const componentSpecs = getSpecs(component);

  if (componentSpecs.length === 0) {
    const item = document.createElement("span");
    item.className = "spec";
    item.textContent = "Specifications not provided";
    specs.append(item);
  } else {
    componentSpecs.forEach(value => {
      const item = document.createElement("span");
      item.className = "spec";
      item.textContent = value;
      specs.append(item);
    });
  }

  const id = document.createElement("div");
  id.className = "component-id";
  id.textContent = `ID: ${component.id}`;

  const addButton = document.createElement("button");
  addButton.type = "button";
  addButton.className = "add-button";
  addButton.textContent = "Add to 3D Builder";

  addButton.addEventListener("click", () => {
    // The builder reads this ID after it loads the catalogue.
    localStorage.setItem("blueprint_pending_component", component.id);
    window.location.href = "./builder.html";
  });

  card.append(top, title, description, specs, id, addButton);

  return card;
}

// Apply the search, library and category filters.
function render() {
  const query = $("search").value.trim().toLowerCase();
  const library = $("library-filter").value;
  const category = $("category-filter").value;

  const filtered = components.filter(component => {
    const correctLibrary =
      library === "all" ||
      (library === "space"
        ? component.library === "space"
        : component.library !== "space");

    const correctCategory =
      category === "all" || component.category === category;

    return correctLibrary &&
      correctCategory &&
      matchesSearch(component, query);
  });

  const grid = $("component-grid");
  grid.replaceChildren();

  filtered.forEach(component => {
    grid.append(createCard(component));
  });

  $("result-count").textContent =
    `${filtered.length} of ${components.length} components`;

  $("message").hidden = filtered.length !== 0;

  if (filtered.length === 0) {
    $("message").textContent =
      "No matching components. Try another search or filter.";
  }

  // Keep the quick-filter chips in sync with the selected category.
  document.querySelectorAll(".chip").forEach(chip => {
    chip.classList.toggle(
      "active",
      chip.textContent === (
        selectedCategory === "all"
          ? "All"
          : categoryLabels[selectedCategory] || selectedCategory
      )
    );
  });
}

// Load the same catalogue used by the backend simulation.
async function loadLibrary() {
  try {
    const response = await fetch(`${API}/api/components`);

    if (!response.ok) {
      throw new Error(`API returned HTTP ${response.status}`);
    }

    const data = await response.json();
    components = Array.isArray(data.components) ? data.components : [];

    $("api-status").textContent = "Backend connected";
    $("api-status").style.color = "#45d6a0";

    $("total-count").textContent = components.length;
    $("space-count").textContent = components.filter(
      c => c.library === "space"
    ).length;

    $("category-count").textContent = new Set(
      components.map(c => c.category).filter(Boolean)
    ).size;

    buildCategoryFilters();
    render();
  } catch (error) {
    $("api-status").textContent = "Backend unavailable";
    $("api-status").style.color = "#ff777f";

    $("message").hidden = false;
    $("message").textContent =
      `Could not load components: ${error.message}. Start the FastAPI server and refresh.`;

    $("result-count").textContent = "Catalogue unavailable";
  }
}

// Connect the search box and dropdowns.
$("search").addEventListener("input", render);

$("library-filter").addEventListener("change", render);

$("category-filter").addEventListener("change", () => {
  selectedCategory = $("category-filter").value;
  render();
});

loadLibrary();
