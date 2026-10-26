#!/usr/bin/env node
/**
 * design-system/verify-semantic-consumers.js — CONSUMER-SIDE semantic check.
 *
 * build.js's pairwise-distinct lint only validates brands/*.json (the SOURCE).
 * It cannot catch a skill that never reads the source at all. That is not a
 * hypothetical: a plan-styling skill passed the source lint clean while its own
 * :root still hardcoded --color-success == --color-warning == the same blue,
 * because the lint never looks at CONSUMERS.
 *
 * This script renders each consumer's actual CSS in a real headless browser and
 * reads back the COMPUTED value via getComputedStyle — resolving every var()
 * chain and color-mix() the same way a real render would. Source-level grep or
 * lint can never prove this; only a browser can.
 *
 * Usage:   node design-system/verify-semantic-consumers.js
 * Exits:   0 = all present targets pass, 1 = a collision was found or the
 *          browser could not be launched.
 *
 * Requires Playwright. It is NOT vendored here — install it wherever you run
 * this from:  npm i -D playwright && npx playwright install chromium
 */

const fs = require("fs");
const path = require("path");

// design-system/ and skills/ are siblings in BOTH the repo checkout and the
// installed {agency-root} tree, so a path relative to this file resolves in
// both without needing to know the agency root.
const SKILLS_DIR = path.join(__dirname, "..", "skills");

function loadChromium() {
  try {
    return require("playwright").chromium;
  } catch (e) {
    console.error(
      "✗ Playwright is not resolvable from here.\n" +
        "  Install it and re-run:  npm i -D playwright && npx playwright install chromium\n" +
        `  (resolution error: ${e.code || e.message})`
    );
    process.exit(1);
  }
}

function extractStyleBlock(htmlPath) {
  const html = fs.readFileSync(htmlPath, "utf8");
  const m = html.match(/<style>([\s\S]*?)<\/style>/);
  if (!m) throw new Error(`No <style> block found in ${htmlPath}`);
  return m[1];
}

// Each target names a CSS source plus the things that must be pairwise distinct
// once computed. `file` is what decides whether the target is present at all —
// a target whose file is missing is SKIPPED, not failed, so this script stays
// correct in an install that does not carry every optional skill.
//
// Adding a consumer: add an entry here. If the consumer embeds its CSS in an
// HTML <style> block rather than shipping a .css, set `inline: true` and the
// block is extracted for you.
const TARGETS = [
  {
    name: "html-plan-style/style.css",
    file: path.join(SKILLS_DIR, "html-plan-style", "style.css"),
    selectors: {
      "callout-success (color)": ".callout-success",
      "callout-warning (color)": ".callout-warning",
      "callout-danger (color)": ".callout-danger",
      "callout-info (color)": ".callout-info",
    },
    // Secondary check: hover/pressed state must differ from resting state.
    pairs: [["--color-secondary", "--color-secondary-dark"]],
  },
];

async function resolveVarPairs(page, varNames) {
  // Custom properties don't get "computed" in the color-mix()-resolved sense
  // via getPropertyValue() — it returns the specified token string. To get the
  // REAL computed pixel value (color-mix included), apply each var as a real
  // CSS property (background-color) on a throwaway element and read THAT
  // element's computed style — this is what actually renders.
  return page.evaluate((names) => {
    const out = {};
    for (const n of names) {
      const el = document.createElement("div");
      el.style.backgroundColor = `var(${n})`;
      document.body.appendChild(el);
      out[n] = getComputedStyle(el).backgroundColor;
      el.remove();
    }
    return out;
  }, varNames);
}

async function getComputedColor(page, selector) {
  return page.locator(selector).evaluate((el) => getComputedStyle(el).color);
}

async function main() {
  const chromium = loadChromium();
  const browser = await chromium.launch();
  let hadFailure = false;
  let checked = 0;

  for (const target of TARGETS) {
    if (!fs.existsSync(target.file)) {
      console.log(`\n=== ${target.name} ===\n  – SKIPPED (not present in this install)`);
      continue;
    }
    checked++;
    console.log(`\n=== ${target.name} ===`);
    const css = target.inline
      ? extractStyleBlock(target.file)
      : fs.readFileSync(target.file, "utf8");
    const html = `<!DOCTYPE html><html><head><style>${css}</style></head><body>
      <div class="callout callout-success"><strong>Success</strong><p>x</p></div>
      <div class="callout callout-warning"><strong>Warning</strong><p>x</p></div>
      <div class="callout callout-danger"><strong>Danger</strong><p>x</p></div>
      <div class="callout callout-info"><strong>Info</strong><p>x</p></div>
    </body></html>`;

    const page = await browser.newPage();
    await page.setContent(html, { waitUntil: "load" });

    const resolved = {};
    for (const [label, selector] of Object.entries(target.selectors || {})) {
      const color = await getComputedColor(page, selector);
      resolved[label] = color;
      console.log(`  ${label.padEnd(28)} ${selector.padEnd(20)} -> computed color: ${color}`);
    }

    const seen = new Map();
    for (const label of Object.keys(target.selectors || {})) {
      const v = resolved[label];
      if (seen.has(v)) {
        console.error(`  ✗ COLLISION: "${label}" and "${seen.get(v)}" both compute to ${v}`);
        hadFailure = true;
      } else {
        seen.set(v, label);
      }
    }
    if (seen.size && seen.size === Object.keys(target.selectors).length) {
      console.log(`  ✓ all ${seen.size} computed colors are pairwise distinct`);
    }

    for (const [a, b] of target.pairs || []) {
      const vals = await resolveVarPairs(page, [a, b]);
      const distinct = vals[a] !== vals[b];
      console.log(`  ${a} = ${vals[a]} | ${b} = ${vals[b]} -> ${distinct ? "✓ distinct" : "✗ COLLISION"}`);
      if (!distinct) hadFailure = true;
    }

    await page.close();
  }

  await browser.close();

  if (hadFailure) {
    console.error("\nCONSUMER-SIDE CHECK FAILED — see ✗ lines above.");
    process.exit(1);
  }
  if (checked === 0) {
    console.log("\nNo consumer targets present in this install — nothing to check.");
    return;
  }
  console.log(`\nCONSUMER-SIDE CHECK PASSED — ${checked} target(s) render pairwise-distinct semantic colors.`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
