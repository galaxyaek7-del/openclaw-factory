const { execFile } = require('child_process');
execFile('python3', ['lib/customer_evidence.py', 'report'],
  { timeout: 20000, cwd: 'C:\\openclaw-dasgboard' },
  (err, stdout, stderr) => {
    console.log('err:', err && err.message);
    console.log('out:', String(stdout).slice(0, 200));
    console.log('stderr:', String(stderr).slice(0, 200));
  });
