/**
 * agency tier set lite|standard|full
 * agency tier get
 *
 * Reads and writes ~/.agency/config.json: { "tier": "lite|standard|full" }
 * Default tier: "standard".
 *
 * DEPRECATED (2026-07-14): "lite" is deprecated and scheduled for deletion next
 * release. It still functions this release but prints a warning on every use.
 * See docs/tiers.md for the sunset rationale.
 */

const { existsSync, readFileSync, writeFileSync, mkdirSync } = require('fs');
const path = require('path');
const os = require('os');

const CONFIG_DIR = path.join(os.homedir(), '.agency');
const CONFIG_PATH = path.join(CONFIG_DIR, 'config.json');
const VALID_TIERS = ['lite', 'standard', 'full'];

module.exports = async function tier({ args, AGENCY_ROOT, console }) {
  const [sub, value] = args;

  if (!sub || sub === 'get') {
    const cfg = readConfig();
    const current = cfg.tier || 'standard (default)';
    console.log(`Current tier: ${current}`);
    console.log('');
    console.log('Available tiers:');
    console.log('  lite     — DEPRECATED (removal next release). PD + Coord + Exec (3 layers).');
    console.log('             Coord = team-lead task-giver (decomposes L3, dispatches Exec, reviews ACK/NACK).');
    console.log('             Phase A QA gate. No Approach Gate, no 50% Check-In, no Phase B IntegrationTester.');
    console.log('             ~30-40% token footprint of standard. See docs/tiers.md for sunset rationale.');
    console.log('  standard — Default. Full quality gates: Phase B IntegrationTester, Approach Gate,');
    console.log('             Mandatory 50% Check-In, pd-structure.md contracts.');
    console.log('  full     — Alias for standard.');
    console.log('');
    console.log('Agent trio per tier:');
    console.log('  lite     → pd-coordinator-lite + coord-lite + task-executor-lite');
    console.log('  standard → pd-coordinator     + coord      + task-executor');
    console.log('');
    console.log('Change with: agency tier set <tier>');
    return;
  }

  if (sub === 'set') {
    if (!value) {
      console.error('Usage: agency tier set lite|standard|full');
      process.exit(1);
    }
    if (!VALID_TIERS.includes(value)) {
      console.error(`Invalid tier: "${value}". Valid values: lite, standard, full`);
      process.exit(1);
    }
    const cfg = readConfig();
    const prev = cfg.tier || 'standard (default)';
    cfg.tier = value;
    writeConfig(cfg);
    console.log(`✓ Tier updated: ${prev} → ${value}`);
    if (value === 'lite') {
      console.log('  ⚠ DEPRECATED: lite is scheduled for deletion next release. See docs/tiers.md.');
      console.log('  Agent trio: pd-coordinator-lite + coord-lite + task-executor-lite');
      console.log('  Coord = team-lead task-giver. Phase A QA. ~30-40% token footprint of standard.');
      console.log('  To move off lite now: agency tier set standard');
    } else {
      console.log('  Full quality gates active. Agent trio: pd-coordinator + coord + task-executor');
      console.log('  Approach Gate, Phase B IntegrationTester, 50% Check-In, pd-structure.md.');
      console.log('  Recommended for Max 5x / Max 20x plans.');
    }
    return;
  }

  console.error(`Unknown subcommand: ${sub}`);
  console.error('Usage: agency tier get | agency tier set lite|standard|full');
  process.exit(1);
};

/**
 * Returns the agent trio for the given tier.
 * Consumed by pd-resume, pd-spawn, and any skill router that selects agent names at spawn time.
 *
 * Default (no tier / falsy) resolves to standard as of the 2026-07-14 lite sunset.
 * 'lite' is deprecated but still resolves correctly this release — see docs/tiers.md.
 *
 * @param {string} tier - 'lite' | 'standard' | 'full'
 * @returns {{ pd: string, coord: string, executor: string }}
 */
function agentTrio(tier) {
  if (tier === 'lite') {
    return {
      pd: 'pd-coordinator-lite',
      coord: 'coord-lite',
      executor: 'task-executor-lite',
    };
  }
  // standard and full (and no tier set) use the full-quality trio
  return {
    pd: 'pd-coordinator',
    coord: 'coord',
    executor: 'task-executor',
  };
}

module.exports.agentTrio = agentTrio;

function readConfig() {
  if (!existsSync(CONFIG_PATH)) return {};
  try {
    return JSON.parse(readFileSync(CONFIG_PATH, 'utf8'));
  } catch {
    return {};
  }
}

function writeConfig(cfg) {
  if (!existsSync(CONFIG_DIR)) mkdirSync(CONFIG_DIR, { recursive: true });
  writeFileSync(CONFIG_PATH, JSON.stringify(cfg, null, 2) + '\n');
}
