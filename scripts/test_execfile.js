const { execFile } = require('child_process');
const payload = JSON.stringify({ email: 'a@b.com' });
execFile('python3', ['lib/customer_evidence.py', 'record'],
  { input: payload, timeout: 15000, cwd: __dirname },
  (err, stdout, stderr) => {
    console.log('err:', err && err.message);
    console.log('code:', err && err.code);
    console.log('out:', JSON.stringify(String(stdout).slice(0, 300)));
    console.log('stderr:', JSON.stringify(String(stderr).slice(0, 300)));
  });
