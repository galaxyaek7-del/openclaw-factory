const fs = require('fs');
const path = require('path');

const REGISTRY_PATH = path.join(__dirname, 'programs_registry.json');
const LINKS_PATH = path.join(__dirname, 'tracking_links.json');
const REPORT_PATH = path.join(__dirname, 'affiliate_report.json');

class AffiliateEngine {
  constructor(registryPath = REGISTRY_PATH, linksPath = LINKS_PATH, reportPath = REPORT_PATH) {
    this.registryPath = registryPath;
    this.linksPath = linksPath;
    this.reportPath = reportPath;
  }

  _loadRegistry() {
    try {
      const raw = fs.readFileSync(this.registryPath, 'utf8');
      const data = JSON.parse(raw);
      return Array.isArray(data.programs) ? data.programs : [];
    } catch (_) {
      return [];
    }
  }

  _loadLinks() {
    try {
      if (!fs.existsSync(this.linksPath)) return { links: [] };
      const raw = fs.readFileSync(this.linksPath, 'utf8');
      const data = JSON.parse(raw);
      return { links: Array.isArray(data.links) ? data.links : [], raw: data };
    } catch (_) {
      return { links: [] };
    }
  }

  _loadReport() {
    try {
      if (!fs.existsSync(this.reportPath)) return { programs: [] };
      const raw = fs.readFileSync(this.reportPath, 'utf8');
      return JSON.parse(raw);
    } catch (_) {
      return { programs: [] };
    }
  }

  _parseCommission(commissionStr) {
    // Handles "3-10%", "50%", "30%", "50% first year"
    if (!commissionStr || typeof commissionStr !== 'string') return 0;
    const nums = commissionStr.match(/(\d+(?:\.\d+)?)/g);
    if (!nums || nums.length === 0) return 0;
    const values = nums.map(n => parseFloat(n));
    if (values.length >= 2) {
      // range like 3-10 => average 6.5
      return (values[0] + values[1]) / 2;
    }
    return values[0];
  }

  // قائمة البرامج المسجلة
  getPrograms(status = null) {
    const programs = this._loadRegistry();
    if (status == null) return programs;
    const s = String(status).trim().toUpperCase();
    return programs.filter(p => String(p.status).toUpperCase() === s);
  }

  // إنشاء رابط تتبع — يضيف UTM parameters
  generateTrackingLink(programId, productUrl) {
    const pid = String(programId || '').trim();
    if (!pid) throw new Error('programId required');
    const programs = this._loadRegistry();
    const prog = programs.find(p => p.id === pid);
    if (!prog) throw new Error(`program not found: ${pid}`);

    let url = String(productUrl || '').trim();
    if (!url) throw new Error('productUrl required');
    // Ensure url has protocol for URL parsing; if missing, keep as is and append manually
    const utm = `utm_source=galaxyforge&utm_medium=affiliate&utm_campaign=${encodeURIComponent(pid)}`;
    const hasQuery = url.includes('?');
    const separator = hasQuery ? '&' : '?';
    const tracked = `${url}${separator}${utm}`;

    // Persist to tracking_links.json (append, never overwrite history)
    try {
      fs.mkdirSync(path.dirname(this.linksPath), { recursive: true });
      let data = { links: [] };
      let existingRaw = {};
      if (fs.existsSync(this.linksPath)) {
        try {
          const raw = fs.readFileSync(this.linksPath, 'utf8');
          const parsed = JSON.parse(raw);
          existingRaw = parsed;
          data.links = Array.isArray(parsed.links) ? parsed.links : [];
        } catch (_) {
          data.links = [];
        }
      }
      data.links.push({
        programId: pid,
        productUrl: url,
        trackingLink: tracked,
        created_at: new Date().toISOString()
      });
      // keep original fields like generated_at, note if existed
      const out = { ...existingRaw, links: data.links, generated_at: new Date().toISOString() };
      if (!out.note) out.note = "تحضير فقط — لا تسجيل في أي برنامج الآن.";
      fs.writeFileSync(this.linksPath, JSON.stringify(out, null, 2), 'utf8');
    } catch (_) {
      // persist failure must not block link generation
    }

    return tracked;
  }

  // حساب العمولة المتوقعة
  calculateExpectedCommission(programId, saleAmount) {
    const pid = String(programId || '').trim();
    const amount = Number(saleAmount);
    if (!Number.isFinite(amount) || amount < 0) throw new Error('saleAmount must be a non-negative number');
    const programs = this._loadRegistry();
    const prog = programs.find(p => p.id === pid);
    if (!prog) throw new Error(`program not found: ${pid}`);
    const rate = this._parseCommission(prog.commission);
    const expected = (amount * rate) / 100;
    return {
      programId: pid,
      programName: prog.name,
      commission: prog.commission,
      rate_percent: rate,
      sale_amount: amount,
      expected_commission: Number(expected.toFixed(2))
    };
  }

  // تقرير الأداء — clicks, conversions, revenue per program
  getPerformanceReport() {
    const programs = this._loadRegistry();
    const { links } = this._loadLinks();
    const reportData = this._loadReport();

    // Count clicks per program from tracking_links.json
    const clicksByProgram = {};
    for (const l of links) {
      const pid = l.programId || l.program_id;
      if (!pid) continue;
      clicksByProgram[pid] = (clicksByProgram[pid] || 0) + 1;
    }

    // Conversions/revenue from affiliate_report.json if present, else 0
    const reportByProgram = {};
    if (reportData && Array.isArray(reportData.programs)) {
      for (const r of reportData.programs) {
        reportByProgram[r.id] = r;
      }
    }

    const perProgram = programs.map(p => {
      const r = reportByProgram[p.id] || {};
      return {
        id: p.id,
        name: p.name,
        commission: p.commission,
        priority: p.priority,
        status: p.status,
        clicks: clicksByProgram[p.id] || 0,
        conversions: typeof r.conversions === 'number' ? r.conversions : 0,
        revenue: typeof r.revenue === 'number' ? r.revenue : 0,
        link: p.link
      };
    });

    const totals = perProgram.reduce((acc, cur) => {
      acc.clicks += cur.clicks;
      acc.conversions += cur.conversions;
      acc.revenue += cur.revenue;
      return acc;
    }, { clicks: 0, conversions: 0, revenue: 0 });

    return {
      generated_at: new Date().toISOString(),
      period: reportData.period || "foundation — no real traffic yet",
      totals,
      programs: perProgram
    };
  }

  // أفضل برنامج هذا الأسبوع — الأعلى revenue ثم clicks
  getTopPerformer() {
    const report = this.getPerformanceReport();
    if (!report.programs || report.programs.length === 0) return null;
    // Filter to only programs with activity; if none, return highest priority READY_TO_JOIN as top potential
    const withActivity = report.programs.filter(p => p.revenue > 0 || p.clicks > 0);
    const pool = withActivity.length > 0 ? withActivity : report.programs;
    let top = pool[0];
    for (const p of pool) {
      if (p.revenue > top.revenue || (p.revenue === top.revenue && p.clicks > top.clicks)) {
        top = p;
      }
    }
    // If all zero, pick by priority (lowest number = highest priority)
    if (top.revenue === 0 && top.clicks === 0) {
      top = [...report.programs].sort((a, b) => a.priority - b.priority)[0];
      return { ...top, note: "لا نشاط بعد — الأعلى أولوية كأفضل مرشح" };
    }
    return top;
  }
}

module.exports = AffiliateEngine;
