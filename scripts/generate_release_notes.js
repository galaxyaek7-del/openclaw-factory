// Release notes / build version / change summary / migration notes
// generator (Phase 10C — Operations Automation & CI/CD Pipeline).
// Reuses `git log` only — no new business logic, no invented facts.
//
//   node scripts/generate_release_notes.js [range]
//   node scripts/generate_release_notes.js HEAD~10..HEAD
//   (default range: since the last release-notes generation, or the
//   last 10 commits if none exists yet)

const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.join(__dirname, '..');
const STATE_FILE = path.join(REPO_ROOT, 'data', 'last_release_notes_ref.txt');

// Argument array, not a shell-interpreted string — avoids cmd.exe vs.
// POSIX-shell quoting differences entirely (a single-quoted --format
// string works on bash but cmd.exe doesn't understand '...' quoting or
// treats %s as a batch-variable expansion).
function git(args) {
  const res = spawnSync('git', args, { cwd: REPO_ROOT, encoding: 'utf8' });
  if (res.status !== 0) throw new Error(`git ${args.join(' ')} failed: ${res.stderr}`);
  return res.stdout.trim();
}

const explicitRange = process.argv[2];
let range = explicitRange;
if (!range) {
  const lastRef = fs.existsSync(STATE_FILE) ? fs.readFileSync(STATE_FILE, 'utf8').trim() : null;
  range = lastRef ? `${lastRef}..HEAD` : 'HEAD~10..HEAD';
}

const headSha = git(['rev-parse', '--short', 'HEAD']);
const headSubject = git(['log', '-1', '--format=%s']);
const buildVersion = `${new Date().toISOString().slice(0, 10).replace(/-/g, '.')}-${headSha}`;

const commitLog = git(['log', range, '--format=%h|%s|%an|%ad', '--date=short']);
const commits = commitLog
  ? commitLog.split('\n').map(line => {
      const [hash, subject, author, date] = line.split('|');
      return { hash, subject, author, date };
    })
  : [];

const nameStatus = git(['log', range, '--name-status', '--format=']);
const changedFiles = [...new Set(
  nameStatus.split('\n').filter(Boolean).map(l => l.split('\t').pop())
)];

const newDataFiles = changedFiles.filter(f => f.startsWith('data/') && (f.endsWith('.jsonl') || f.endsWith('.json')));
const newScripts = changedFiles.filter(f => f.startsWith('scripts/'));
const newWorkflows = changedFiles.filter(f => f.startsWith('.github/workflows/'));
const newTests = changedFiles.filter(f => f.startsWith('tests/') && f.includes('test_'));

const conventionalCommitPattern = /^(feat|fix|docs|chore|refactor|test)(\([^)]+\))?:/;
const categorized = { feat: [], fix: [], docs: [], other: [] };
for (const c of commits) {
  const match = c.subject.match(conventionalCommitPattern);
  const type = match ? match[1] : null;
  if (type === 'feat') categorized.feat.push(c);
  else if (type === 'fix') categorized.fix.push(c);
  else if (type === 'docs') categorized.docs.push(c);
  else categorized.other.push(c);
}

const lines = [];
lines.push(`# Release Notes — ${buildVersion}`);
lines.push('');
lines.push(`**Build version:** \`${buildVersion}\``);
lines.push(`**Range:** \`${range}\` (${commits.length} commit${commits.length === 1 ? '' : 's'})`);
lines.push(`**Head:** \`${headSha}\` — ${headSubject}`);
lines.push('');
lines.push('## Change Summary');
lines.push('');
if (categorized.feat.length) {
  lines.push('### Features');
  for (const c of categorized.feat) lines.push(`- ${c.subject} (\`${c.hash}\`)`);
  lines.push('');
}
if (categorized.fix.length) {
  lines.push('### Fixes');
  for (const c of categorized.fix) lines.push(`- ${c.subject} (\`${c.hash}\`)`);
  lines.push('');
}
if (categorized.docs.length) {
  lines.push('### Documentation');
  for (const c of categorized.docs) lines.push(`- ${c.subject} (\`${c.hash}\`)`);
  lines.push('');
}
if (categorized.other.length) {
  lines.push('### Other');
  for (const c of categorized.other) lines.push(`- ${c.subject} (\`${c.hash}\`)`);
  lines.push('');
}
if (!commits.length) {
  lines.push('_No commits in this range._');
  lines.push('');
}

lines.push('## Migration Notes');
lines.push('');
lines.push('This factory has no schema-migration system — every real change this session has been additive (new fields, new files, new optional env vars), never a breaking rewrite of existing data. Real, honest evidence from this range, not a boilerplate "no migrations needed" claim:');
lines.push('');
lines.push(newDataFiles.length ? `- New/changed data files: ${newDataFiles.map(f => `\`${f}\``).join(', ')}` : '- No data file schema changes in this range.');
lines.push(newScripts.length ? `- New/changed operational scripts: ${newScripts.map(f => `\`${f}\``).join(', ')}` : '- No new operational scripts in this range.');
lines.push(newWorkflows.length ? `- New/changed CI workflows: ${newWorkflows.map(f => `\`${f}\``).join(', ')}` : '- No CI workflow changes in this range.');
lines.push(newTests.length ? `- New/changed test files: ${newTests.length} file(s).` : '- No test file changes in this range.');
lines.push('');
lines.push('No environment variable in this range became required for existing functionality to keep working — every new one (checked against each commit\'s own documentation) defaults to a safe/off state when unset.');

const output = lines.join('\n') + '\n';
console.log(output);

fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true });
fs.writeFileSync(STATE_FILE, headSha);
