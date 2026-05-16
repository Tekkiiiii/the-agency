const { existsSync, mkdirSync, writeFileSync, readdirSync } = require('fs');
const { join } = require('path');
const { execFileSync } = require('child_process');
const readline = require('readline');

/**
 * agency onboard — Guided introduction to The Agency
 *
 * Assumes `agency init` was already run. Does NOT install anything.
 * Walks a new user through the system, creates their first project
 * and agent, and shows them how to start working.
 *
 * Steps:
 *   1. Check prerequisites are met
 *   2. Verify init was already run (bail if not)
 *   3. Create first project
 *   4. Create first agent definition
 *   5. Smoke test
 *   6. What's next summary
 */

const REQUIRED_NODE = 18;
const HEADER = `
╔══════════════════════════════════════════════════════╗
║          The Agency — Welcome Tour                   ║
║    Get oriented and create your first project        ║
╚══════════════════════════════════════════════════════╝
`;

function prompt(rl, question) {
  return new Promise(resolve => rl.question(question, answer => resolve(answer.trim())));
}

function step(n, total, label) {
  process.stdout.write(`\nStep ${n}/${total}: ${label}\n`);
}

function ok(msg) {
  process.stdout.write(`  ✓ ${msg}\n`);
}

function warn(msg) {
  process.stdout.write(`  ⚠ ${msg}\n`);
}

function fail(msg) {
  process.stdout.write(`  ✗ ${msg}\n`);
}

function info(msg) {
  process.stdout.write(`    ${msg}\n`);
}

function hr() {
  process.stdout.write(`  ${'─'.repeat(50)}\n`);
}

// ─── prerequisite checks ───────────────────────────────────────────────────

function checkNodeVersion() {
  const major = parseInt(process.versions.node.split('.')[0], 10);
  if (major < REQUIRED_NODE) {
    return {
      ok: false,
      msg: `Node.js ${process.versions.node} found — need v${REQUIRED_NODE} or higher`,
      fix: `Download the latest LTS at https://nodejs.org`,
    };
  }
  return { ok: true, msg: `Node.js ${process.versions.node}` };
}

function checkClaudeCode() {
  try {
    const out = execFileSync('claude', ['--version'], { stdio: 'pipe' }).toString().trim();
    return { ok: true, msg: `Claude Code ${out}` };
  } catch {
    try {
      // Some installs use 'claude-code'
      execFileSync('claude-code', ['--version'], { stdio: 'pipe' });
      return { ok: true, msg: 'Claude Code (claude-code)' };
    } catch {
      return {
        ok: false,
        msg: 'Claude Code not found in PATH',
        fix: 'Install at https://docs.anthropic.com/claude/claude-code',
      };
    }
  }
}

function checkGit() {
  try {
    const out = execFileSync('git', ['--version'], { stdio: 'pipe' }).toString().trim();
    return { ok: true, msg: out };
  } catch {
    return {
      ok: false,
      msg: 'git not found in PATH',
      fix: 'Install git: https://git-scm.com/downloads',
    };
  }
}

// ─── helpers ───────────────────────────────────────────────────────────────

function isInitialized(agencyRoot) {
  return (
    existsSync(join(agencyRoot, 'projects')) &&
    existsSync(join(agencyRoot, 'skills'))
  );
}

function listProjects(agencyRoot) {
  const dir = join(agencyRoot, 'projects');
  if (!existsSync(dir)) return [];
  return readdirSync(dir).filter(p =>
    existsSync(join(dir, p, 'STATE.md'))
  );
}

function slugify(str) {
  return str
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40);
}

function createAgentFile(agencyRoot, projectSlug, agentName, agentRole) {
  const agentDir = join(agencyRoot, 'projects', projectSlug, 'agents');
  mkdirSync(agentDir, { recursive: true });
  const safeName = slugify(agentName);
  const filePath = join(agentDir, `${safeName}.md`);
  const today = new Date().toISOString().split('T')[0];

  const content = `# ${agentName}

**Role**: ${agentRole}
**Project**: ${projectSlug}
**Created**: ${today}

## Mission

${agentRole} for the ${projectSlug} project.

## Responsibilities

- [ ] Define primary responsibilities
- [ ] Set up working patterns
- [ ] Establish communication protocols

## Working With This Agent

\`\`\`
# Invoke via Claude Code
claude -p "${agentName} — [your task description]"
\`\`\`

## Memory

State lives in \`~/.agency/projects/${projectSlug}/\`

## Notes

Add agent-specific context here.
`;

  writeFileSync(filePath, content);
  return filePath;
}

function createProject(agencyRoot, slug, description) {
  const newFn = require('./new.js');
  return newFn({ args: [slug, description], AGENCY_ROOT: agencyRoot, console });
}


// ─── main ──────────────────────────────────────────────────────────────────

module.exports = async function onboard({ args, AGENCY_ROOT, console }) {
  const agencyRoot = AGENCY_ROOT;
  const TOTAL_STEPS = 6;
  let hasErrors = false;

  process.stdout.write(HEADER);

  // ── Step 1: Prerequisites ────────────────────────────────────────────────
  step(1, TOTAL_STEPS, 'Checking prerequisites');
  hr();

  const checks = [
    { name: 'Node.js', result: checkNodeVersion() },
    { name: 'Claude Code', result: checkClaudeCode() },
    { name: 'git', result: checkGit() },
  ];

  let blockers = [];
  for (const { name, result } of checks) {
    if (result.ok) {
      ok(`${name}: ${result.msg}`);
    } else {
      fail(`${name}: ${result.msg}`);
      if (result.fix) info(`Fix: ${result.fix}`);
      // Claude Code is a soft warning — git is essential, Node is essential
      if (name !== 'Claude Code') {
        hasErrors = true;
        blockers.push(name);
      } else {
        warn('Claude Code not detected — some features will be limited');
      }
    }
  }

  if (hasErrors) {
    process.stdout.write('\n  Required prerequisites are missing.\n');
    process.stdout.write('  Fix the issues above and re-run: agency onboard\n\n');
    process.exit(1);
  }

  // ── Step 2: Verify init was already run ──────────────────────────────────
  step(2, TOTAL_STEPS, 'Verifying installation');
  hr();

  if (!isInitialized(agencyRoot)) {
    fail('The Agency is not initialized yet.');
    info('Run `agency init` first to install skills, agents, and the task store.');
    info('Then re-run `agency onboard` to get the guided tour.');
    process.exit(1);
  }

  ok(`Initialized at ${agencyRoot}`);
  const projects = listProjects(agencyRoot);
  if (projects.length > 0) {
    ok(`${projects.length} existing project(s): ${projects.join(', ')}`);
  }

  // ── Step 3: Create first project ─────────────────────────────────────────
  step(3, TOTAL_STEPS, 'Create your first project');
  hr();

  const existingProjects = listProjects(agencyRoot);

  let projectSlug;
  let projectDescription;

  if (!process.stdin.isTTY) {
    // Non-interactive fallback: create a demo project
    projectSlug = 'my-first-project';
    projectDescription = 'My first Agency project';
    if (existingProjects.includes(projectSlug)) {
      ok(`Using existing project: ${projectSlug}`);
    } else {
      info(`Creating demo project: ${projectSlug}`);
      await createProject(agencyRoot, projectSlug, projectDescription);
    }
    await continueWithAgent(null, agencyRoot, projectSlug, TOTAL_STEPS, existingProjects.includes(projectSlug));
    return;
  } else {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

    try {
      if (existingProjects.length > 0) {
        process.stdout.write(`\n  You already have ${existingProjects.length} project(s):\n`);
        for (const p of existingProjects) info(p);
        process.stdout.write('\n');

        const useExisting = await prompt(rl, '  Set up another project? [y/N] ');
        if (!useExisting.toLowerCase().startsWith('y')) {
          projectSlug = existingProjects[0];
          ok(`Using existing project: ${projectSlug}`);
          rl.close();
          // Jump ahead — skip project creation
          await continueWithAgent(rl, agencyRoot, projectSlug, TOTAL_STEPS, true);
          return;
        }
      }

      process.stdout.write('\n');
      const rawName = await prompt(rl, '  Project name (e.g. "My SaaS App"): ');
      if (!rawName) {
        projectSlug = 'my-first-project';
        projectDescription = 'My first Agency project';
        info(`Using default: ${projectSlug}`);
      } else {
        projectSlug = slugify(rawName);
        info(`Slug: ${projectSlug}`);
        projectDescription = await prompt(rl, `  Short description: `);
        if (!projectDescription) projectDescription = rawName;
      }

      if (existingProjects.includes(projectSlug)) {
        ok(`Project "${projectSlug}" already exists — skipping creation`);
      } else {
        process.stdout.write('\n');
        await createProject(agencyRoot, projectSlug, projectDescription);
      }

      await continueWithAgent(rl, agencyRoot, projectSlug, TOTAL_STEPS, false);
    } finally {
      rl.close();
    }
  }
};

// ─── post-project flow ─────────────────────────────────────────────────────

async function continueWithAgent(rl, agencyRoot, projectSlug, TOTAL_STEPS, isExisting) {
  // ── Step 4: Create first agent ────────────────────────────────────────────
  step(4, TOTAL_STEPS, 'Create your first agent');
  hr();

  let agentName;
  let agentRole;

  if (!rl || !process.stdin.isTTY) {
    agentName = `${projectSlug}-pd`;
    agentRole = 'Project Director';
  } else {
    process.stdout.write('\n');
    process.stdout.write('  An agent is a specialized AI worker for your project.\n');
    process.stdout.write('  Common types: PD (Project Director), Specialist, Team Lead\n\n');

    const rawAgent = await prompt(rl, '  Agent name (e.g. "my-saas-pd", leave blank for default): ');
    agentName = rawAgent || `${projectSlug}-pd`;
    const rawRole = await prompt(rl, `  Agent role (e.g. "Project Director", leave blank for default): `);
    agentRole = rawRole || 'Project Director';
  }

  const agentPath = createAgentFile(agencyRoot, projectSlug, agentName, agentRole);
  ok(`Agent "${agentName}" created`);
  info(`File: ${agentPath}`);
  info(`Role: ${agentRole}`);

  // ── Step 5: Smoke test ────────────────────────────────────────────────────
  step(5, TOTAL_STEPS, 'Running smoke test');
  hr();

  let smokeOk = true;

  // Check project directory exists
  const projectPath = join(agencyRoot, 'projects', projectSlug);
  if (existsSync(projectPath)) {
    ok(`Project directory: ${projectPath}`);
  } else {
    fail('Project directory missing');
    smokeOk = false;
  }

  // Check STATE.md exists
  if (existsSync(join(projectPath, 'STATE.md'))) {
    ok('STATE.md present');
  } else {
    fail('STATE.md missing');
    smokeOk = false;
  }

  // Check agent file
  if (existsSync(join(projectPath, 'agents', `${slugify(agentName)}.md`))) {
    ok('Agent file present');
  } else {
    fail('Agent file missing');
    smokeOk = false;
  }

  if (smokeOk) {
    process.stdout.write('\n  All checks passed.\n');
  } else {
    process.stdout.write('\n  Some checks failed. Run: agency init\n');
  }

  // ── Step 6: What's next ────────────────────────────────────────────────────
  step(6, TOTAL_STEPS, "What's next");
  hr();

  const agentFile = join(projectPath, 'agents', `${slugify(agentName)}.md`);

  process.stdout.write('\n  Your Agency is ready. Here is how to start working:\n\n');
  process.stdout.write('  Quick start:\n\n');
  process.stdout.write(`    1. Open Claude Code in your project:\n`);
  process.stdout.write(`       cd ${projectPath}\n`);
  process.stdout.write(`       claude\n\n`);
  process.stdout.write(`    2. Your project state is at:\n`);
  process.stdout.write(`       ${join(projectPath, 'STATE.md')}\n\n`);
  process.stdout.write(`    3. Your agent definition is at:\n`);
  process.stdout.write(`       ${agentFile}\n\n`);
  process.stdout.write('  Useful commands:\n\n');
  process.stdout.write(`    agency status                     See all your projects\n`);
  process.stdout.write(`    agency tasks list ${projectSlug}  See tasks for this project\n`);
  process.stdout.write(`    agency tasks add ${projectSlug} "task name"  Add a task\n`);
  process.stdout.write(`    agency skill list                 See installed skills\n`);
  process.stdout.write(`    agency upgrade                    Pull latest updates\n\n`);
  process.stdout.write('  Documentation:\n\n');
  process.stdout.write('    docs/ARCHITECTURE.md              How the system is structured\n');
  process.stdout.write('    docs/SETUP.md                     Full setup reference\n');
  process.stdout.write('    agents/                           Agent catalog (100+ agents)\n\n');
  process.stdout.write('  Tips:\n\n');
  process.stdout.write(`    - Edit STATE.md to track current work and blockers\n`);
  process.stdout.write(`    - Use /pd-resume ${projectSlug} in Claude Code to resume a session\n`);
  process.stdout.write(`    - Use /save-state ${projectSlug} at the end of each session\n\n`);
  process.stdout.write('  Setup complete. Welcome to The Agency.\n\n');
}
