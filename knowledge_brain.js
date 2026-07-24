#!/usr/bin/env node
/**
 * Galaxy Forge Knowledge Brain — search helper (CONSTITUTION.md §18, Knowledge
 * Brain: "search the brain before building").
 *
 * Reads OpenClaw_Brain/ directly off disk — no index to keep in sync, no
 * database. Every call reflects the Brain's exact current state.
 *
 * Usage:
 *   node knowledge_brain.js search "pricing"     # keyword search across every .md file
 *   node knowledge_brain.js map                  # the folder map + entry counts (what GET /brain serves)
 */

const fs = require('fs');
const path = require('path');

const BRAIN_DIR = path.join(__dirname, 'OpenClaw_Brain');

function listMarkdownFiles(dir = BRAIN_DIR) {
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...listMarkdownFiles(full));
    } else if (entry.isFile() && entry.name.toLowerCase().endsWith('.md')) {
      out.push(full);
    }
  }
  return out;
}

// Real keyword search, not embeddings/AI — the Brain is small enough that a
// plain substring/line scan is honest and sufficient; no fabricated
// "semantic search" over a dataset this size would add real value.
function searchBrain(query, { limit = 20 } = {}) {
  const q = String(query || '').trim().toLowerCase();
  if (!q) return [];

  const results = [];
  for (const file of listMarkdownFiles()) {
    const rel = path.relative(BRAIN_DIR, file).replace(/\\/g, '/');
    const lines = fs.readFileSync(file, 'utf8').split('\n');
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].toLowerCase().includes(q)) {
        results.push({
          file: rel,
          line: i + 1,
          text: lines[i].trim(),
        });
        if (results.length >= limit) return results;
      }
    }
  }
  return results;
}

// The folder map GET /brain serves — real, computed from disk every call,
// not a hardcoded copy of MASTER_INDEX.md's table (which could drift).
function getBrainMap() {
  if (!fs.existsSync(BRAIN_DIR)) {
    return { exists: false, folders: [] };
  }
  const folders = fs.readdirSync(BRAIN_DIR, { withFileTypes: true })
    .filter(e => e.isDirectory())
    .map(e => e.name)
    .sort();

  const map = folders.map(name => {
    const dir = path.join(BRAIN_DIR, name);
    const files = listMarkdownFiles(dir);
    return { folder: name, fileCount: files.length, files: files.map(f => path.relative(BRAIN_DIR, f).replace(/\\/g, '/')) };
  });

  const masterIndexPath = path.join(BRAIN_DIR, 'MASTER_INDEX.md');
  return {
    exists: true,
    masterIndex: fs.existsSync(masterIndexPath) ? 'MASTER_INDEX.md' : null,
    totalMarkdownFiles: listMarkdownFiles().length,
    folders: map,
  };
}

function main() {
  const [, , cmd, ...rest] = process.argv;
  if (cmd === 'search') {
    const results = searchBrain(rest.join(' '));
    console.log(JSON.stringify(results, null, 2));
  } else if (cmd === 'map') {
    console.log(JSON.stringify(getBrainMap(), null, 2));
  } else {
    console.log('Usage: node knowledge_brain.js search "<query>"  |  node knowledge_brain.js map');
  }
}

if (require.main === module) {
  main();
}

module.exports = { searchBrain, getBrainMap, listMarkdownFiles, BRAIN_DIR };
