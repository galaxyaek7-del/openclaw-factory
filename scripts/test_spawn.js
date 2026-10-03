const { execFile, spawn } = require('child_process');
// Attempt 1: execFile with input
execFile('python3', ['lib/customer_evidence.py', 'record'],
  { input: JSON.stringify({ email: 't@t.com', message: 'hi' }), cwd: 'C:\\openclaw-dasgboard' },
  (err, stdout, stderr) => {
    console.log('execFile err:', err && err.message);
    console.log('execFile code:', err && err.code);
    console.log('execFile out:', JSON.stringify(String(stdout).slice(0, 200)));
    console.log('execFile stderr:', JSON.stringify(String(stderr).slice(0, 300)));
    // Attempt 2: spawn with stdin write
    const p = spawn('python3', ['lib/customer_evidence.py', 'record'], { cwd: 'C:\\openclaw-dasgboard' });
    let out = '', err2 = '';
    p.stdout.on('data', d => out += d);
    p.stderr.on('data', d => err2 += d);
    p.on('close', code => {
      console.log('spawn code:', code);
      console.log('spawn out:', out.slice(0, 200));
      console.log('spawn stderr:', err2.slice(0, 300));
    });
    p.stdin.write(JSON.stringify({ email: 't@t.com', message: 'hi' }));
    p.stdin.end();
  });
