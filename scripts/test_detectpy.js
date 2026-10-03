function detectPython() {
  const candidates = ['python3', 'python', 'py'];
  for (const cmd of candidates) {
    try {
      require('child_process').execSync(`${cmd} --version`, { stdio: 'ignore' });
      return cmd;
    } catch { }
  }
  return 'python';
}
console.log('detected:', detectPython());
const { execFile } = require('child_process');
const payload = JSON.stringify({ email: 't@t.com', message: 'hi' });
execFile(detectPython(), ['lib/customer_evidence.py', 'record'],
  { input: payload, timeout: 15000, cwd: 'C:\\openclaw-dasgboard' },
  (err, stdout, stderr) => {
    console.log('err:', err && err.message);
    console.log('out:', String(stdout).slice(0, 300));
  });
