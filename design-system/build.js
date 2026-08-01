#!/usr/bin/env node
/**
 * design-system/build.js — brands/*.json (source) -> brands/*.css (generated) + lint.
 *
 * JSON is the source of truth. CSS is generated output — never hand-edit brands/*.css.
 * Run: node {agency-root}/design-system/build.js
 *
 * What it does:
 *   1. Reads every brands/*.json, validates the required role schema
 *   2. Generates brands/{name}.css — a :root block of canonical --brand-* vars
 *   3. Lints overlays/*.css — must contain ZERO hex color literals (roles only)
 *
 * A separate, always-run verification step (documented in README.md) confirms the
 * generated brands/*.css matches what's committed in git:
 *   git diff --exit-code design-system/brands/*.css
 * That check is intentionally kept outside this script — this script has no
 * business shelling out to git, and the check is one command anyone running
 * the verification suite already runs.
 *
 * Canonical role schema — every brand.json's "roles" object must define exactly
 * these keys (values are keys into that same file's "colors" object):
 *   bg, surface, surface-alt, border, ink, text-muted, primary, primary-dark,
 *   primary-light, accent, accent-dark, secondary, secondary-dark, depth,
 *   text-on-primary
 *
 * Semantic schema — every brand.json also needs a top-level "semantic" object
 * with exactly these 4 roles, each an { accent, text } pair:
 *   success, warning, danger, info
 * These are FUNCTIONAL signals, not brand expression — they must stay mutually
 * distinguishable regardless of which brand is loaded, even when the brand has
 * no dedicated hue for one (see each brand's semantic.*.note for provenance).
 * NEVER use an "accent" value as foreground text — it is sized/contrasted for
 * borders/icons on a light tint, not for text-on-tint. Use "text" for that.
 *
 * Overlays (overlays/*.css) consume ONLY var(--brand-*) — never a literal hex.
 * That is the enforceable contract this script's lint step protects.
 */

const fs = require("fs");
const path = require("path");

const ROOT = __dirname;
const BRANDS_DIR = path.join(ROOT, "brands");
const OVERLAYS_DIR = path.join(ROOT, "overlays");

const REQUIRED_ROLES = [
  "bg", "surface", "surface-alt", "border", "ink", "text-muted",
  "primary", "primary-dark", "primary-light",
  "accent", "accent-dark",
  "secondary", "secondary-dark",
  "depth", "text-on-primary",
];

const REQUIRED_FONTS = ["display", "body", "mono"];
const REQUIRED_SEMANTIC_ROLES = ["success", "warning", "danger", "info"];

let hadError = false;

function fail(msg) {
  console.error(`✗ ${msg}`);
  hadError = true;
}

function ok(msg) {
  console.log(`✓ ${msg}`);
}

// ---------------------------------------------------------------------------
// Step 1 — load + validate brand JSONs
// ---------------------------------------------------------------------------

const brandFiles = fs
  .readdirSync(BRANDS_DIR)
  .filter((f) => f.endsWith(".json"))
  .sort();

if (brandFiles.length === 0) {
  fail(`No brands/*.json found in ${BRANDS_DIR}`);
  process.exit(1);
}

const brands = [];

for (const file of brandFiles) {
  const full = path.join(BRANDS_DIR, file);
  let data;
  try {
    data = JSON.parse(fs.readFileSync(full, "utf8"));
  } catch (e) {
    fail(`${file}: invalid JSON — ${e.message}`);
    continue;
  }

  if (!data.name || !data.colors || !data.roles || !data.fonts) {
    fail(`${file}: missing one of required top-level keys (name/colors/roles/fonts)`);
    continue;
  }

  const missingRoles = REQUIRED_ROLES.filter((r) => !(r in data.roles));
  if (missingRoles.length) {
    fail(`${file}: roles missing required keys: ${missingRoles.join(", ")}`);
  }

  const unresolvable = Object.entries(data.roles).filter(
    ([, colorKey]) => !(colorKey in data.colors)
  );
  if (unresolvable.length) {
    fail(
      `${file}: roles reference undefined colors: ${unresolvable
        .map(([role, key]) => `${role}->${key}`)
        .join(", ")}`
    );
  }

  const missingFonts = REQUIRED_FONTS.filter((f) => !(f in data.fonts));
  if (missingFonts.length) {
    fail(`${file}: fonts missing required keys: ${missingFonts.join(", ")}`);
  }

  // --- Semantic block validation ---
  if (!data.semantic) {
    fail(`${file}: missing top-level "semantic" block (success/warning/danger/info)`);
  } else {
    const missingSemantic = REQUIRED_SEMANTIC_ROLES.filter((r) => !(r in data.semantic));
    if (missingSemantic.length) {
      fail(`${file}: semantic missing required roles: ${missingSemantic.join(", ")}`);
    }
    for (const role of REQUIRED_SEMANTIC_ROLES) {
      const entry = data.semantic[role];
      if (!entry) continue;
      if (!entry.accent || !entry.text) {
        fail(`${file}: semantic.${role} missing "accent" and/or "text"`);
      }
    }

    // Pairwise-distinct: the 4 semantic accent values must never collide. A
    // collision means two functionally-different signals (e.g. success vs.
    // warning) render as the same color — the exact defect this lint exists for.
    const accentEntries = REQUIRED_SEMANTIC_ROLES
      .filter((r) => data.semantic[r] && data.semantic[r].accent)
      .map((r) => [r, data.semantic[r].accent]);
    const seenAccents = new Map();
    for (const [role, value] of accentEntries) {
      const key = value.toLowerCase();
      if (seenAccents.has(key)) {
        fail(
          `${file}: semantic.${role}.accent (${value}) collides with semantic.${seenAccents.get(
            key
          )}.accent — the four semantic accents must be pairwise distinct`
        );
      } else {
        seenAccents.set(key, role);
      }
    }
  }

  // --- secondary-dark != secondary ---
  // Both are required roles, so this always applies. A collision means the
  // hover/pressed state of "secondary" is visually indistinguishable from its
  // resting state.
  if (data.roles.secondary && data.roles["secondary-dark"]) {
    const secondaryVal = data.colors[data.roles.secondary];
    const secondaryDarkVal = data.colors[data.roles["secondary-dark"]];
    if (secondaryVal && secondaryDarkVal && secondaryVal.toLowerCase() === secondaryDarkVal.toLowerCase()) {
      fail(
        `${file}: roles.secondary-dark (${data.roles["secondary-dark"]} -> ${secondaryDarkVal}) resolves to the same value as roles.secondary (${data.roles.secondary} -> ${secondaryVal}) — hover/pressed state has no differentiation`
      );
    }
  }

  brands.push(data);
}

if (hadError) {
  console.error("\nAborting — fix brand JSON errors above before generating CSS.");
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Step 2 — generate brands/{name}.css from JSON
// ---------------------------------------------------------------------------

for (const brand of brands) {
  const lines = [];
  lines.push(`/* AUTO-GENERATED by design-system/build.js — DO NOT EDIT DIRECTLY.`);
  lines.push(` * Source: brands/${brand.name}.json — edit that file, then re-run build.js.`);
  lines.push(` * Brand: ${brand.label || brand.name}`);
  if (brand.source) lines.push(` * Provenance: ${brand.source}`);
  lines.push(` */`);
  lines.push(`:root {`);

  for (const role of REQUIRED_ROLES) {
    const colorKey = brand.roles[role];
    const value = brand.colors[colorKey];
    lines.push(`  --brand-${role}: ${value};  /* ${colorKey} */`);
  }

  lines.push(``);
  lines.push(`  --brand-font-display: ${brand.fonts.display};`);
  lines.push(`  --brand-font-body: ${brand.fonts.body};`);
  lines.push(`  --brand-font-mono: ${brand.fonts.mono};`);

  if (brand.semantic) {
    lines.push(``);
    for (const role of REQUIRED_SEMANTIC_ROLES) {
      const entry = brand.semantic[role];
      if (!entry) continue;
      lines.push(`  --brand-${role}-accent: ${entry.accent};`);
      lines.push(`  --brand-${role}-text: ${entry.text};`);
    }
  }

  lines.push(`}`);
  lines.push(``);

  const cssPath = path.join(BRANDS_DIR, `${brand.name}.css`);
  fs.writeFileSync(cssPath, lines.join("\n"));
  ok(`generated brands/${brand.name}.css (${REQUIRED_ROLES.length} roles + 3 fonts)`);
}

// ---------------------------------------------------------------------------
// Step 3 — lint overlays/*.css: zero hex literals allowed
// ---------------------------------------------------------------------------

const HEX_RE = /#[0-9a-fA-F]{3,8}\b/;

// Decimal rgb()/rgba() literals evade HEX_RE entirely. This blind spot produced
// three real bugs in the system this was extracted from: a deck skill's
// atmospheric glow (rgba(122,78,36,.28) wood-brown, rendered brown under every
// brand), a plan-style skill's old --shadow-glow, and a hand-typed
// rgba(0,86,167,..) inside a brand skill's own docs.
//
// A blanket ban would be wrong: achromatic values (r=g=b) are structural, not
// brand — a drop shadow is black at every brand, e.g. the legitimate
// rgba(0,0,0,0.10) in contrast-dark.css. Chromatic values encode a HUE, which
// only a brand can own, so those must go through var(--brand-*).
const RGB_RE = /\brgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/g;

function chromaticRgb(line) {
  const hits = [];
  for (const m of line.matchAll(RGB_RE)) {
    const [r, g, b] = [m[1], m[2], m[3]].map(Number);
    if (!(r === g && g === b)) hits.push(`rgb(${r},${g},${b})`);
  }
  return hits;
}

if (fs.existsSync(OVERLAYS_DIR)) {
  const overlayFiles = fs
    .readdirSync(OVERLAYS_DIR)
    .filter((f) => f.endsWith(".css"));

  let overlayViolations = [];
  for (const file of overlayFiles) {
    const full = path.join(OVERLAYS_DIR, file);
    const content = fs.readFileSync(full, "utf8");
    content.split("\n").forEach((line, i) => {
      // Strip inline comments before checking — a hex literal inside a /* */
      // comment is still not allowed to be the ONLY place a value lives, but
      // comments documenting "never use #C07030 here" reference a forbidden
      // value, not a live one.
      const stripped = line.replace(/\/\*.*?\*\//g, "");
      if (HEX_RE.test(stripped)) {
        overlayViolations.push(`overlays/${file}:${i + 1}: ${line.trim()}`);
      }
      const chromatic = chromaticRgb(stripped);
      if (chromatic.length) {
        overlayViolations.push(
          `overlays/${file}:${i + 1}: chromatic ${chromatic.join(", ")} — decimal rgb() carrying a hue; use var(--brand-*)`
        );
      }
    });
  }

  if (overlayViolations.length) {
    fail(`overlays contain hex literals (must reference var(--brand-*) only):`);
    overlayViolations.forEach((v) => console.error(`    ${v}`));
  } else {
    ok(`overlays/*.css lint clean — zero hex literals (${overlayFiles.length} files checked)`);
  }
} else {
  console.log("  (no overlays/ dir yet — skipping lint)");
}

// ---------------------------------------------------------------------------

if (hadError) {
  console.error("\nBUILD FAILED — see ✗ lines above.");
  process.exit(1);
}

console.log(`\nBuild OK — ${brands.length} brand(s): ${brands.map((b) => b.name).join(", ")}`);
console.log(`Next: git diff --exit-code design-system/brands/*.css  (confirm no drift, then commit)`);
