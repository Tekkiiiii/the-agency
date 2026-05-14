const { existsSync, mkdirSync, copyFileSync, readdirSync, statSync } = require('fs');
const { join } = require('path');

function shouldCopy(srcPath, destPath) {
  if (!existsSync(destPath)) return true;
  const srcStat = statSync(srcPath);
  const destStat = statSync(destPath);
  if (srcStat.mtimeMs > destStat.mtimeMs) return true;
  if (srcStat.size !== destStat.size) return true;
  return false;
}

function syncSkills(repoDir, destDir, console) {
  const srcDir = join(repoDir, 'skills');
  const result = { updated: [], preserved: [] };

  if (!existsSync(srcDir)) {
    console.log('  ⚠ No skills/ directory in repo — skipping');
    return result;
  }

  mkdirSync(destDir, { recursive: true });

  const skillFiles = readdirSync(srcDir).filter(
    f => f.endsWith('.md') && f !== 'INDEX.md' && f !== 'README.md'
  );

  for (const file of skillFiles) {
    const name = file.replace('.md', '');
    const srcPath = join(srcDir, file);
    const skillDir = join(destDir, name);
    const destPath = join(skillDir, 'SKILL.md');

    mkdirSync(skillDir, { recursive: true });

    if (shouldCopy(srcPath, destPath)) {
      copyFileSync(srcPath, destPath);
      result.updated.push(name);
    } else {
      result.preserved.push(name);
    }
  }

  const indexSrc = join(srcDir, 'INDEX.md');
  if (existsSync(indexSrc)) {
    copyFileSync(indexSrc, join(destDir, 'INDEX.md'));
  }

  return result;
}

function syncAgents(repoDir, destDir, console) {
  const srcDir = join(repoDir, 'agents');
  const result = { updated: 0, preserved: 0 };

  if (!existsSync(srcDir)) {
    console.log('  ⚠ No agents/ directory in repo — skipping');
    return result;
  }

  mkdirSync(destDir, { recursive: true });

  const walk = (src, dest) => {
    const entries = readdirSync(src, { withFileTypes: true });
    for (const entry of entries) {
      const srcPath = join(src, entry.name);
      const destPath = join(dest, entry.name);

      if (entry.isDirectory()) {
        mkdirSync(destPath, { recursive: true });
        walk(srcPath, destPath);
      } else if (entry.name.endsWith('.md')) {
        if (shouldCopy(srcPath, destPath)) {
          copyFileSync(srcPath, destPath);
          result.updated++;
        } else {
          result.preserved++;
        }
      }
    }
  };

  walk(srcDir, destDir);
  return result;
}

module.exports = { syncSkills, syncAgents };
