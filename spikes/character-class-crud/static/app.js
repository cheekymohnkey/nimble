const STAT_OPTIONS = ["STR", "DEX", "INT", "WIL"];
const DEFAULT_FEATURE_TYPE_OPTIONS = [
  "auto",
  "choice_grant",
  "resource_change",
  "stat_increase",
  "spell_grant",
  "passive",
  "other",
];
const DEFAULT_RESPEC_RULE_OPTIONS = ["never", "level_up_only", "gm_override", "anytime"];
const RESPEC_RULE_LABELS = {
  never: "Never",
  level_up_only: "Level Up Only",
  gm_override: "GM Override",
  anytime: "Anytime",
};

const state = {
  classes: [],
  rulesets: [],
  selectedClassId: null,
  search: "",
  progressionFeatures: [],
  subclasses: [],
  selectedSubclassId: null,
  selectedFeatureId: null,
  featureTypeOptions: [...DEFAULT_FEATURE_TYPE_OPTIONS],
  choiceGroups: [],
  selectedChoiceGroupId: null,
  choiceOptions: [],
  selectedChoiceOptionId: null,
  respecRuleOptions: [...DEFAULT_RESPEC_RULE_OPTIONS],
};

const ui = {
  classRows: document.getElementById("classRows"),
  classCount: document.getElementById("classCount"),
  classTableWrap: document.getElementById("classTableWrap"),
  listHint: document.getElementById("listHint"),
  searchInput: document.getElementById("searchInput"),
  newClassBtn: document.getElementById("newClassBtn"),
  formTitle: document.getElementById("formTitle"),
  selectedBadge: document.getElementById("selectedBadge"),
  classForm: document.getElementById("classForm"),
  saveBtn: document.getElementById("saveBtn"),
  deleteBtn: document.getElementById("deleteBtn"),
  resetBtn: document.getElementById("resetBtn"),
  rulesetId: document.getElementById("rulesetId"),
  name: document.getElementById("name"),
  description: document.getElementById("description"),
  hitDie: document.getElementById("hitDie"),
  startingHp: document.getElementById("startingHp"),
  keyStat1: document.getElementById("keyStat1"),
  keyStat2: document.getElementById("keyStat2"),
  saveAdvStat: document.getElementById("saveAdvStat"),
  saveDisadvStat: document.getElementById("saveDisadvStat"),
  armorProficiencies: document.getElementById("armorProficiencies"),
  weaponProficiencies: document.getElementById("weaponProficiencies"),
  startingGear: document.getElementById("startingGear"),
  addRulesetBtn: document.getElementById("addRulesetBtn"),
  rulesetDialog: document.getElementById("rulesetDialog"),
  rulesetForm: document.getElementById("rulesetForm"),
  rulesetName: document.getElementById("rulesetName"),
  rulesetVersion: document.getElementById("rulesetVersion"),
  rulesetSourceBook: document.getElementById("rulesetSourceBook"),
  rulesetSourcePageRef: document.getElementById("rulesetSourcePageRef"),
  cancelRulesetBtn: document.getElementById("cancelRulesetBtn"),
  subclassCount: document.getElementById("subclassCount"),
  subclassHint: document.getElementById("subclassHint"),
  subclassEditor: document.getElementById("subclassEditor"),
  subclassTableWrap: document.getElementById("subclassTableWrap"),
  subclassRows: document.getElementById("subclassRows"),
  subclassListHint: document.getElementById("subclassListHint"),
  subclassForm: document.getElementById("subclassForm"),
  subclassFormTitle: document.getElementById("subclassFormTitle"),
  subclassEditingBadge: document.getElementById("subclassEditingBadge"),
  subclassName: document.getElementById("subclassName"),
  subclassStoryBased: document.getElementById("subclassStoryBased"),
  subclassDescription: document.getElementById("subclassDescription"),
  subclassSaveBtn: document.getElementById("subclassSaveBtn"),
  subclassDeleteBtn: document.getElementById("subclassDeleteBtn"),
  subclassResetBtn: document.getElementById("subclassResetBtn"),
  progressionCount: document.getElementById("progressionCount"),
  progressionHint: document.getElementById("progressionHint"),
  progressionEditor: document.getElementById("progressionEditor"),
  progressionTableWrap: document.getElementById("progressionTableWrap"),
  progressionRows: document.getElementById("progressionRows"),
  progressionListHint: document.getElementById("progressionListHint"),
  progressionForm: document.getElementById("progressionForm"),
  progressionFormTitle: document.getElementById("progressionFormTitle"),
  progressionEditingBadge: document.getElementById("progressionEditingBadge"),
  progressionLevel: document.getElementById("progressionLevel"),
  progressionSubclass: document.getElementById("progressionSubclass"),
  progressionFeatureType: document.getElementById("progressionFeatureType"),
  progressionName: document.getElementById("progressionName"),
  progressionDisplayOrder: document.getElementById("progressionDisplayOrder"),
  progressionDescription: document.getElementById("progressionDescription"),
  progressionCombatUsageNotes: document.getElementById("progressionCombatUsageNotes"),
  progressionSaveBtn: document.getElementById("progressionSaveBtn"),
  progressionDeleteBtn: document.getElementById("progressionDeleteBtn"),
  progressionResetBtn: document.getElementById("progressionResetBtn"),
  choiceGroupCount: document.getElementById("choiceGroupCount"),
  choiceGroupHint: document.getElementById("choiceGroupHint"),
  choiceGroupEditor: document.getElementById("choiceGroupEditor"),
  choiceGroupTableWrap: document.getElementById("choiceGroupTableWrap"),
  choiceGroupRows: document.getElementById("choiceGroupRows"),
  choiceGroupListHint: document.getElementById("choiceGroupListHint"),
  choiceGroupForm: document.getElementById("choiceGroupForm"),
  choiceGroupFormTitle: document.getElementById("choiceGroupFormTitle"),
  choiceGroupEditingBadge: document.getElementById("choiceGroupEditingBadge"),
  choiceGroupName: document.getElementById("choiceGroupName"),
  choiceGroupSubclass: document.getElementById("choiceGroupSubclass"),
  choiceGroupMaxChoices: document.getElementById("choiceGroupMaxChoices"),
  choiceGroupRespecRule: document.getElementById("choiceGroupRespecRule"),
  choiceGroupDescription: document.getElementById("choiceGroupDescription"),
  choiceGroupSaveBtn: document.getElementById("choiceGroupSaveBtn"),
  choiceGroupDeleteBtn: document.getElementById("choiceGroupDeleteBtn"),
  choiceGroupResetBtn: document.getElementById("choiceGroupResetBtn"),
  choiceOptionCount: document.getElementById("choiceOptionCount"),
  choiceOptionHint: document.getElementById("choiceOptionHint"),
  choiceOptionEditor: document.getElementById("choiceOptionEditor"),
  choiceOptionTableWrap: document.getElementById("choiceOptionTableWrap"),
  choiceOptionRows: document.getElementById("choiceOptionRows"),
  choiceOptionListHint: document.getElementById("choiceOptionListHint"),
  choiceOptionForm: document.getElementById("choiceOptionForm"),
  choiceOptionFormTitle: document.getElementById("choiceOptionFormTitle"),
  choiceOptionEditingBadge: document.getElementById("choiceOptionEditingBadge"),
  choiceOptionName: document.getElementById("choiceOptionName"),
  choiceOptionDisplayOrder: document.getElementById("choiceOptionDisplayOrder"),
  choiceOptionDescription: document.getElementById("choiceOptionDescription"),
  choiceOptionCombatUsageNotes: document.getElementById("choiceOptionCombatUsageNotes"),
  choiceOptionPrereqJson: document.getElementById("choiceOptionPrereqJson"),
  choiceOptionEffectsJson: document.getElementById("choiceOptionEffectsJson"),
  choiceOptionSaveBtn: document.getElementById("choiceOptionSaveBtn"),
  choiceOptionDeleteBtn: document.getElementById("choiceOptionDeleteBtn"),
  choiceOptionResetBtn: document.getElementById("choiceOptionResetBtn"),
  toast: document.getElementById("toast"),
};

function showToast(message, type = "success") {
  ui.toast.textContent = message;
  ui.toast.classList.remove("hidden", "error");
  if (type === "error") {
    ui.toast.classList.add("error");
  }

  window.clearTimeout(showToast._timer);
  showToast._timer = window.setTimeout(() => {
    ui.toast.classList.add("hidden");
  }, 3500);
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};

  if (!response.ok) {
    const error = new Error(data.error || `Request failed (${response.status})`);
    error.details = data;
    throw error;
  }

  return data;
}

function titleCase(raw) {
  return raw
    .split("_")
    .map((piece) => piece.charAt(0).toUpperCase() + piece.slice(1))
    .join(" ");
}

function normalizeJsonTextForTextarea(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

function renderStatSelect(select, selectedValue = "") {
  select.innerHTML = "";
  for (const stat of STAT_OPTIONS) {
    const option = document.createElement("option");
    option.value = stat;
    option.textContent = stat;
    if (stat === selectedValue) {
      option.selected = true;
    }
    select.appendChild(option);
  }
}

function renderRulesetOptions(selectedId = null) {
  const prior = selectedId || Number(ui.rulesetId.value) || null;
  ui.rulesetId.innerHTML = "";

  if (state.rulesets.length === 0) {
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Create a ruleset first";
    ui.rulesetId.appendChild(placeholder);
    ui.rulesetId.disabled = true;
    ui.saveBtn.disabled = true;
    return;
  }

  ui.rulesetId.disabled = false;
  ui.saveBtn.disabled = false;

  for (const ruleset of state.rulesets) {
    const option = document.createElement("option");
    option.value = String(ruleset.id);
    option.textContent = `${ruleset.name} (${ruleset.version})`;
    if (prior === ruleset.id) {
      option.selected = true;
    }
    ui.rulesetId.appendChild(option);
  }
}

function renderLevelOptions(selectedValue = 1) {
  ui.progressionLevel.innerHTML = "";
  for (let level = 1; level <= 20; level += 1) {
    const option = document.createElement("option");
    option.value = String(level);
    option.textContent = `Level ${level}`;
    if (level === Number(selectedValue)) {
      option.selected = true;
    }
    ui.progressionLevel.appendChild(option);
  }
}

function renderFeatureTypeOptions(selectedValue = "auto") {
  const fallback = state.featureTypeOptions.includes(selectedValue)
    ? selectedValue
    : state.featureTypeOptions[0] || "auto";

  ui.progressionFeatureType.innerHTML = "";
  for (const type of state.featureTypeOptions) {
    const option = document.createElement("option");
    option.value = type;
    option.textContent = titleCase(type);
    if (type === fallback) {
      option.selected = true;
    }
    ui.progressionFeatureType.appendChild(option);
  }
}

function renderScopeOptions(select, selectedSubclassId = null) {
  const prior =
    selectedSubclassId ??
    (select.value ? Number(select.value) : null);

  select.innerHTML = "";

  const coreOption = document.createElement("option");
  coreOption.value = "";
  coreOption.textContent = "Core class (all subclasses)";
  coreOption.selected = prior === null;
  select.appendChild(coreOption);

  for (const subclass of state.subclasses) {
    const option = document.createElement("option");
    option.value = String(subclass.id);
    option.textContent = subclass.isStoryBased
      ? `${subclass.name} (story-based)`
      : subclass.name;
    if (prior === subclass.id) {
      option.selected = true;
    }
    select.appendChild(option);
  }
}

function renderRespecRuleOptions(selectedValue = "never") {
  const fallback = state.respecRuleOptions.includes(selectedValue)
    ? selectedValue
    : state.respecRuleOptions[0] || "never";

  ui.choiceGroupRespecRule.innerHTML = "";
  for (const rule of state.respecRuleOptions) {
    const option = document.createElement("option");
    option.value = rule;
    option.textContent = RESPEC_RULE_LABELS[rule] || titleCase(rule);
    if (rule === fallback) {
      option.selected = true;
    }
    ui.choiceGroupRespecRule.appendChild(option);
  }
}

function classRulesetLabel(cls) {
  return `${cls.ruleset.name} (${cls.ruleset.version})`;
}

function progressionScopeLabel(feature) {
  if (!feature.subclass) {
    return "Core class";
  }
  return feature.subclass.isStoryBased
    ? `${feature.subclass.name} (story-based)`
    : feature.subclass.name;
}

function choiceGroupScopeLabel(group) {
  if (!group.subclass) {
    return "Core class";
  }
  return group.subclass.isStoryBased
    ? `${group.subclass.name} (story-based)`
    : group.subclass.name;
}

function getFilteredClasses() {
  if (!state.search.trim()) {
    return state.classes;
  }

  const term = state.search.trim().toLowerCase();
  return state.classes.filter((cls) => {
    return (
      cls.name.toLowerCase().includes(term) ||
      cls.ruleset.name.toLowerCase().includes(term) ||
      cls.ruleset.version.toLowerCase().includes(term)
    );
  });
}

function renderClassTable() {
  const filtered = getFilteredClasses();
  ui.classRows.innerHTML = "";

  for (const cls of filtered) {
    const row = document.createElement("tr");
    row.className = "class-row";
    if (cls.id === state.selectedClassId) {
      row.classList.add("active");
    }

    row.innerHTML = `
      <td>${escapeHtml(cls.name)}</td>
      <td>${escapeHtml(classRulesetLabel(cls))}</td>
      <td>d${cls.hitDie}</td>
      <td>${cls.startingHp}</td>
    `;

    row.addEventListener("click", () => {
      void selectClass(cls.id);
    });

    ui.classRows.appendChild(row);
  }

  ui.classCount.textContent = `${filtered.length} record${filtered.length === 1 ? "" : "s"}`;
  const hasRows = filtered.length > 0;
  ui.classTableWrap.classList.toggle("hidden", !hasRows);
  ui.listHint.classList.toggle("hidden", hasRows);

  if (!hasRows && state.search.trim()) {
    ui.listHint.textContent = "No classes match your search.";
  } else if (!hasRows) {
    ui.listHint.textContent = "No classes yet. Add one with New Class.";
  }
}

function renderSubclassTable() {
  ui.subclassRows.innerHTML = "";
  const subclasses = state.subclasses;

  for (const subclass of subclasses) {
    const row = document.createElement("tr");
    row.className = "class-row";
    if (subclass.id === state.selectedSubclassId) {
      row.classList.add("active");
    }

    row.innerHTML = `
      <td>${escapeHtml(subclass.name)}</td>
      <td>${subclass.isStoryBased ? "Yes" : "No"}</td>
      <td>${escapeHtml(subclass.description || "")}</td>
    `;

    row.addEventListener("click", () => {
      selectSubclass(subclass.id);
    });

    ui.subclassRows.appendChild(row);
  }

  ui.subclassCount.textContent = `${subclasses.length} subclass${subclasses.length === 1 ? "" : "es"}`;
  const hasRows = subclasses.length > 0;
  ui.subclassTableWrap.classList.toggle("hidden", !hasRows);
  ui.subclassListHint.classList.toggle("hidden", hasRows);
}

function renderProgressionTable() {
  ui.progressionRows.innerHTML = "";
  const features = state.progressionFeatures;

  for (const feature of features) {
    const row = document.createElement("tr");
    row.className = "class-row progression-row";
    if (feature.id === state.selectedFeatureId) {
      row.classList.add("active");
    }

    row.innerHTML = `
      <td>${feature.level}</td>
      <td>${escapeHtml(feature.name)}</td>
      <td>${escapeHtml(progressionScopeLabel(feature))}</td>
      <td>${escapeHtml(titleCase(feature.featureType))}</td>
    `;

    row.addEventListener("click", () => {
      selectFeature(feature.id);
    });

    ui.progressionRows.appendChild(row);
  }

  ui.progressionCount.textContent = `${features.length} abilit${features.length === 1 ? "y" : "ies"}`;
  const hasRows = features.length > 0;
  ui.progressionTableWrap.classList.toggle("hidden", !hasRows);
  ui.progressionListHint.classList.toggle("hidden", hasRows);
}

function renderChoiceGroupTable() {
  ui.choiceGroupRows.innerHTML = "";
  const groups = state.choiceGroups;

  for (const group of groups) {
    const row = document.createElement("tr");
    row.className = "class-row";
    if (group.id === state.selectedChoiceGroupId) {
      row.classList.add("active");
    }

    row.innerHTML = `
      <td>${escapeHtml(group.name)}</td>
      <td>${escapeHtml(choiceGroupScopeLabel(group))}</td>
      <td>${group.maxChoices}</td>
      <td>${escapeHtml(RESPEC_RULE_LABELS[group.respecRule] || titleCase(group.respecRule))}</td>
    `;

    row.addEventListener("click", () => {
      void selectChoiceGroup(group.id);
    });

    ui.choiceGroupRows.appendChild(row);
  }

  ui.choiceGroupCount.textContent = `${groups.length} group${groups.length === 1 ? "" : "s"}`;
  const hasRows = groups.length > 0;
  ui.choiceGroupTableWrap.classList.toggle("hidden", !hasRows);
  ui.choiceGroupListHint.classList.toggle("hidden", hasRows);
}

function renderChoiceOptionTable() {
  ui.choiceOptionRows.innerHTML = "";
  const options = state.choiceOptions;

  for (const option of options) {
    const row = document.createElement("tr");
    row.className = "class-row";
    if (option.id === state.selectedChoiceOptionId) {
      row.classList.add("active");
    }

    row.innerHTML = `
      <td>${escapeHtml(option.name)}</td>
      <td>${option.displayOrder}</td>
    `;

    row.addEventListener("click", () => {
      selectChoiceOption(option.id);
    });

    ui.choiceOptionRows.appendChild(row);
  }

  ui.choiceOptionCount.textContent = `${options.length} option${options.length === 1 ? "" : "s"}`;
  const hasRows = options.length > 0;
  ui.choiceOptionTableWrap.classList.toggle("hidden", !hasRows);
  ui.choiceOptionListHint.classList.toggle("hidden", hasRows);
}

function multilineFromValue(value) {
  if (!value) {
    return "";
  }

  if (Array.isArray(value)) {
    return value.join("\n");
  }

  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }

  return String(value);
}

function normalizeLines(text) {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function parseStartingGearInput(text) {
  const trimmed = text.trim();
  if (!trimmed) {
    return [];
  }

  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      return JSON.parse(trimmed);
    } catch {
      return normalizeLines(trimmed);
    }
  }

  return normalizeLines(trimmed);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function selectedClass() {
  return state.classes.find((item) => item.id === state.selectedClassId) || null;
}

function selectedSubclass() {
  return state.subclasses.find((item) => item.id === state.selectedSubclassId) || null;
}

function selectedFeature() {
  return state.progressionFeatures.find((item) => item.id === state.selectedFeatureId) || null;
}

function selectedChoiceGroup() {
  return state.choiceGroups.find((item) => item.id === state.selectedChoiceGroupId) || null;
}

function selectedChoiceOption() {
  return state.choiceOptions.find((item) => item.id === state.selectedChoiceOptionId) || null;
}

function setEditingMode(isEditing) {
  ui.formTitle.textContent = isEditing ? "Edit Character Class" : "Create Character Class";
  ui.selectedBadge.classList.toggle("hidden", !isEditing);
  ui.deleteBtn.disabled = !isEditing;
  ui.saveBtn.textContent = isEditing ? "Save Changes" : "Save Class";
}

function setSubclassEditingMode(isEditing) {
  ui.subclassFormTitle.textContent = isEditing ? "Edit Subclass" : "Add Subclass";
  ui.subclassEditingBadge.classList.toggle("hidden", !isEditing);
  ui.subclassDeleteBtn.disabled = !isEditing;
  ui.subclassSaveBtn.textContent = isEditing ? "Save Subclass Changes" : "Save Subclass";
}

function setProgressionEditingMode(isEditing) {
  ui.progressionFormTitle.textContent = isEditing ? "Edit Ability" : "Add Ability";
  ui.progressionEditingBadge.classList.toggle("hidden", !isEditing);
  ui.progressionDeleteBtn.disabled = !isEditing;
  ui.progressionSaveBtn.textContent = isEditing ? "Save Ability Changes" : "Save Ability";
}

function setChoiceGroupEditingMode(isEditing) {
  ui.choiceGroupFormTitle.textContent = isEditing ? "Edit Option Group" : "Add Option Group";
  ui.choiceGroupEditingBadge.classList.toggle("hidden", !isEditing);
  ui.choiceGroupDeleteBtn.disabled = !isEditing;
  ui.choiceGroupSaveBtn.textContent = isEditing ? "Save Group Changes" : "Save Group";
}

function setChoiceOptionEditingMode(isEditing) {
  ui.choiceOptionFormTitle.textContent = isEditing ? "Edit Option" : "Add Option";
  ui.choiceOptionEditingBadge.classList.toggle("hidden", !isEditing);
  ui.choiceOptionDeleteBtn.disabled = !isEditing;
  ui.choiceOptionSaveBtn.textContent = isEditing ? "Save Option Changes" : "Save Option";
}

function setProgressionEnabled(isEnabled) {
  ui.progressionEditor.classList.toggle("hidden", !isEnabled);
  if (!isEnabled) {
    ui.progressionHint.textContent = "Save and select a class to define level-by-level abilities.";
  }
}

function setSubclassEnabled(isEnabled) {
  ui.subclassEditor.classList.toggle("hidden", !isEnabled);
  if (!isEnabled) {
    ui.subclassHint.textContent =
      "Save and select a class to define subclass options (including story-based subclasses).";
  }
}

function setChoiceGroupEnabled(isEnabled) {
  ui.choiceGroupEditor.classList.toggle("hidden", !isEnabled);
  if (!isEnabled) {
    ui.choiceGroupHint.textContent =
      "Save and select a class to define optional ability collections (for example, Savage Arsenal).";
  }
}

function setChoiceOptionEnabled(isEnabled) {
  ui.choiceOptionEditor.classList.toggle("hidden", !isEnabled);
  if (!isEnabled) {
    ui.choiceOptionHint.textContent = "Select an option group to add individual selectable abilities.";
  }
}

function clearProgressionState() {
  state.progressionFeatures = [];
  state.selectedFeatureId = null;
  renderProgressionTable();
  renderScopeOptions(ui.progressionSubclass, null);
  renderFeatureTypeOptions(state.featureTypeOptions[0] || "auto");
  renderLevelOptions(1);
  ui.progressionName.value = "";
  ui.progressionDisplayOrder.value = "0";
  ui.progressionDescription.value = "";
  setProgressionEditingMode(false);
}

function clearSubclassState() {
  state.subclasses = [];
  state.selectedSubclassId = null;
  renderSubclassTable();
  setSubclassEditingMode(false);
  ui.subclassName.value = "";
  ui.subclassStoryBased.checked = false;
  ui.subclassDescription.value = "";
}

function clearChoiceOptionState() {
  state.choiceOptions = [];
  state.selectedChoiceOptionId = null;
  renderChoiceOptionTable();
  setChoiceOptionEditingMode(false);
  ui.choiceOptionName.value = "";
  ui.choiceOptionDisplayOrder.value = "0";
  ui.choiceOptionDescription.value = "";
  ui.choiceOptionPrereqJson.value = "";
  ui.choiceOptionEffectsJson.value = "";
}

function clearChoiceGroupState() {
  state.choiceGroups = [];
  state.selectedChoiceGroupId = null;
  renderChoiceGroupTable();
  renderScopeOptions(ui.choiceGroupSubclass, null);
  renderRespecRuleOptions(state.respecRuleOptions[0] || "never");
  ui.choiceGroupName.value = "";
  ui.choiceGroupMaxChoices.value = "1";
  ui.choiceGroupDescription.value = "";
  setChoiceGroupEditingMode(false);
  clearChoiceOptionState();
}

function resetClassForm() {
  state.selectedClassId = null;
  setEditingMode(false);

  ui.classForm.reset();

  renderRulesetOptions();
  const firstRuleset = state.rulesets[0];
  if (firstRuleset) {
    ui.rulesetId.value = String(firstRuleset.id);
  }

  renderStatSelect(ui.keyStat1, "STR");
  renderStatSelect(ui.keyStat2, "DEX");
  renderStatSelect(ui.saveAdvStat, "STR");
  renderStatSelect(ui.saveDisadvStat, "INT");

  ui.hitDie.value = "8";
  ui.startingHp.value = "8";

  setSubclassEnabled(false);
  clearSubclassState();

  setProgressionEnabled(false);
  clearProgressionState();

  setChoiceGroupEnabled(false);
  clearChoiceGroupState();
  setChoiceOptionEnabled(false);

  renderClassTable();
}

function fillClassForm(cls) {
  state.selectedClassId = cls.id;
  setEditingMode(true);

  ui.rulesetId.value = String(cls.ruleset.id);
  ui.name.value = cls.name || "";
  ui.description.value = cls.description || "";
  ui.hitDie.value = String(cls.hitDie || "");
  ui.startingHp.value = String(cls.startingHp || "");

  renderStatSelect(ui.keyStat1, cls.keyStat1);
  renderStatSelect(ui.keyStat2, cls.keyStat2);
  renderStatSelect(ui.saveAdvStat, cls.saveAdvStat);
  renderStatSelect(ui.saveDisadvStat, cls.saveDisadvStat);

  ui.armorProficiencies.value = multilineFromValue(cls.armorProficiencies);
  ui.weaponProficiencies.value = multilineFromValue(cls.weaponProficiencies);
  ui.startingGear.value = multilineFromValue(cls.startingGear);

  renderClassTable();
}

function fillSubclassForm(subclass) {
  state.selectedSubclassId = subclass.id;
  setSubclassEditingMode(true);

  ui.subclassName.value = subclass.name || "";
  ui.subclassStoryBased.checked = Boolean(subclass.isStoryBased);
  ui.subclassDescription.value = subclass.description || "";

  renderSubclassTable();
}

function resetSubclassForm() {
  state.selectedSubclassId = null;
  setSubclassEditingMode(false);

  ui.subclassName.value = "";
  ui.subclassStoryBased.checked = false;
  ui.subclassDescription.value = "";

  renderSubclassTable();
}

function fillFeatureForm(feature) {
  state.selectedFeatureId = feature.id;
  setProgressionEditingMode(true);

  renderLevelOptions(feature.level);
  renderScopeOptions(ui.progressionSubclass, feature.subclass ? feature.subclass.id : null);
  renderFeatureTypeOptions(feature.featureType);
  ui.progressionName.value = feature.name || "";
  ui.progressionDisplayOrder.value = String(feature.displayOrder ?? 0);
  ui.progressionDescription.value = feature.description || "";
  ui.progressionCombatUsageNotes.value = feature.combatUsageNotes || "";

  renderProgressionTable();
}

function resetFeatureForm() {
  state.selectedFeatureId = null;
  setProgressionEditingMode(false);

  renderLevelOptions(1);
  renderScopeOptions(ui.progressionSubclass, null);
  renderFeatureTypeOptions(state.featureTypeOptions[0] || "auto");
  ui.progressionName.value = "";
  ui.progressionDisplayOrder.value = "0";
  ui.progressionDescription.value = "";
  ui.progressionCombatUsageNotes.value = "";

  renderProgressionTable();
}

function fillChoiceGroupForm(group) {
  state.selectedChoiceGroupId = group.id;
  setChoiceGroupEditingMode(true);

  ui.choiceGroupName.value = group.name || "";
  ui.choiceGroupMaxChoices.value = String(group.maxChoices ?? 1);
  ui.choiceGroupDescription.value = group.description || "";
  renderScopeOptions(ui.choiceGroupSubclass, group.subclass ? group.subclass.id : null);
  renderRespecRuleOptions(group.respecRule || (state.respecRuleOptions[0] || "never"));

  renderChoiceGroupTable();
}

function resetChoiceGroupForm() {
  state.selectedChoiceGroupId = null;
  setChoiceGroupEditingMode(false);

  renderScopeOptions(ui.choiceGroupSubclass, null);
  renderRespecRuleOptions(state.respecRuleOptions[0] || "never");
  ui.choiceGroupName.value = "";
  ui.choiceGroupMaxChoices.value = "1";
  ui.choiceGroupDescription.value = "";

  renderChoiceGroupTable();

  setChoiceOptionEnabled(false);
  clearChoiceOptionState();
}

function fillChoiceOptionForm(option) {
  state.selectedChoiceOptionId = option.id;
  setChoiceOptionEditingMode(true);

  ui.choiceOptionName.value = option.name || "";
  ui.choiceOptionDisplayOrder.value = String(option.displayOrder ?? 0);
  ui.choiceOptionDescription.value = option.description || "";
  ui.choiceOptionCombatUsageNotes.value = option.combatUsageNotes || "";
  ui.choiceOptionPrereqJson.value = normalizeJsonTextForTextarea(option.prereq);
  ui.choiceOptionEffectsJson.value = normalizeJsonTextForTextarea(option.effects);

  renderChoiceOptionTable();
}

function resetChoiceOptionForm() {
  state.selectedChoiceOptionId = null;
  setChoiceOptionEditingMode(false);

  ui.choiceOptionName.value = "";
  ui.choiceOptionDisplayOrder.value = "0";
  ui.choiceOptionDescription.value = "";
  ui.choiceOptionCombatUsageNotes.value = "";
  ui.choiceOptionPrereqJson.value = "";
  ui.choiceOptionEffectsJson.value = "";

  renderChoiceOptionTable();
}

async function selectClass(classId) {
  const cls = state.classes.find((item) => item.id === classId);
  if (!cls) {
    return;
  }

  fillClassForm(cls);
  await loadSubclassesForSelectedClass();
  await Promise.all([loadProgressionForSelectedClass(), loadChoiceGroupsForSelectedClass()]);
}

function selectSubclass(subclassId) {
  const subclass = state.subclasses.find((item) => item.id === subclassId);
  if (!subclass) {
    return;
  }
  fillSubclassForm(subclass);
}

function selectFeature(featureId) {
  const feature = state.progressionFeatures.find((item) => item.id === featureId);
  if (!feature) {
    return;
  }
  fillFeatureForm(feature);
}

async function selectChoiceGroup(groupId) {
  const group = state.choiceGroups.find((item) => item.id === groupId);
  if (!group) {
    return;
  }

  fillChoiceGroupForm(group);
  await loadChoiceOptionsForSelectedGroup();
}

function selectChoiceOption(optionId) {
  const option = state.choiceOptions.find((item) => item.id === optionId);
  if (!option) {
    return;
  }
  fillChoiceOptionForm(option);
}

function validateLocal(payload) {
  if (payload.keyStat1 === payload.keyStat2) {
    throw new Error("Primary and secondary key stats must be different.");
  }
  if (payload.saveAdvStat === payload.saveDisadvStat) {
    throw new Error("Save advantage and disadvantage stats must be different.");
  }
}

function collectPayloadFromForm() {
  const payload = {
    rulesetId: Number(ui.rulesetId.value),
    name: ui.name.value.trim(),
    description: ui.description.value.trim(),
    hitDie: Number(ui.hitDie.value),
    startingHp: Number(ui.startingHp.value),
    keyStat1: ui.keyStat1.value,
    keyStat2: ui.keyStat2.value,
    saveAdvStat: ui.saveAdvStat.value,
    saveDisadvStat: ui.saveDisadvStat.value,
    armorProficiencies: normalizeLines(ui.armorProficiencies.value),
    weaponProficiencies: normalizeLines(ui.weaponProficiencies.value),
    startingGear: parseStartingGearInput(ui.startingGear.value),
  };

  validateLocal(payload);
  return payload;
}

function collectSubclassPayloadFromForm() {
  const payload = {
    name: ui.subclassName.value.trim(),
    isStoryBased: ui.subclassStoryBased.checked,
    description: ui.subclassDescription.value.trim(),
  };

  if (!state.selectedClassId) {
    throw new Error("Select a class before editing subclasses.");
  }
  if (!payload.name) {
    throw new Error("Subclass name is required.");
  }

  return payload;
}

function collectProgressionPayloadFromForm() {
  const subclassValue = ui.progressionSubclass.value;
  const payload = {
    level: Number(ui.progressionLevel.value),
    subclassId: subclassValue ? Number(subclassValue) : null,
    name: ui.progressionName.value.trim(),
    featureType: ui.progressionFeatureType.value,
    displayOrder: Number(ui.progressionDisplayOrder.value),
    description: ui.progressionDescription.value.trim(),
    combatUsageNotes: ui.progressionCombatUsageNotes.value.trim(),
  };

  if (!state.selectedClassId) {
    throw new Error("Select a class before editing progression.");
  }
  if (!payload.name) {
    throw new Error("Ability name is required.");
  }
  if (!Number.isInteger(payload.level) || payload.level < 1 || payload.level > 20) {
    throw new Error("Level must be between 1 and 20.");
  }
  if (!Number.isInteger(payload.displayOrder) || payload.displayOrder < 0) {
    throw new Error("Order within level must be 0 or greater.");
  }

  return payload;
}

function collectChoiceGroupPayloadFromForm() {
  const subclassValue = ui.choiceGroupSubclass.value;
  const payload = {
    name: ui.choiceGroupName.value.trim(),
    subclassId: subclassValue ? Number(subclassValue) : null,
    maxChoices: Number(ui.choiceGroupMaxChoices.value),
    respecRule: ui.choiceGroupRespecRule.value,
    description: ui.choiceGroupDescription.value.trim(),
  };

  if (!state.selectedClassId) {
    throw new Error("Select a class before editing option groups.");
  }
  if (!payload.name) {
    throw new Error("Group name is required.");
  }
  if (!Number.isInteger(payload.maxChoices) || payload.maxChoices <= 0) {
    throw new Error("Max choices must be greater than 0.");
  }

  return payload;
}

function collectChoiceOptionPayloadFromForm() {
  const payload = {
    name: ui.choiceOptionName.value.trim(),
    displayOrder: Number(ui.choiceOptionDisplayOrder.value),
    description: ui.choiceOptionDescription.value.trim(),
    combatUsageNotes: ui.choiceOptionCombatUsageNotes.value.trim(),
    prereqJson: ui.choiceOptionPrereqJson.value.trim(),
    effectsJson: ui.choiceOptionEffectsJson.value.trim(),
  };

  if (!state.selectedChoiceGroupId) {
    throw new Error("Select an option group before editing options.");
  }
  if (!payload.name) {
    throw new Error("Option name is required.");
  }
  if (!Number.isInteger(payload.displayOrder) || payload.displayOrder < 0) {
    throw new Error("Display order must be 0 or greater.");
  }

  return payload;
}

function openRulesetDialog() {
  ui.rulesetForm.reset();
  ui.rulesetDialog.showModal();
}

async function loadRulesets() {
  const data = await api("/api/rulesets");
  state.rulesets = data.rulesets || [];
  renderRulesetOptions();
}

async function loadClasses() {
  const data = await api("/api/classes");
  state.classes = data.classes || [];
  renderClassTable();
}

async function loadSubclassesForSelectedClass(subclassIdToSelect = null) {
  if (!state.selectedClassId) {
    setSubclassEnabled(false);
    clearSubclassState();
    return;
  }

  const data = await api(`/api/classes/${state.selectedClassId}/subclasses`);
  state.subclasses = data.subclasses || [];

  setSubclassEnabled(true);
  ui.subclassHint.textContent = `Managing subclasses for ${data.className}.`;
  renderSubclassTable();

  const targetId = subclassIdToSelect || state.selectedSubclassId;
  if (targetId) {
    const found = state.subclasses.find((item) => item.id === targetId);
    if (found) {
      fillSubclassForm(found);
      return;
    }
  }

  resetSubclassForm();
}

async function loadProgressionForSelectedClass(featureIdToSelect = null) {
  if (!state.selectedClassId) {
    setProgressionEnabled(false);
    clearProgressionState();
    return;
  }

  const data = await api(`/api/classes/${state.selectedClassId}/progression`);
  state.progressionFeatures = data.features || [];
  state.subclasses = data.subclasses || [];
  if (Array.isArray(data.featureTypeOptions) && data.featureTypeOptions.length > 0) {
    state.featureTypeOptions = data.featureTypeOptions;
  } else {
    state.featureTypeOptions = [...DEFAULT_FEATURE_TYPE_OPTIONS];
  }

  setProgressionEnabled(true);
  ui.progressionHint.textContent = `Managing progression for ${data.className}.`;
  renderProgressionTable();

  const targetId = featureIdToSelect || state.selectedFeatureId;
  if (targetId) {
    const found = state.progressionFeatures.find((item) => item.id === targetId);
    if (found) {
      fillFeatureForm(found);
      return;
    }
  }

  resetFeatureForm();
}

async function loadChoiceGroupsForSelectedClass(groupIdToSelect = null, optionIdToSelect = null) {
  if (!state.selectedClassId) {
    setChoiceGroupEnabled(false);
    clearChoiceGroupState();
    setChoiceOptionEnabled(false);
    return;
  }

  const data = await api(`/api/classes/${state.selectedClassId}/choice-groups`);
  state.choiceGroups = data.groups || [];
  state.subclasses = data.subclasses || state.subclasses;
  if (Array.isArray(data.respecRuleOptions) && data.respecRuleOptions.length > 0) {
    state.respecRuleOptions = data.respecRuleOptions;
  } else {
    state.respecRuleOptions = [...DEFAULT_RESPEC_RULE_OPTIONS];
  }

  setChoiceGroupEnabled(true);
  ui.choiceGroupHint.textContent = `Managing option sets for ${data.className}.`;
  renderChoiceGroupTable();

  const targetGroupId = groupIdToSelect || state.selectedChoiceGroupId;
  if (targetGroupId) {
    const foundGroup = state.choiceGroups.find((item) => item.id === targetGroupId);
    if (foundGroup) {
      fillChoiceGroupForm(foundGroup);
      await loadChoiceOptionsForSelectedGroup(optionIdToSelect);
      return;
    }
  }

  resetChoiceGroupForm();
}

async function loadChoiceOptionsForSelectedGroup(optionIdToSelect = null) {
  if (!state.selectedChoiceGroupId) {
    setChoiceOptionEnabled(false);
    clearChoiceOptionState();
    return;
  }

  const data = await api(`/api/choice-groups/${state.selectedChoiceGroupId}/options`);
  state.choiceOptions = data.options || [];

  setChoiceOptionEnabled(true);
  ui.choiceOptionHint.textContent = `Managing options for ${data.group.name}.`;
  renderChoiceOptionTable();

  const targetOptionId = optionIdToSelect || state.selectedChoiceOptionId;
  if (targetOptionId) {
    const foundOption = state.choiceOptions.find((item) => item.id === targetOptionId);
    if (foundOption) {
      fillChoiceOptionForm(foundOption);
      return;
    }
  }

  resetChoiceOptionForm();
}

async function refreshDataAndRestoreSelection(classIdToSelect = null) {
  const priorSelected = classIdToSelect || state.selectedClassId;
  await Promise.all([loadRulesets(), loadClasses()]);

  if (priorSelected) {
    const found = state.classes.find((cls) => cls.id === priorSelected);
    if (found) {
      fillClassForm(found);
      await loadSubclassesForSelectedClass();
      await Promise.all([loadProgressionForSelectedClass(), loadChoiceGroupsForSelectedClass()]);
      return;
    }
  }

  resetClassForm();
}

async function handleSaveClass(event) {
  event.preventDefault();

  try {
    const payload = collectPayloadFromForm();
    let data;

    if (state.selectedClassId) {
      data = await api(`/api/classes/${state.selectedClassId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      showToast("Class updated.");
    } else {
      data = await api("/api/classes", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showToast("Class created.");
    }

    await refreshDataAndRestoreSelection(data.class.id);
  } catch (error) {
    showToast(error.message || "Could not save class", "error");
  }
}

async function handleDeleteClass() {
  const cls = selectedClass();
  if (!cls) {
    return;
  }

  const ok = window.confirm(`Delete ${cls.name}? This cannot be undone.`);
  if (!ok) {
    return;
  }

  try {
    await api(`/api/classes/${cls.id}`, { method: "DELETE" });
    showToast("Class deleted.");
    await refreshDataAndRestoreSelection(null);
  } catch (error) {
    const blockers = error.details?.blockers;
    if (blockers) {
      const message = `Delete blocked: ${blockers.subclasses} subclasses, ${blockers.classLevelFeatures} class features, ${blockers.featureChoiceGroups} feature groups still reference this class.`;
      showToast(message, "error");
    } else {
      showToast(error.message || "Delete failed", "error");
    }
  }
}

async function handleSaveSubclass(event) {
  event.preventDefault();

  try {
    const payload = collectSubclassPayloadFromForm();
    let data;

    if (state.selectedSubclassId) {
      data = await api(`/api/subclasses/${state.selectedSubclassId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      showToast("Subclass updated.");
    } else {
      data = await api(`/api/classes/${state.selectedClassId}/subclasses`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showToast("Subclass created.");
    }

    await loadSubclassesForSelectedClass(data.subclass.id);
    await Promise.all([loadProgressionForSelectedClass(), loadChoiceGroupsForSelectedClass()]);
  } catch (error) {
    showToast(error.message || "Could not save subclass", "error");
  }
}

async function handleDeleteSubclass() {
  const subclass = selectedSubclass();
  if (!subclass) {
    return;
  }

  const ok = window.confirm(`Delete subclass "${subclass.name}"? This cannot be undone.`);
  if (!ok) {
    return;
  }

  try {
    await api(`/api/subclasses/${subclass.id}`, { method: "DELETE" });
    showToast("Subclass deleted.");
    await loadSubclassesForSelectedClass();
    await Promise.all([loadProgressionForSelectedClass(), loadChoiceGroupsForSelectedClass()]);
  } catch (error) {
    const blockers = error.details?.blockers;
    if (blockers) {
      const message = `Delete blocked: ${blockers.classLevelFeatures} class features and ${blockers.featureChoiceGroups} option groups still reference this subclass.`;
      showToast(message, "error");
    } else {
      showToast(error.message || "Could not delete subclass", "error");
    }
  }
}

async function handleSaveProgression(event) {
  event.preventDefault();

  try {
    const payload = collectProgressionPayloadFromForm();
    let data;

    if (state.selectedFeatureId) {
      data = await api(`/api/progression/${state.selectedFeatureId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      showToast("Ability updated.");
    } else {
      data = await api(`/api/classes/${state.selectedClassId}/progression`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showToast("Ability added.");
    }

    await loadProgressionForSelectedClass(data.feature.id);
  } catch (error) {
    showToast(error.message || "Could not save ability", "error");
  }
}

async function handleDeleteProgression() {
  const feature = selectedFeature();
  if (!feature) {
    return;
  }

  const ok = window.confirm(`Delete ability "${feature.name}"? This cannot be undone.`);
  if (!ok) {
    return;
  }

  try {
    await api(`/api/progression/${feature.id}`, { method: "DELETE" });
    showToast("Ability deleted.");
    await loadProgressionForSelectedClass();
  } catch (error) {
    showToast(error.message || "Could not delete ability", "error");
  }
}

async function handleSaveChoiceGroup(event) {
  event.preventDefault();

  try {
    const payload = collectChoiceGroupPayloadFromForm();
    let data;

    if (state.selectedChoiceGroupId) {
      data = await api(`/api/choice-groups/${state.selectedChoiceGroupId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      showToast("Option group updated.");
    } else {
      data = await api(`/api/classes/${state.selectedClassId}/choice-groups`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showToast("Option group created.");
    }

    await loadChoiceGroupsForSelectedClass(data.group.id);
  } catch (error) {
    showToast(error.message || "Could not save option group", "error");
  }
}

async function handleDeleteChoiceGroup() {
  const group = selectedChoiceGroup();
  if (!group) {
    return;
  }

  const ok = window.confirm(`Delete option group "${group.name}" and all its options?`);
  if (!ok) {
    return;
  }

  try {
    await api(`/api/choice-groups/${group.id}`, { method: "DELETE" });
    showToast("Option group deleted.");
    await loadChoiceGroupsForSelectedClass();
  } catch (error) {
    showToast(error.message || "Could not delete option group", "error");
  }
}

async function handleSaveChoiceOption(event) {
  event.preventDefault();

  try {
    const payload = collectChoiceOptionPayloadFromForm();
    let data;

    if (state.selectedChoiceOptionId) {
      data = await api(`/api/choice-options/${state.selectedChoiceOptionId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      showToast("Option updated.");
    } else {
      data = await api(`/api/choice-groups/${state.selectedChoiceGroupId}/options`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showToast("Option created.");
    }

    await loadChoiceOptionsForSelectedGroup(data.option.id);
  } catch (error) {
    showToast(error.message || "Could not save option", "error");
  }
}

async function handleDeleteChoiceOption() {
  const option = selectedChoiceOption();
  if (!option) {
    return;
  }

  const ok = window.confirm(`Delete option "${option.name}"? This cannot be undone.`);
  if (!ok) {
    return;
  }

  try {
    await api(`/api/choice-options/${option.id}`, { method: "DELETE" });
    showToast("Option deleted.");
    await loadChoiceOptionsForSelectedGroup();
  } catch (error) {
    showToast(error.message || "Could not delete option", "error");
  }
}

async function handleCreateRuleset(event) {
  event.preventDefault();

  try {
    const payload = {
      name: ui.rulesetName.value.trim(),
      version: ui.rulesetVersion.value.trim(),
      sourceBook: ui.rulesetSourceBook.value.trim(),
      sourcePageRef: ui.rulesetSourcePageRef.value.trim(),
    };

    const data = await api("/api/rulesets", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    ui.rulesetDialog.close();
    showToast("Ruleset created.");
    await loadRulesets();
    ui.rulesetId.value = String(data.ruleset.id);
  } catch (error) {
    showToast(error.message || "Could not create ruleset", "error");
  }
}

function attachHandlers() {
  ui.classForm.addEventListener("submit", handleSaveClass);
  ui.deleteBtn.addEventListener("click", handleDeleteClass);
  ui.resetBtn.addEventListener("click", () => resetClassForm());
  ui.newClassBtn.addEventListener("click", () => resetClassForm());
  ui.addRulesetBtn.addEventListener("click", openRulesetDialog);
  ui.cancelRulesetBtn.addEventListener("click", () => ui.rulesetDialog.close());
  ui.rulesetForm.addEventListener("submit", handleCreateRuleset);

  ui.subclassForm.addEventListener("submit", handleSaveSubclass);
  ui.subclassDeleteBtn.addEventListener("click", handleDeleteSubclass);
  ui.subclassResetBtn.addEventListener("click", () => resetSubclassForm());

  ui.progressionForm.addEventListener("submit", handleSaveProgression);
  ui.progressionDeleteBtn.addEventListener("click", handleDeleteProgression);
  ui.progressionResetBtn.addEventListener("click", () => resetFeatureForm());

  ui.choiceGroupForm.addEventListener("submit", handleSaveChoiceGroup);
  ui.choiceGroupDeleteBtn.addEventListener("click", handleDeleteChoiceGroup);
  ui.choiceGroupResetBtn.addEventListener("click", () => resetChoiceGroupForm());

  ui.choiceOptionForm.addEventListener("submit", handleSaveChoiceOption);
  ui.choiceOptionDeleteBtn.addEventListener("click", handleDeleteChoiceOption);
  ui.choiceOptionResetBtn.addEventListener("click", () => resetChoiceOptionForm());

  ui.searchInput.addEventListener("input", (event) => {
    state.search = event.target.value || "";
    renderClassTable();
  });
}

async function init() {
  renderStatSelect(ui.keyStat1, "STR");
  renderStatSelect(ui.keyStat2, "DEX");
  renderStatSelect(ui.saveAdvStat, "STR");
  renderStatSelect(ui.saveDisadvStat, "INT");

  renderLevelOptions(1);
  renderFeatureTypeOptions(DEFAULT_FEATURE_TYPE_OPTIONS[0]);
  renderScopeOptions(ui.progressionSubclass, null);

  renderScopeOptions(ui.choiceGroupSubclass, null);
  renderRespecRuleOptions(DEFAULT_RESPEC_RULE_OPTIONS[0]);

  setSubclassEnabled(false);
  clearSubclassState();

  setProgressionEnabled(false);
  clearProgressionState();

  setChoiceGroupEnabled(false);
  clearChoiceGroupState();
  setChoiceOptionEnabled(false);

  attachHandlers();

  try {
    await refreshDataAndRestoreSelection();

    if (state.rulesets.length === 0) {
      showToast("Create a ruleset first, then add classes.", "error");
    }
  } catch (error) {
    showToast(error.message || "Failed to load initial data", "error");
  }
}

init();
