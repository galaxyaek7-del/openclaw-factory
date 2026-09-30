const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '..');

// Security hardening: confine a caller-supplied filePath to the project
// root so QA file reads cannot escape the repository (e.g. /etc/passwd,
// Windows system files, or other users' files). Throws if the resolved
// path lands outside REPO_ROOT.
function confineToRepoRoot(p) {
  const resolved = path.resolve(REPO_ROOT, String(p));
  if (resolved !== REPO_ROOT && !resolved.startsWith(REPO_ROOT + path.sep)) {
    throw new Error('filePath escapes allowed directory');
  }
  return resolved;
}

// Reuse existing quality systems — do not duplicate
// For digital_product we delegate technical checks to inspectors.py logic via file existence,
// for other types we apply product-type-specific JS checks.

const VALID_PRODUCT_TYPES = new Set(['text', 'code', 'visual', 'digital_product', 'b2b', 'video']);
const VALID_CONTENT_TYPES = new Set(['text/plain', 'text/markdown', 'text/html', 'application/json', 'application/javascript', 'image/png', 'image/jpeg', 'video/mp4', 'application/pdf']);

function normalizeProductType(pt) {
  if (!pt || typeof pt !== 'string') return null;
  const n = pt.trim().toLowerCase();
  return VALID_PRODUCT_TYPES.has(n) ? n : null;
}

function normalizeContentType(ct) {
  if (!ct || typeof ct !== 'string') return 'text/plain';
  const n = ct.trim().toLowerCase().split(';')[0].trim();
  // allow short alias like "text", "code", "visual" -> map to default
  if (n === 'text') return 'text/plain';
  if (n === 'code' || n === 'javascript' || n === 'js') return 'application/javascript';
  if (n === 'visual' || n === 'image') return 'image/png';
  if (n === 'video') return 'video/mp4';
  if (n === 'digital_product' || n === 'pdf') return 'application/pdf';
  return VALID_CONTENT_TYPES.has(n) ? n : 'text/plain';
}

function isEmpty(content) {
  if (content == null) return true;
  if (typeof content !== 'string') {
    try { content = String(content); } catch (_) { return true; }
  }
  return content.trim().length === 0;
}

function getLength(content) {
  if (typeof content !== 'string') return 0;
  return content.trim().length;
}

function hasExcessiveRepetition(content) {
  if (!content || typeof content !== 'string') return false;
  const words = content.toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length < 20) return false;
  const freq = {};
  for (const w of words) freq[w] = (freq[w]||0)+1;
  const max = Math.max(...Object.values(freq));
  const ratio = max / words.length;
  // if any word repeats >30% of total words and more than 10 times, flag
  if (ratio > 0.3 && max > 10) return true;
  // also check repeated 3-gram
  const trigrams = {};
  for (let i=0;i<words.length-2;i++) {
    const tri = words.slice(i,i+3).join(' ');
    trigrams[tri] = (trigrams[tri]||0)+1;
    if (trigrams[tri] > 8) return true;
  }
  return false;
}

function hasTodoMarkers(content) {
  if (!content || typeof content !== 'string') return false;
  const markers = ['TODO', 'FIXME', 'undefined', 'null'];
  // For text, TODO is not acceptable; for code, undefined/null may be acceptable in some contexts but we flag if present as suspicious
  // We check case-sensitive for TODO/FIXME, case-insensitive for undefined/null as standalone?
  if (content.includes('TODO') || content.includes('FIXME')) return true;
  // For code, check for literal 'undefined' or 'null' as standalone suspicious if product_type code/digital_product/B2B
  // We'll let caller decide per product_type whether this is critical
  return false;
}

function hasUndefinedNullForCode(content) {
  if (!content || typeof content !== 'string') return false;
  // Check for unresolved placeholders
  return /\bundefined\b/.test(content) || /\bnull\b/.test(content) && content.includes('TODO');
}

function checkStructure(content, productType) {
  if (!content || typeof content !== 'string') return { passed: false, evidence: 'empty content' };
  switch(productType) {
    case 'text': {
      // Text should have at least 2 paragraphs or headings
      const paragraphs = content.split(/\n\s*\n/).filter(p => p.trim().length > 10);
      const hasHeadings = /^#{1,6}\s/m.test(content) || /^[A-Z][^\n]{0,60}\n[-=]{2,}/m.test(content);
      if (paragraphs.length >= 2 || hasHeadings) return { passed: true, evidence: `paragraphs:${paragraphs.length} headings:${hasHeadings}` };
      return { passed: false, evidence: `only ${paragraphs.length} paragraph(s), no headings` };
    }
    case 'code': {
      // Code should have at least one function/class and balanced braces
      const hasFunction = /(function\s+\w+|const\s+\w+\s*=\s*\(|class\s+\w+|def\s+\w+|=>)/.test(content);
      const opens = (content.match(/\{/g)||[]).length;
      const closes = (content.match(/\}/g)||[]).length;
      const balanced = Math.abs(opens - closes) <= 2;
      if (hasFunction && balanced) return { passed: true, evidence: `hasFunction:${hasFunction} braces:${opens}/${closes}` };
      return { passed: false, evidence: `hasFunction:${hasFunction} braces:${opens}/${closes} not balanced` };
    }
    case 'visual': {
      // Visual is file-based; structure check via file existence done elsewhere
      return { passed: true, evidence: 'visual structure checked via file' };
    }
    case 'digital_product': {
      // Should have title, sections, and not just placeholder
      const hasTitle = /#\s+\S+/.test(content) || content.includes('Title:') || content.length > 100;
      const sections = content.split(/\n#{1,3}\s/).length;
      if (hasTitle && sections >= 2) return { passed: true, evidence: `hasTitle:${hasTitle} sections:${sections}` };
      return { passed: false, evidence: `hasTitle:${hasTitle} sections:${sections}` };
    }
    case 'b2b': {
      // B2B should have value prop, audience, pricing
      const hasValue = /value/i.test(content) || /benefit/i.test(content) || /solution/i.test(content);
      const hasAudience = /audience|target|for\s+\w+\s+who/i.test(content);
      const hasPricing = /\$\s*\d+|price|pricing|commission/i.test(content);
      if (hasValue && hasAudience) return { passed: true, evidence: `value:${hasValue} audience:${hasAudience} pricing:${hasPricing}` };
      return { passed: false, evidence: `value:${hasValue} audience:${hasAudience} pricing:${hasPricing} missing` };
    }
    case 'video': {
      return { passed: false, evidence: 'video not supported yet' };
    }
    default:
      return { passed: false, evidence: 'unknown product type' };
  }
}

function getRequiredElements(productType) {
  switch(productType) {
    case 'text': return ['title', 'body'];
    case 'code': return ['code', 'exports'];
    case 'visual': return ['image_file', 'dimensions'];
    case 'digital_product': return ['title', 'cover', 'interior', 'price'];
    case 'b2b': return ['value_proposition', 'audience', 'pricing'];
    case 'video': return ['video_file', 'duration'];
    default: return [];
  }
}

function checkMissingElements(content, productType, metadata) {
  const required = getRequiredElements(productType);
  const missing = [];
  const meta = metadata || {};
  const lowerContent = (content || '').toLowerCase();
  for (const el of required) {
    // If metadata provides it, consider present
    if (meta[el] != null && String(meta[el]).trim() !== '') continue;
    // Otherwise check content as fallback
    let present = false;
    switch (el) {
      case 'title':
        present = /#\s+\S+/.test(content) || content.includes('Title') || content.includes('title');
        break;
      case 'body':
        present = getLength(content) >= 20;
        break;
      case 'code':
        present = /(function|class|const|let|import|export)/.test(content);
        break;
      case 'exports':
        present = /module\.exports|export\s/.test(content);
        break;
      case 'image_file':
        present = lowerContent.includes('image') || lowerContent.includes('.png') || lowerContent.includes('.jpg');
        break;
      case 'dimensions':
        present = lowerContent.includes('dimension') || lowerContent.includes('1600') || lowerContent.includes('size');
        break;
      case 'cover':
        present = lowerContent.includes('cover');
        break;
      case 'interior':
        present = lowerContent.includes('interior') || lowerContent.includes('pages');
        break;
      case 'price':
      case 'pricing':
        present = lowerContent.includes('price') || lowerContent.includes('pricing') || /\$\s*\d+/.test(content);
        break;
      case 'value_proposition':
        present = lowerContent.includes('value') || lowerContent.includes('proposition') || lowerContent.includes('solution') || lowerContent.includes('benefit');
        break;
      case 'audience':
        present = lowerContent.includes('audience') || lowerContent.includes('target') || lowerContent.includes('for ') ;
        break;
      case 'video_file':
        present = lowerContent.includes('video') || lowerContent.includes('.mp4');
        break;
      case 'duration':
        present = lowerContent.includes('duration') || lowerContent.includes('minutes') || lowerContent.includes('seconds');
        break;
      default:
        // For unknown required, check if content mentions it
        present = lowerContent.includes(el.toLowerCase());
        break;
    }
    if (!present) missing.push(el);
  }
  return missing;
}

// Product-type-specific min lengths (not arbitrary 100 deduction)
const MIN_LENGTHS = {
  text: 100,
  code: 30,
  visual: 0, // file-based, not string length
  digital_product: 500,
  b2b: 200,
  video: 0,
};

function evaluate({ content, productType, contentType, filePath, metadata, classification } = {}) {
  // Normalize inputs — fix contentType handling
  const ptRaw = productType;
  const pt = normalizeProductType(productType);
  const ct = normalizeContentType(contentType);

  const issues = [];
  const warnings = [];
  const strengths = [];
  const criteria = [];
  const evidence = {};

  let score = 0;
  let totalWeight = 0;
  let passed = false;
  let verdict = 'QA_REVIEW_REQUIRED';
  let finalClassification = classification || 'UNKNOWN';

  // Handle unsupported product type
  if (!pt) {
    const ev = `unsupported product_type: ${String(ptRaw)}`;
    criteria.push({ name: 'product_type_valid', passed: false, weight: 10, evidence: ev });
    issues.push(`Unsupported product_type: ${String(ptRaw)}`);
    evidence.product_type = ev;
    return {
      score: 0,
      passed: false,
      verdict: 'QA_REVIEW_REQUIRED',
      issues,
      warnings,
      strengths,
      criteria,
      product_type: String(ptRaw || 'unknown'),
      contentType: ct,
      evidence,
      classification: 'UNKNOWN',
    };
  }

  // Video not yet supported — honest UNKNOWN
  if (pt === 'video') {
    criteria.push({ name: 'video_supported', passed: false, weight: 10, evidence: 'video family not registered (5 families: kdp_books, professional_templates, digital_toolkits, knowledge_bases, automation_systems)' });
    issues.push('Video not supported yet — no video adapter');
    evidence.video = 'BLOCKED — NO FABRICATION';
    return {
      score: 0,
      passed: false,
      verdict: 'QA_REVIEW_REQUIRED',
      issues,
      warnings,
      strengths,
      criteria,
      product_type: pt,
      contentType: ct,
      evidence,
      classification: 'UNKNOWN',
    };
  }

  // If filePath provided, read file (for visual/pdf) — handle correctly
  let fileContent = content;
  let fileInfo = null;
  if (filePath) {
    // Security hardening: confine the caller-supplied path to the repo root
    // before any filesystem access. On escape, skip the read (no disclosure).
    let safePath = null;
    try {
      safePath = confineToRepoRoot(filePath);
    } catch (e) {
      fileInfo = { exists: false, error: 'path not allowed' };
      evidence.file = 'path not allowed: outside project root';
    }
    if (safePath) {
      try {
        if (fs.existsSync(safePath)) {
          const stat = fs.statSync(safePath);
          fileInfo = { exists: true, size: stat.size, ext: path.extname(safePath) };
          if (pt === 'visual' || pt === 'digital_product') {
            // For visual/digital, we don't need string content, file existence is evidence
            evidence.file = `exists size:${stat.size} ext:${path.extname(safePath)}`;
          } else {
            // For text/code, also read content if not provided
            if (!content) {
              fileContent = fs.readFileSync(safePath, 'utf8');
            }
          }
        } else {
          fileInfo = { exists: false };
          evidence.file = 'file not found';
        }
      } catch (e) {
        fileInfo = { exists: false, error: e.message };
        evidence.file = `read error: ${e.message}`;
      }
    }
  }

  const text = typeof fileContent === 'string' ? fileContent : (typeof content === 'string' ? content : '');

  // Criterion 1: not empty (critical, weight 20)
  {
    const passed = !isEmpty(text) || (fileInfo && fileInfo.exists && fileInfo.size > 0);
    const w = 20;
    totalWeight += w;
    if (passed) {
      score += w;
      criteria.push({ name: 'not_empty', passed: true, weight: w, evidence: fileInfo ? `file size ${fileInfo.size}` : `length ${getLength(text)}` });
      strengths.push('Content not empty');
      evidence.not_empty = 'non-empty';
    } else {
      criteria.push({ name: 'not_empty', passed: false, weight: w, evidence: 'empty content' });
      issues.push('Content is empty');
      evidence.not_empty = 'empty';
    }
  }

  // If empty, no need to check further length — but still evaluate other criteria for completeness
  const isEmptyFlag = isEmpty(text) && !(fileInfo && fileInfo.exists && fileInfo.size > 0);

  // Criterion 2: min length per product_type (weight 15)
  {
    const w = 15;
    totalWeight += w;
    if (isEmptyFlag) {
      criteria.push({ name: 'min_length', passed: false, weight: w, evidence: 'empty' });
      issues.push(`Content empty, fails min_length for ${pt}`);
    } else {
      const min = MIN_LENGTHS[pt] || 0;
      const len = getLength(text);
      // For visual, length 0 is ok if file exists
      let passed;
      let ev;
      if (pt === 'visual' && fileInfo && fileInfo.exists) {
        passed = true;
        ev = `visual file exists, length check waived`;
        strengths.push('Visual file present');
      } else {
        passed = len >= min;
        ev = `${len} chars (min ${min} for ${pt})`;
        if (passed) strengths.push(`Meets min length for ${pt}`);
      }
      if (passed) {
        score += w;
        criteria.push({ name: 'min_length', passed: true, weight: w, evidence: ev });
        evidence.min_length = ev;
      } else {
        criteria.push({ name: 'min_length', passed: false, weight: w, evidence: ev });
        // For B2B/digital_product short is critical, for text warning
        if (pt === 'digital_product' || pt === 'b2b') {
          issues.push(`Content too short for ${pt}: ${ev}`);
        } else {
          warnings.push(`Short content for ${pt}: ${ev}`);
        }
        evidence.min_length = ev;
      }
    }
  }

  // Criterion 3: repetition (weight 10)
  {
    const w = 10;
    totalWeight += w;
    const rep = hasExcessiveRepetition(text);
    if (!rep) {
      score += w;
      criteria.push({ name: 'no_repetition', passed: true, weight: w, evidence: 'no excessive repetition' });
      strengths.push('No excessive repetition');
      evidence.repetition = 'none';
    } else {
      criteria.push({ name: 'no_repetition', passed: false, weight: w, evidence: 'excessive repetition detected' });
      issues.push('Excessive repetition detected');
      evidence.repetition = 'high';
    }
  }

  // Criterion 4: TODO/undefined/null (weight 10, critical for code/digital/B2B)
  {
    const w = 10;
    totalWeight += w;
    const hasTodo = hasTodoMarkers(text);
    const hasUndef = pt === 'code' || pt === 'digital_product' || pt === 'b2b' ? hasUndefinedNullForCode(text) : false;
    const flagged = hasTodo || hasUndef;
    if (!flagged) {
      score += w;
      criteria.push({ name: 'no_todo', passed: true, weight: w, evidence: 'no TODO/undefined/null' });
      evidence.todo = 'clean';
    } else {
      criteria.push({ name: 'no_todo', passed: false, weight: w, evidence: `found ${hasTodo?'TODO/FIXME':''} ${hasUndef?'undefined/null':''}`.trim() });
      if (pt === 'code' || pt === 'b2b') {
        issues.push('Found TODO/undefined/null — not acceptable for ' + pt);
      } else {
        warnings.push('Found TODO/undefined — review required for ' + pt);
      }
      evidence.todo = 'found';
    }
  }

  // Criterion 5: structure (weight 15)
  {
    const w = 15;
    totalWeight += w;
    const res = checkStructure(text, pt);
    if (res.passed) {
      score += w;
      criteria.push({ name: 'structure', passed: true, weight: w, evidence: res.evidence });
      strengths.push('Structure OK for ' + pt);
      evidence.structure = res.evidence;
    } else {
      criteria.push({ name: 'structure', passed: false, weight: w, evidence: res.evidence });
      // B2B structure is critical, text is warning
      if (pt === 'b2b' || pt === 'code') issues.push(`Structure issue for ${pt}: ${res.evidence}`);
      else warnings.push(`Structure issue for ${pt}: ${res.evidence}`);
      evidence.structure = res.evidence;
    }
  }

  // Criterion 6: missing required elements (weight 15)
  {
    const w = 15;
    totalWeight += w;
    const missing = checkMissingElements(text, pt, metadata);
    if (missing.length === 0) {
      score += w;
      criteria.push({ name: 'required_elements', passed: true, weight: w, evidence: `all required for ${pt}: ${getRequiredElements(pt).join(', ')}` });
      strengths.push('All required elements present');
      evidence.required = 'all present';
    } else {
      criteria.push({ name: 'required_elements', passed: false, weight: w, evidence: `missing: ${missing.join(', ')}` });
      issues.push(`Missing required for ${pt}: ${missing.join(', ')}`);
      evidence.required = `missing ${missing.join(',')}`;
    }
  }

  // Criterion 7: file check for visual/digital_product (weight 15, but only for those)
  if (pt === 'visual' || pt === 'digital_product') {
    const w = 15;
    totalWeight += w;
    if (fileInfo && fileInfo.exists && fileInfo.size > 0) {
      score += w;
      criteria.push({ name: 'file_exists', passed: true, weight: w, evidence: `file ${fileInfo.size} bytes ext ${fileInfo.ext}` });
      evidence.file_exists = 'yes';
    } else if (filePath) {
      criteria.push({ name: 'file_exists', passed: false, weight: w, evidence: 'file not found or empty' });
      issues.push('Required file not found');
      evidence.file_exists = 'no';
    } else {
      // No filePath provided for visual/digital — check if content has file hint
      criteria.push({ name: 'file_exists', passed: false, weight: w, evidence: 'no filePath provided for file-based product' });
      warnings.push('No filePath for visual/digital_product — cannot verify file');
      evidence.file_exists = 'UNKNOWN — no evidence';
    }
  }

  // Final score 0-100
  const finalScore = totalWeight > 0 ? Math.round((score / totalWeight) * 100) : 0;

  // Classification: if no evidence provided at all, UNKNOWN
  const hasEvidence = finalScore > 0 || issues.length > 0 || warnings.length > 0;
  if (!hasEvidence && isEmptyFlag) {
    finalClassification = 'UNKNOWN';
  } else if (finalClassification === 'UNKNOWN' && hasEvidence) {
    // If caller said UNKNOWN but we have evidence, keep as provided? But spec says use UNKNOWN only when evidence missing
    // We'll keep as provided or promote to TEST if not specified
    if (!classification) finalClassification = 'TEST';
  }
  if (!classification) {
    finalClassification = 'TEST';
  } else if (['REAL','TEST','MOCK','UNKNOWN'].includes(classification)) {
    finalClassification = classification;
  } else {
    finalClassification = 'TEST';
  }

  // Verdict: not 95% => global ready. Use QA_APPROVED/REJECTED/REVIEW_REQUIRED
  const hasCriticalIssue = issues.length > 0;
  const hasUnknownEvidence = evidence.required && evidence.required.includes('UNKNOWN') || evidence.file_exists === 'UNKNOWN — no evidence';
  if (hasCriticalIssue || finalScore < 50) {
    verdict = 'QA_REJECTED';
    passed = false;
  } else if (hasUnknownEvidence || warnings.length > 0 || finalScore < 80) {
    verdict = 'QA_REVIEW_REQUIRED';
    passed = false;
  } else {
    verdict = 'QA_APPROVED';
    passed = true;
  }

  // Special: if video was handled earlier, we already returned, so not here
  // If classification is UNKNOWN due to missing evidence, ensure REVIEW_REQUIRED
  if (finalClassification === 'UNKNOWN' && verdict === 'QA_APPROVED') {
    verdict = 'QA_REVIEW_REQUIRED';
    passed = false;
  }

  return {
    score: finalScore,
    passed,
    verdict,
    issues,
    warnings,
    strengths,
    criteria,
    product_type: pt,
    contentType: ct,
    evidence,
    classification: finalClassification,
  };
}

module.exports = {
  evaluate,
  normalizeProductType,
  normalizeContentType,
  confineToRepoRoot,
  VALID_PRODUCT_TYPES: Array.from(VALID_PRODUCT_TYPES),
  MIN_LENGTHS,
};
