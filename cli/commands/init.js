const { existsSync, mkdirSync, writeFileSync, symlinkSync, unlinkSync, realpathSync } = require('fs');
const path = require('path');
const os = require('os');
const { execFileSync } = require('child_process');
const { syncSkills, syncAgents } = require('./sync-assets.js');

// Compare two paths by real (symlink-resolved) location — see matching helper
// in upgrade.js for why bare path.resolve() is not sufficient here.
function samePath(a, b) {
  try {
    return realpathSync(a) === realpathSync(b);
  } catch (_) {
    return path.resolve(a) === path.resolve(b);
  }
}

module.exports = async function init({ args, AGENCY_ROOT, console }) {
  const agencyRoot = AGENCY_ROOT;
  const repoRoot = path.resolve(__dirname, '../..');

  console.log(`\nInitializing The Agency at ${agencyRoot}\n`);

  // 1. Root directory
  if (!existsSync(agencyRoot)) {
    mkdirSync(agencyRoot, { recursive: true });
    console.log('  ✓ Created root directory');
  } else {
    console.log('  ✓ Root directory exists');
  }

  // 2. Subdirectories
  for (const dir of ['projects', 'sessions', 'memory']) {
    const d = path.join(agencyRoot, dir);
    if (!existsSync(d)) {
      mkdirSync(d, { recursive: true });
      console.log(`  ✓ Created ${dir}/`);
    } else {
      console.log(`  ✓ ${dir}/ exists`);
    }
  }

  // 3. Skills
  const skillsDest = path.join(agencyRoot, 'skills');
  const skills = syncSkills(repoRoot, skillsDest, console);
  console.log(`  ✓ ${skills.updated.length} skills installed, ${skills.preserved.length} preserved`);

  // 4. Agents
  const agentsDest = path.join(agencyRoot, 'agents');
  const agents = syncAgents(repoRoot, agentsDest, console);
  console.log(`  ✓ ${agents.updated} agents installed, ${agents.preserved} preserved`);

  // 5. Core docs
  const coreSrc = path.join(repoRoot, 'core');
  const coreDest = path.join(agencyRoot, 'core');
  if (existsSync(coreSrc)) {
    mkdirSync(coreDest, { recursive: true });
    const { execFileSync } = require('child_process');
    try {
      execFileSync('cp', ['-r', coreSrc + '/.', coreDest + '/'], { stdio: 'pipe' });
      console.log('  ✓ Core docs installed');
    } catch (_) {
      console.log('  ⚠ Could not copy core docs');
    }
  }

  // 6. SQLite task store
  const dbPath = path.join(agencyRoot, 'task-store.db');
  if (!existsSync(dbPath)) {
    try {
      const Database = require('better-sqlite3');
      const db = new Database(dbPath);
      db.exec(require('./schema.js'));
      db.close();
      console.log('  ✓ Created task-store.db');
    } catch {
      writeFileSync(dbPath, '');
      console.log('  ⚠ better-sqlite3 not installed — task-store.db is a placeholder');
      console.log('       Run: npm install better-sqlite3');
    }
  } else {
    console.log('  ✓ task-store.db exists');
  }

  // 7. CLI link
  const cliSrc = path.resolve(__dirname, '../bin/agency.js');
  linkCli(cliSrc, console);

  // 7b. Write default tier to ~/.agency/config.json (only if not already set)
  const tierArg = args.find(a => a && a.startsWith('--tier='));
  const tierVal = tierArg ? tierArg.split('=')[1] : 'lite';
  const validTiers = ['lite', 'standard', 'full'];
  const resolvedTier = validTiers.includes(tierVal) ? tierVal : 'lite';

  const cfgDir = path.join(os.homedir(), '.agency');
  const cfgPath = path.join(cfgDir, 'config.json');
  if (!existsSync(cfgDir)) mkdirSync(cfgDir, { recursive: true });

  let existingCfg = {};
  if (existsSync(cfgPath)) {
    try { existingCfg = JSON.parse(require('fs').readFileSync(cfgPath, 'utf8')); } catch (_) {}
  }
  if (!existingCfg.tier) {
    existingCfg.tier = resolvedTier;
    writeFileSync(cfgPath, JSON.stringify(existingCfg, null, 2) + '\n');
    console.log(`  ✓ Default tier: ${resolvedTier}  (change with: agency tier set standard)`);
  } else {
    console.log(`  ✓ Tier: ${existingCfg.tier} (existing config preserved)`);
  }

  console.log(`\n✓ The Agency is ready — ${skillsDest}\n`);
  console.log('Next steps:');
  console.log('  agency initiate                           Install tool deps + register MCP servers');
  console.log('  agency onboard                            Guided introduction');
  console.log('  agency new <project-slug> "<description>"  Create your first project');
  console.log('  agency status                             Show all projects');
  console.log('  agency skill list                         View installed skills\n');
};

function linkCli(cliSrc, console) {
  if (os.platform() === 'win32') {
    const shimDir = path.join(os.homedir(), '.local', 'bin');
    mkdirSync(shimDir, { recursive: true });
    const shimPath = path.join(shimDir, 'agency.cmd');
    if (!existsSync(shimPath)) {
      writeFileSync(shimPath, `@node "${cliSrc}" %*`);
      console.log(`  ✓ CLI shim created → ${shimPath}`);
    } else {
      console.log('  ✓ CLI shim already exists');
    }
    return;
  }

  try { execFileSync('chmod', ['+x', cliSrc], { stdio: 'pipe' }); } catch (_) {}

  // Check if 'agency' is already on PATH — but verify it points to THIS repo.
  // If the symlink points elsewhere (stale clone, different checkout), re-link to cliSrc.
  try {
    const existingBin = execFileSync('which', ['agency'], { stdio: 'pipe' }).toString().trim();
    let existingTarget = '';
    try {
      existingTarget = execFileSync('readlink', [existingBin], { stdio: 'pipe' }).toString().trim();
    } catch (_) {
      // not a symlink — could be a shim or direct file
      existingTarget = existingBin;
    }
    if (samePath(existingTarget, cliSrc)) {
      console.log(`  ✓ CLI already linked → ${existingBin}`);
      return;
    }
    // Symlink exists but points to a different path — re-link to this repo
    console.log(`  ⚠ CLI symlink points to wrong location:`);
    console.log(`      was: ${existingTarget}`);
    console.log(`      now: ${cliSrc}`);
    try {
      execFileSync('ln', ['-sf', cliSrc, existingBin], { stdio: 'pipe' });
      console.log(`  ✓ CLI re-linked → ${existingBin}`);
      return;
    } catch (_) {
      console.log(`  ⚠ Could not re-link ${existingBin} (permission error?)`);
      console.log(`    Run manually: ln -sf "${cliSrc}" "${existingBin}"`);
      return;
    }
  } catch (_) {
    // 'which agency' failed — not on PATH yet, proceed to install
  }

  const targets = ['/usr/local/bin/agency', path.join(os.homedir(), '.local', 'bin', 'agency')];
  for (const target of targets) {
    try {
      mkdirSync(path.dirname(target), { recursive: true });
      try { unlinkSync(target); } catch (_) {}
      symlinkSync(cliSrc, target);
      console.log(`  ✓ CLI linked → ${target}`);
      if (target.includes('.local/bin') && !(process.env.PATH || '').includes('.local/bin')) {
        const shell = existsSync(path.join(os.homedir(), '.zshrc')) ? '.zshrc' : '.bashrc';
        console.log(`    Add to PATH: echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/${shell}`);
      }
      return;
    } catch (_) {
      continue;
    }
  }

  console.log('  ⚠ Could not create symlink — add this to your PATH:');
  console.log(`    ${cliSrc}`);
}
