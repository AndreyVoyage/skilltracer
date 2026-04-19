#!/usr/bin/env node
/**
 * generate-github-links.js
 * Генератор raw-ссылок GitHub для репозитория skilltracer
 * ES Modules, Node 18+
 */

import { promises as fs, lstatSync, existsSync, createWriteStream } from 'fs';
import { spawn } from 'child_process';
import { resolve, relative, join, extname, basename } from 'path';
import https from 'https';
import { URL } from 'url';
import readline from 'readline';

// ==================== ANSI Colors ====================
const c = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m',
};

// ==================== Config ====================
const IGNORE_DIRS = new Set([
  '.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build',
  '.next', 'out', 'coverage', '.cache', '.turbo'
]);

const BINARY_EXTENSIONS = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp', '.bmp',
  '.woff', '.woff2', '.ttf', '.otf', '.eot',
  '.pyc', '.pyo', '.zip', '.tar', '.gz', '.rar', '.7z',
  '.mp3', '.mp4', '.avi', '.mov', '.webm', '.pdf', '.doc', '.docx',
  '.exe', '.dll', '.so', '.dylib', '.bin'
]);

const CONFIG_FILES = new Set([
  'readme.md', 'package.json', 'package-lock.json', 'requirements.txt',
  'docker-compose.yml', 'docker-compose.yaml', '.env.example', '.env',
  'tsconfig.json', 'vite.config.ts', 'vite.config.js', 'caddyfile',
  'tailwind.config.js', 'tailwind.config.ts', 'jest.config.js',
  'Makefile', 'LICENSE', 'CHANGELOG.md', 'CONTRIBUTING.md',
  '.gitignore', '.dockerignore', 'jest.setup.js'
]);

// ==================== Helpers ====================
function execPromise(cmd, args = [], options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      cwd: options.cwd || process.cwd(),
      shell: true,
      stdio: ['pipe', 'pipe', 'pipe']
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (d) => stdout += d.toString());
    child.stderr.on('data', (d) => stderr += d.toString());
    child.on('close', (code) => {
      if (code !== 0) {
        const err = new Error(stderr.trim() || `Command failed with code ${code}`);
        err.code = code;
        err.stderr = stderr;
        reject(err);
      } else {
        resolve(stdout.trim());
      }
    });
  });
}

function parseArgs(argv) {
  const flags = {};
  for (const arg of argv.slice(2)) {
    if (arg.startsWith('--')) {
      const [key, val] = arg.replace(/^--/, '').split('=');
      flags[key] = val === undefined ? true : val;
    }
  }
  return flags;
}

function drawProgressBar(current, total, width = 30) {
  const ratio = total === 0 ? 1 : Math.min(1, current / total);
  const filled = Math.round(width * ratio);
  const empty = width - filled;
  const bar = '█'.repeat(filled) + '░'.repeat(empty);
  const pct = Math.round(ratio * 100).toString().padStart(3, ' ');
  process.stdout.write(`\r${c.cyan}[${bar}]${c.reset} ${pct}% (${current}/${total})`);
}

function clearProgressBar() {
  process.stdout.write('\r' + ' '.repeat(60) + '\r');
}

// ==================== Core Logic ====================
export function generateRawUrl(owner, repo, branch, filepath) {
  const encodedPath = filepath.split('/').map(encodeURIComponent).join('/');
  return `https://raw.githubusercontent.com/${owner}/${repo}/${branch}/${encodedPath}`;
}

async function getGitRemote(cwd) {
  try {
    const out = await execPromise('git remote -v', [], { cwd });
    const lines = out.split('\n').filter(Boolean);
    const originLine = lines.find(l => l.startsWith('origin\t'));
    if (!originLine) {
      throw new Error('No remote origin found');
    }
    const match = originLine.match(/origin\t+(.+?)\s+\(fetch\)/);
    if (!match) throw new Error('Cannot parse remote origin');
    const url = match[1];
    // Parse GitHub owner/repo
    const m = url.match(/github\.com[:\/]([^\/]+)\/([^\/]+?)(?:\.git)?$/);
    if (!m) throw new Error('Remote origin is not a GitHub repository');
    return { owner: m[1], repo: m[2] };
  } catch (err) {
    if (err.stderr && err.stderr.includes('not a git repository')) {
      const e = new Error('This directory is not a Git repository. Run: git init');
      e.code = 'NOT_GIT_REPO';
      throw e;
    }
    throw err;
  }
}

async function getGitBranch(cwd) {
  try {
    const out = await execPromise('git rev-parse --abbrev-ref HEAD', [], { cwd });
    return out.trim();
  } catch (err) {
    return 'main';
  }
}

async function walkDir(dir, root, onFile, onDir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    const relPath = relative(root, fullPath).replace(/\\/g, '/');

    if (entry.isSymbolicLink()) {
      // Skip symlinks to avoid loops
      continue;
    }

    if (entry.isDirectory()) {
      if (IGNORE_DIRS.has(entry.name)) continue;
      if (onDir) onDir(relPath);
      await walkDir(fullPath, root, onFile, onDir);
    } else if (entry.isFile()) {
      await onFile(fullPath, relPath);
    }
  }
}

function categorizeFile(relPath, filenameLower) {
  const ext = extname(relPath).toLowerCase();

  if (BINARY_EXTENSIONS.has(ext) || ext === '.zip') {
    return 'binary';
  }

  if (CONFIG_FILES.has(filenameLower) || CONFIG_FILES.has(basename(relPath).toLowerCase())) {
    return 'config';
  }

  if (relPath.includes('/backend/') || relPath.includes('/api/') || relPath.includes('/bot/') || ext === '.py') {
    return 'backend';
  }

  if (relPath.includes('/frontend/') || relPath.includes('/src/') || ['.tsx', '.ts', '.jsx', '.js', '.css', '.scss'].includes(ext)) {
    return 'frontend';
  }

  if (ext === '.sql' || relPath.includes('/alembic/') || relPath.includes('/migrations/')) {
    return 'database';
  }

  return 'other';
}

async function getFileSize(fullPath) {
  try {
    const stat = await fs.stat(fullPath);
    return stat.size;
  } catch {
    return 0;
  }
}

function httpHead(url, timeout = 5000) {
  return new Promise((resolve) => {
    const req = https.request(new URL(url), { method: 'HEAD', timeout }, (res) => {
      resolve({ status: res.statusCode, headers: res.headers });
    });
    req.on('error', () => resolve({ status: 0 }));
    req.on('timeout', () => { req.destroy(); resolve({ status: 0 }); });
    req.end();
  });
}

async function retryWithBackoff(fn, retries = 3, delay = 1000) {
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (err) {
      if (i === retries - 1) throw err;
      await new Promise(r => setTimeout(r, delay * Math.pow(2, i)));
    }
  }
}

// ==================== Markdown Generation ====================
function generateMarkdown(repoInfo, categories, warnings) {
  const lines = [];
  const now = new Date().toISOString().split('T')[0];

  lines.push(`# Raw ссылки для ${repoInfo.repo}`);
  lines.push(`**Репозиторий:** https://github.com/${repoInfo.owner}/${repoInfo.repo}`);
  lines.push(`**Ветка:** ${repoInfo.branch}`);
  lines.push(`**Сгенерировано:** ${now}`);
  lines.push('');

  const emojiMap = {
    config: '📋 Config',
    backend: '⚙️ Backend',
    frontend: '🎨 Frontend',
    database: '🗄️ Database',
    binary: '🔴 Binary',
    other: '📁 Other'
  };

  for (const [cat, files] of Object.entries(categories)) {
    if (files.length === 0) continue;
    lines.push(`## ${emojiMap[cat] || cat}`);
    for (const f of files) {
      if (cat === 'binary') {
        lines.push(`- ${f.name} — [скачать](${f.url}) *(бинарный файл)*`);
      } else {
        lines.push(`- [${f.name}](${f.url})`);
      }
    }
    lines.push('');
  }

  if (warnings.length) {
    lines.push('## ⚠️ Предупреждения');
    for (const w of warnings) {
      lines.push(`- ${w}`);
    }
    lines.push('');
  }

  return lines.join('\n');
}

// ==================== Tests ====================
function assert(condition, message) {
  if (!condition) throw new Error(`Assertion failed: ${message}`);
}

async function runTests() {
  console.log(`\n${c.bold}${c.blue}🧪 Running tests...${c.reset}\n`);
  let passed = 0;
  let failed = 0;

  // Unit: URL generation
  try {
    const url = generateRawUrl('AndreyVoyage', 'skilltracer', 'main', 'test/file.py');
    assert(url === 'https://raw.githubusercontent.com/AndreyVoyage/skilltracer/main/test/file.py', 'URL format');
    passed++;
    console.log(`${c.green}✅${c.reset} Unit test: URL generation`);
  } catch (e) {
    failed++;
    console.log(`${c.red}❌${c.reset} Unit test: URL generation — ${e.message}`);
  }

  // Unit: URL encoding spaces
  try {
    const url = generateRawUrl('user', 'repo', 'main', 'file name.txt');
    assert(url.includes('%20'), 'URL space encoding');
    passed++;
    console.log(`${c.green}✅${c.reset} Unit test: URL space encoding`);
  } catch (e) {
    failed++;
    console.log(`${c.red}❌${c.reset} Unit test: URL space encoding — ${e.message}`);
  }

  // Unit: categorization
  try {
    assert(categorizeFile('backend/app/main.py', 'main.py') === 'backend', 'cat backend');
    assert(categorizeFile('frontend/src/App.tsx', 'app.tsx') === 'frontend', 'cat frontend');
    assert(categorizeFile('database.sql', 'database.sql') === 'database', 'cat database');
    assert(categorizeFile('logo.png', 'logo.png') === 'binary', 'cat binary');
    passed++;
    console.log(`${c.green}✅${c.reset} Unit test: categorization`);
  } catch (e) {
    failed++;
    console.log(`${c.red}❌${c.reset} Unit test: categorization — ${e.message}`);
  }

  // Integration: test ignore node_modules
  try {
    const testDir = resolve('.test-ignore');
    await fs.mkdir(testDir, { recursive: true });
    await fs.mkdir(join(testDir, 'node_modules'), { recursive: true });
    await fs.writeFile(join(testDir, 'node_modules', 'pkg.json'), '{}');
    await fs.writeFile(join(testDir, 'keep.txt'), 'ok');
    const found = [];
    await walkDir(testDir, testDir, (_fp, rp) => found.push(rp));
    assert(found.length === 1 && found[0] === 'keep.txt', 'node_modules ignored');
    await fs.rm(testDir, { recursive: true, force: true });
    passed++;
    console.log(`${c.green}✅${c.reset} Integration test: ignore node_modules`);
  } catch (e) {
    failed++;
    console.log(`${c.red}❌${c.reset} Integration test: ignore node_modules — ${e.message}`);
  }

  // Integration: HEAD request (public repo)
  try {
    const res = await retryWithBackoff(() => httpHead('https://raw.githubusercontent.com/AndreyVoyage/skilltracer/master/README.md'));
    assert(res.status === 200 || res.status === 301 || res.status === 302, `HEAD status ${res.status}`);
    passed++;
    console.log(`${c.green}✅${c.reset} Integration test: HTTP HEAD (status ${res.status})`);
  } catch (e) {
    failed++;
    console.log(`${c.red}❌${c.reset} Integration test: HTTP HEAD — ${e.message}`);
  }

  // Integration: symlink handling
  try {
    const testDir = resolve('.test-symlink');
    const target = join(testDir, 'real.txt');
    const link = join(testDir, 'link.txt');
    await fs.mkdir(testDir, { recursive: true });
    await fs.writeFile(target, 'data');
    try {
      await fs.symlink(target, link);
    } catch {
      // Windows may need admin rights for symlinks; skip gracefully
    }
    const found = [];
    await walkDir(testDir, testDir, (_fp, rp) => found.push(rp));
    // Should contain only real.txt
    assert(found.includes('real.txt'), 'symlink real file present');
    assert(!found.includes('link.txt'), 'symlink skipped');
    await fs.rm(testDir, { recursive: true, force: true });
    passed++;
    console.log(`${c.green}✅${c.reset} Integration test: symlinks skipped`);
  } catch (e) {
    failed++;
    console.log(`${c.red}❌${c.reset} Integration test: symlinks — ${e.message}`);
  }

  console.log(`\n${c.bold}Test results:${c.reset} ${c.green}${passed} passed${c.reset}, ${c.red}${failed} failed${c.reset}`);
  return { passed, failed };
}

// ==================== Main ====================
async function main() {
  const args = parseArgs(process.argv);
  const cwd = process.cwd();

  // Handle --test flag explicitly or run tests by default after generation
  if (args.test) {
    await runTests();
    process.exit(0);
  }

  console.log(`${c.bold}${c.cyan}
╔══════════════════════════════════════════╗
║  GitHub Raw Links Generator              ║
║  for skilltracer                         ║
╚══════════════════════════════════════════╝${c.reset}\n`);

  // Step 1: Verify git repo and get info
  let repoInfo;
  try {
    const { owner, repo } = await getGitRemote(cwd);
    const branch = args.branch || await getGitBranch(cwd);
    repoInfo = { owner, repo, branch };
    console.log(`${c.green}✅${c.reset} Repository: ${c.bold}${owner}/${repo}${c.reset}`);
    console.log(`${c.green}✅${c.reset} Branch: ${c.bold}${branch}${c.reset}\n`);
  } catch (err) {
    if (err.code === 'NOT_GIT_REPO') {
      console.error(`${c.red}❌ Ошибка:${c.reset} ${err.message}`);
      process.exit(1);
    }
    if (err.message.includes('No remote origin')) {
      console.error(`${c.red}❌ Ошибка:${c.reset} Нет remote origin. Добавь:`);
      console.error(`   git remote add origin https://github.com/AndreyVoyage/skilltracer.git`);
      process.exit(1);
    }
    console.error(`${c.red}❌ Ошибка:${c.reset} ${err.message}`);
    process.exit(1);
  }

  // Step 2: Collect files
  const categories = {
    config: [],
    backend: [],
    frontend: [],
    database: [],
    binary: [],
    other: []
  };
  const warnings = [];
  const allFiles = [];

  // First pass: count files for progress bar
  let totalFiles = 0;
  let processedFiles = 0;

  await walkDir(cwd, cwd, () => { totalFiles++; });

  // Reset and do actual work
  await walkDir(cwd, cwd, async (fullPath, relPath) => {
    processedFiles++;
    drawProgressBar(processedFiles, totalFiles);

    const filename = basename(relPath);
    const filenameLower = filename.toLowerCase();
    const category = categorizeFile(relPath, filenameLower);
    const size = await getFileSize(fullPath);
    const url = generateRawUrl(repoInfo.owner, repoInfo.repo, repoInfo.branch, relPath);

    if (category === 'binary') {
      if (size > 10 * 1024 * 1024) {
        warnings.push(`Файл \`${relPath}\` > 10MB — слишком большой для raw`);
      }
      if (!args['no-binary']) {
        categories.binary.push({ name: relPath, url, size });
      }
    } else {
      if (size > 100 * 1024) {
        warnings.push(`\`${relPath}\` > 100KB, может долго грузиться`);
      }
      categories[category].push({ name: relPath, url, size });
    }

    allFiles.push({ url, category, size });
  });

  clearProgressBar();

  // Step 3: Validation (--validate flag)
  let validated = 0;
  let broken = 0;
  if (args.validate) {
    console.log(`${c.yellow}🔍 Валидация URL...${c.reset}`);
    const nonBinary = allFiles.filter(f => f.category !== 'binary');
    for (let i = 0; i < nonBinary.length; i++) {
      const f = nonBinary[i];
      drawProgressBar(i + 1, nonBinary.length);
      const res = await retryWithBackoff(() => httpHead(f.url), 3, 800);
      if (res.status !== 200) {
        broken++;
        warnings.push(`404: ${f.url} (status ${res.status})`);
      } else {
        validated++;
      }
    }
    clearProgressBar();
  }

  // Step 4: Sort files
  for (const cat of Object.keys(categories)) {
    categories[cat].sort((a, b) => a.name.localeCompare(b.name));
  }

  // Step 5: Generate markdown
  const md = generateMarkdown(repoInfo, categories, warnings);
  const outputPath = resolve(args.output || 'GITHUB_LINKS.md');
  await fs.writeFile(outputPath, md, 'utf-8');

  // Step 6: Report
  const totalLinks = Object.values(categories).reduce((sum, arr) => sum + arr.length, 0);
  const binaryCount = categories.binary.length;

  console.log(`\n${c.bold}${c.green}✅ Готово!${c.reset}\n`);
  console.log(`   ${c.cyan}•${c.reset} ${totalLinks} ссылок сгенерировано`);
  if (args['no-binary']) {
    console.log(`   ${c.cyan}•${c.reset} ${binaryCount} бинарных файла пропущено (--no-binary)`);
  } else {
    console.log(`   ${c.cyan}•${c.reset} ${binaryCount} бинарных файла`);
  }
  if (args.validate) {
    if (broken === 0) {
      console.log(`   ${c.cyan}•${c.reset} Все URL валидны (HTTP 200)`);
    } else {
      console.log(`   ${c.yellow}•${c.reset} ${broken} недоступных URL`);
    }
  }
  if (warnings.length) {
    console.log(`   ${c.yellow}•${c.reset} ${warnings.length} предупреждений`);
    for (const w of warnings.slice(0, 5)) {
      console.log(`      ${c.yellow}⚠${c.reset}  ${w}`);
    }
    if (warnings.length > 5) {
      console.log(`      ${c.dim}...и ещё ${warnings.length - 5}${c.reset}`);
    }
  }
  console.log(`\n   ${c.dim}Файл сохранён:${c.reset} ${outputPath}\n`);

  // Step 7: Run tests
  const { passed, failed } = await runTests();
  if (failed > 0) process.exit(2);
}

main().catch(err => {
  console.error(`${c.red}❌ Fatal error:${c.reset}`, err.message);
  process.exit(1);
});
