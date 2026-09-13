const { describe, it, before, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const os = require('os');

const telemod = require('../lib/telegram_commands');
const { isAuthorized, checkRate, COMMANDS, processMessage, getFactoryStatus, getQueueSummary, getEvolutionQueueSummary, getHelpText, getActionsList, getQueueState, getEvolutionQueue, logCommand } = telemod._testExports();

function withEnv(overrides, fn) {
  const saved = {};
  for (const key of Object.keys(overrides)) {
    saved[key] = process.env[key];
    if (overrides[key] === undefined) delete process.env[key];
    else process.env[key] = overrides[key];
  }
  try { fn(); } finally {
    for (const key of Object.keys(overrides)) {
      if (saved[key] === undefined) delete process.env[key];
      else process.env[key] = saved[key];
    }
  }
}

describe('telegram-commands authorization', () => {
  it('authorized when chat ID matches', () => {
    withEnv({ OPENCLAW_TELEGRAM_CHAT_ID: '12345' }, () => {
      assert.ok(isAuthorized('12345'));
      assert.ok(isAuthorized(12345));
    });
  });
  it('unauthorized when chat ID differs', () => {
    withEnv({ OPENCLAW_TELEGRAM_CHAT_ID: '12345' }, () => {
      assert.ok(!isAuthorized('99999'));
    });
  });
  it('unauthorized when OPENCLAW_TELEGRAM_CHAT_ID not set', () => {
    withEnv({ OPENCLAW_TELEGRAM_CHAT_ID: undefined }, () => {
      assert.ok(!isAuthorized('12345'));
    });
  });
});

describe('telegram-commands rate limiting', () => {
  it('allows first request', () => {
    withEnv({ OPENCLAW_TELEGRAM_CHAT_ID: 'test' }, () => {
      assert.ok(checkRate('rate_test_1'));
    });
  });
  it('blocks after 10 requests in window', () => {
    withEnv({ OPENCLAW_TELEGRAM_CHAT_ID: 'test' }, () => {
      for (let i = 0; i < 10; i++) checkRate('rate_test_2');
      assert.ok(!checkRate('rate_test_2'));
    });
  });
});

describe('telegram-commands /help', () => {
  it('returns help text with all command names', () => {
    const text = getHelpText();
    assert.ok(text.includes('/status'));
    assert.ok(text.includes('/queue'));
    assert.ok(text.includes('/evolution'));
    assert.ok(text.includes('/pause'));
    assert.ok(text.includes('/resume'));
    assert.ok(text.includes('/approve'));
    assert.ok(text.includes('/reject'));
    assert.ok(text.includes('/help'));
  });
});

describe('telegram-commands /actions', () => {
  it('lists key actions', () => {
    const text = getActionsList();
    assert.ok(text.includes('pause_production') || text.includes('pause-production'));
    assert.ok(text.includes('resume_production') || text.includes('resume-production'));
    assert.ok(text.includes('approve'));
    assert.ok(text.includes('reject'));
  });
});

describe('telegram-commands /status', () => {
  it('returns factory status with readable text', () => {
    const text = getFactoryStatus();
    assert.ok(typeof text === 'string');
    assert.ok(text.length > 10);
    assert.ok(text.includes('Galaxy Forge'));
  });
});

describe('telegram-commands /queue', () => {
  it('returns queue summary', () => {
    const text = getQueueSummary();
    assert.ok(typeof text === 'string');
    assert.ok(text.includes('Job Queue'));
  });
});

describe('telegram-commands /evolution', () => {
  it('returns evolution queue summary', () => {
    const text = getEvolutionQueueSummary();
    assert.ok(typeof text === 'string');
    assert.ok(text.includes('Evolution Queue'));
  });
});

describe('telegram-commands getQueueState', () => {
  it('returns zeroed state when no queue file exists', () => {
    const q = getQueueState();
    assert.equal(typeof q.running, 'number');
    assert.equal(typeof q.pending, 'number');
    assert.equal(typeof q.completed, 'number');
    assert.equal(typeof q.failed, 'number');
    assert.equal(typeof q.total, 'number');
    assert.ok(Array.isArray(q.recent));
  });
});

describe('telegram-commands getEvolutionQueue', () => {
  it('returns awaiting array and total', () => {
    const eq = getEvolutionQueue();
    assert.ok(Array.isArray(eq.awaiting));
    assert.equal(typeof eq.total, 'number');
  });
});

describe('telegram-commands processMessage', () => {
  const fakeToken = 'fake-token';
  const fakeChatId = '12345';

  before(() => {
    process.env.TELEGRAM_BOT_TOKEN = fakeToken;
    process.env.OPENCLAW_TELEGRAM_CHAT_ID = fakeChatId;
  });

  it('ignores non-command messages', async () => {
    await processMessage({ chat: { id: fakeChatId }, text: 'hello world' }, fakeToken);
  });
  it('responds to /help without auth', async () => {
    await processMessage({ chat: { id: '99999' }, text: '/help' }, fakeToken);
  });
  it('rejects unauthorized commands', async () => {
    await processMessage({ chat: { id: '99999' }, text: '/status' }, fakeToken);
  });
  it('parses command with @botname suffix', async () => {
    await processMessage({ chat: { id: fakeChatId }, text: '/status@GalaxyForgeBot' }, fakeToken);
  });
  it('handles unknown commands', async () => {
    await processMessage({ chat: { id: fakeChatId }, text: '/nonexistent' }, fakeToken);
  });
  it('handles /pause without args', async () => {
    await processMessage({ chat: { id: fakeChatId }, text: '/pause' }, fakeToken);
  });
  it('handles /approve without proposal ID', async () => {
    await processMessage({ chat: { id: fakeChatId }, text: '/approve' }, fakeToken);
  });
});

describe('telegram-commands logCommand', () => {
  it('writes to telegram_commands.jsonl', () => {
    logCommand({ command: 'test', chatId: '123', result: 'ok' });
  });
});

describe('telegram-commands COMMANDS registry', () => {
  it('has all expected command names', () => {
    const expected = ['status', 'queue', 'help', 'actions', 'evolution', 'pause', 'resume', 'approve', 'reject'];
    for (const name of expected) {
      assert.ok(COMMANDS[name], `Missing command: ${name}`);
    }
  });
  it('every command has execute function', () => {
    for (const [name, cmd] of Object.entries(COMMANDS)) {
      assert.equal(typeof cmd.execute, 'function', `${name} missing execute`);
    }
  });
  it('state-changing commands are marked', () => {
    const stateChanging = ['pause', 'resume', 'approve', 'reject'];
    for (const name of stateChanging) {
      assert.ok(COMMANDS[name].stateChanging, `${name} should be stateChanging`);
    }
    const readOnly = ['status', 'queue', 'help', 'actions', 'evolution'];
    for (const name of readOnly) {
      assert.ok(!COMMANDS[name].stateChanging, `${name} should NOT be stateChanging`);
    }
  });
  it('non-help commands require auth', () => {
    for (const [name, cmd] of Object.entries(COMMANDS)) {
      if (name === 'help') {
        assert.ok(!cmd.auth, 'help should not require auth');
      } else {
        assert.ok(cmd.auth, `${name} should require auth`);
      }
    }
  });
});

describe('telegram-commands edge cases', () => {
  it('processMessage handles null text gracefully', async () => {
    await processMessage({ chat: { id: '12345' }, text: null }, 'token');
  });
  it('processMessage handles empty text gracefully', async () => {
    await processMessage({ chat: { id: '12345' }, text: '' }, 'token');
  });
  it('processMessage handles message without chat', async () => {
    await processMessage({ text: '/help' }, 'token');
  });
  it('processMessage handles /reject without proposal ID', async () => {
    await processMessage({ chat: { id: '12345' }, text: '/reject' }, 'token');
  });
});

describe('telegram-commands start/stop', () => {
  it('start returns false when env vars missing', () => {
    withEnv({ TELEGRAM_BOT_TOKEN: undefined, OPENCLAW_TELEGRAM_CHAT_ID: undefined }, () => {
      const result = require('../lib/telegram_commands').start();
      assert.equal(result, false);
    });
  });
});
