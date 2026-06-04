/**
 * agency tier set lite|standard|full
 * agency tier get
 *
 * Reads and writes ~/.agency/config.json: { "tier": "lite|standard|full" }
 * Default tier: "lite" (Pro-plan friendly)
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
    const current = cfg.tier || 'lite (default)';
    console.log(`Current tier: ${current}`);
    console.log('');
    console.log('Available tiers:');
    console.log('  lite     — Pro plan friendly. Simpler QA, no Approach Gate, no 50% Check-In.');
    console.log('             Lower token budget per session. Good for solo projects.');
    console.log('  standard — Full quality gates: Phase B IntegrationTester, Approach Gate,');
    console.log('             Mandatory 50% Check-In, pd-structure.md contracts.');
    console.log('             Best for Max 5x / Max 20x users.');
    console.log('  full     — Alias for standard.');
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
    const prev = cfg.tier || 'lite (default)';
    cfg.tier = value;
    writeConfig(cfg);
    console.log(`✓ Tier updated: ${prev} → ${value}`);
    if (value === 'lite') {
      console.log('  Pro-plan mode active. Simpler orchestration, lower token use.');
      console.log('  To use full quality gates: agency tier set standard');
    } else {
      console.log('  Full quality gates active (Approach Gate, Phase B QA, pd-structure.md).');
      console.log('  Recommended for Max 5x / Max 20x plans.');
    }
    return;
  }

  console.error(`Unknown subcommand: ${sub}`);
  console.error('Usage: agency tier get | agency tier set lite|standard|full');
  process.exit(1);
};

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
