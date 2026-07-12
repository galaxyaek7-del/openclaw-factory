'use strict';
// OpenClaw Factory — Publisher -> distribution link (ADR-019).
//
// Extracted out of server.js so it's testable without a real Groq network
// call: the groq client, key, and system prompt are all injected by the
// caller (server.js passes its real ones; tests pass fakes). Never throws —
// a missing key, a missing title, or a Groq error are all returned as
// {ok:false, error}, matching the fail-safe style already used throughout
// server.js/factory_loop.js.

const fs = require('fs');
const path = require('path');

const DEFAULT_LOG_PATH = path.join(__dirname, '..', 'publisher_seo_log.jsonl');

function logPublisherSEO(entry, logPath = DEFAULT_LOG_PATH) {
  try {
    fs.appendFileSync(logPath, JSON.stringify({ timestamp: new Date().toISOString(), ...entry }) + '\n');
  } catch (_) { /* logging must never break a distribution attempt */ }
}

async function generatePublisherSEO(record, { groqClient, groqKey, systemPrompt } = {}) {
  const title = (record && (record.title || record.topic)) || '';
  if (!groqKey) return { ok: false, error: 'GROQ_KEY غير مضبوط في .env' };
  if (!title) return { ok: false, error: 'لا عنوان أو نيتش في السجل لإنتاج بيانات SEO له' };
  try {
    const response = await groqClient.chat.completions.create({
      model: 'llama-3.1-8b-instant',
      max_tokens: 1024,
      messages: [
        { role: 'system', content: systemPrompt },
        {
          role: 'user',
          content: `حضّر بيانات نشر محسّنة لـSEO لهذا المنتج الحقيقي (لا مثال افتراضي):\nالعنوان: ${title}\nالوصف/النيتش: ${record.topic || record.description || ''}`,
        },
      ],
    });
    return { ok: true, content: response.choices[0].message.content };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

module.exports = { logPublisherSEO, generatePublisherSEO, DEFAULT_LOG_PATH };
