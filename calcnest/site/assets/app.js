/* MoneyMath — all calculators and converters run in the browser. No data leaves the page. */
(function (root) {
  'use strict';

  var nf0 = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });
  var nf2 = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 });
  var nfMoney = new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var nfConv = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 6 });

  function inr(n) { return '₹' + nf0.format(Math.round(n)); }
  function inr2(n) { return '₹' + nfMoney.format(n); }
  function plain(n) { return nf2.format(+n.toPrecision(12)); }

  /* US dollars and loan helpers */
  var nfUsd0 = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
  var nfUsd2 = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  function usd(n) { return (n < 0 ? '-$' : '$') + nfUsd0.format(Math.abs(Math.round(n))); }
  function usd2(n) { return (n < 0 ? '-$' : '$') + nfUsd2.format(Math.abs(n)); }
  function yearsMonths(m) {
    var y = Math.floor(m / 12), mo = m % 12, out = [];
    if (y) out.push(y + (y === 1 ? ' year' : ' years'));
    if (mo || !y) out.push(mo + (mo === 1 ? ' month' : ' months'));
    return out.join(', ');
  }
  function monthYear(monthsFromNow) {
    var d = new Date(); d.setDate(1); d.setMonth(d.getMonth() + monthsFromNow);
    return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  }
  function pmt(P, i, n) { return i === 0 ? P / n : (P * i * Math.pow(1 + i, n)) / (Math.pow(1 + i, n) - 1); }
  function amortize(P, annualRate, n, extra) {
    var i = annualRate / 1200, pay = pmt(P, i, n), bal = P, interest = 0, m = 0;
    while (m < n && bal > 0.005) {
      var it = bal * i, princ = Math.min(bal, pay + extra - it);
      interest += it; bal -= princ; m++;
    }
    return { months: m, interest: interest, payment: pay };
  }
  function bracketTax(income, brackets) {
    var tax = 0;
    for (var k = 0; k < brackets.length; k++) {
      var lo = brackets[k][0], hi = k + 1 < brackets.length ? brackets[k + 1][0] : Infinity;
      if (income > lo) tax += (Math.min(income, hi) - lo) * brackets[k][1];
    }
    return tax;
  }
  function payoff(B, r, p) {
    var bal = B, interest = 0, m = 0;
    while (bal > 0.005 && m < 1200) { var it = bal * r; interest += it; bal = bal + it - p; m++; }
    return { months: m, interest: interest, done: bal <= 0.005 };
  }

  function words(n) {
    if (!isFinite(n) || n < 1000) return '';
    if (n >= 1e7) return '₹' + nf2.format(n / 1e7) + ' Crore';
    if (n >= 1e5) return '₹' + nf2.format(n / 1e5) + ' Lakh';
    return '₹' + nf2.format(n / 1e3) + ' Thousand';
  }

  /* ------------------------------------------------------------------ *
   * Calculators. Each takes the field values and returns a result object:
   * { primary:[label,value], rows:[[label,value]...], donut:[[label,amount,color]...] }
   * or { error:'message' } or null (not enough input yet).
   * ------------------------------------------------------------------ */
  var CALCS = {
    emi: function (v) {
      var P = v.amount, n = Math.round(v.years * 12), r = v.rate / 1200;
      if (!(P > 0) || !(n > 0) || !(v.rate >= 0)) return null;
      var e = r === 0 ? P / n : (P * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
      var total = e * n, interest = total - P;
      return {
        primary: ['Monthly EMI', inr(e)],
        donut: [['Principal', P, '#2d4ef5'], ['Total interest', interest, '#ffc83d']],
        rows: [
          ['Principal amount', inr(P)],
          ['Total interest', inr(interest)],
          ['Total payment', inr(total)],
          ['Loan term', n + ' months']
        ]
      };
    },

    sip: function (v) {
      var P = v.monthly, i = v.rate / 1200, n = Math.round(v.years * 12), step = (v.step || 0) / 100;
      if (!(P > 0) || !(n > 0) || !(v.rate >= 0)) return null;
      var bal = 0, invested = 0, dep = P;
      for (var m = 1; m <= n; m++) {
        if (m > 1 && (m - 1) % 12 === 0) dep *= 1 + step;
        bal = (bal + dep) * (1 + i); // deposit at the start of each month
        invested += dep;
      }
      var gain = bal - invested;
      return {
        primary: ['Estimated value', inr(bal)],
        donut: [['Amount invested', invested, '#2d4ef5'], ['Estimated returns', gain, '#ffc83d']],
        rows: [
          ['Amount invested', inr(invested)],
          ['Estimated returns', inr(gain)],
          ['Total value', inr(bal)],
          ['Investment period', n + ' months']
        ]
      };
    },

    'pct-of': function (v) {
      if (isNaN(v.x) || isNaN(v.y)) return null;
      return { primary: ['Result', plain((v.x * v.y) / 100)] };
    },
    'pct-is': function (v) {
      if (isNaN(v.x) || isNaN(v.y)) return null;
      if (v.y === 0) return { error: 'The second number cannot be zero.' };
      return { primary: ['Result', plain((v.x / v.y) * 100) + '%'] };
    },
    'pct-change': function (v) {
      if (isNaN(v.x) || isNaN(v.y)) return null;
      if (v.x === 0) return { error: 'The starting value cannot be zero.' };
      var c = ((v.y - v.x) / Math.abs(v.x)) * 100;
      var word = c > 0 ? 'increase' : c < 0 ? 'decrease' : 'change';
      return {
        primary: [word.charAt(0).toUpperCase() + word.slice(1), plain(Math.abs(c)) + '%'],
        rows: [['Difference', plain(v.y - v.x)]]
      };
    },

    age: function (v) {
      var a = parseDate(v.dob), b = parseDate(v.on);
      if (!a || !b) return null;
      if (a > b) return { error: 'Date of birth must be before the "Age on" date.' };
      var y = b.getFullYear() - a.getFullYear(), m = b.getMonth() - a.getMonth(), d = b.getDate() - a.getDate();
      if (d < 0) { m--; d += new Date(b.getFullYear(), b.getMonth(), 0).getDate(); }
      if (m < 0) { y--; m += 12; }
      var days = Math.round((Date.UTC(b.getFullYear(), b.getMonth(), b.getDate()) - Date.UTC(a.getFullYear(), a.getMonth(), a.getDate())) / 864e5);
      var next = new Date(b.getFullYear(), a.getMonth(), a.getDate());
      if (next < b) next = new Date(b.getFullYear() + 1, a.getMonth(), a.getDate());
      var toNext = Math.round((Date.UTC(next.getFullYear(), next.getMonth(), next.getDate()) - Date.UTC(b.getFullYear(), b.getMonth(), b.getDate())) / 864e5);
      var wd = next.toLocaleDateString('en-IN', { weekday: 'long' });
      return {
        primary: ['Your age', y + ' years, ' + m + ' months, ' + d + ' days'],
        rows: [
          ['Total months', nf0.format(y * 12 + m)],
          ['Total weeks', nf0.format(Math.floor(days / 7))],
          ['Total days', nf0.format(days)],
          ['Next birthday', toNext === 0 ? 'Today' : 'in ' + toNext + ' days (' + wd + ')']
        ]
      };
    },

    gst: function (v) {
      var amt = v.amount, r = v.rate;
      if (!(amt >= 0) || !(r >= 0) || isNaN(amt) || isNaN(r)) return null;
      var base, gst, total;
      if (v.mode === 'remove') { total = amt; base = total / (1 + r / 100); gst = total - base; }
      else { base = amt; gst = (base * r) / 100; total = base + gst; }
      return {
        primary: v.mode === 'remove' ? ['Amount without GST', inr2(base)] : ['Total with GST', inr2(total)],
        rows: [
          ['Amount before GST', inr2(base)],
          ['CGST (' + plain(r / 2) + '%)', inr2(gst / 2)],
          ['SGST (' + plain(r / 2) + '%)', inr2(gst / 2)],
          ['Total GST (IGST if inter-state)', inr2(gst)],
          ['Amount with GST', inr2(total)]
        ]
      };
    }
  };

  var BLUE = '#2d4ef5', GOLD = '#ffc83d', TEAL = '#0b8f80', GREY = '#9fb0d4', NAVY = '#0e1a30';

  Object.assign(CALCS, {
    mortgage: function (v) {
      var price = v.price, down = v.down, rate = v.rate, years = +v.years;
      if (!(price > 0) || isNaN(down) || isNaN(rate) || !(years > 0) || rate < 0) return null;
      if (down < 0 || down >= 100) return { error: 'Enter a down payment between 0% and 99%.' };
      var loan = price * (1 - down / 100), n = Math.round(years * 12);
      var pi = pmt(loan, rate / 1200, n);
      var tax = (price * (v.tax || 0)) / 1200, ins = (v.ins || 0) / 12, hoa = v.hoa || 0;
      var pmi = down < 20 ? (loan * (v.pmi || 0)) / 1200 : 0;
      var extra = v.extra > 0 ? v.extra : 0;
      var base = amortize(loan, rate, n, 0);
      var fast = extra > 0 ? amortize(loan, rate, n, extra) : base;
      var rows = [
        ['Loan amount', usd(loan)],
        ['Down payment', usd(price - loan)],
        ['Principal and interest', usd2(pi)],
        ['Property tax', usd2(tax)],
        ['Home insurance', usd2(ins)]
      ];
      if (pmi > 0) rows.push(['Mortgage insurance (PMI)', usd2(pmi)]);
      if (hoa > 0) rows.push(['HOA dues', usd2(hoa)]);
      rows.push(['Total interest over the loan', usd(fast.interest)]);
      rows.push(['Paid off in', yearsMonths(fast.months)]);
      if (extra > 0) {
        rows.push(['Extra principal payment', usd2(extra) + ' a month']);
        rows.push(['Interest saved by paying extra', usd(base.interest - fast.interest)]);
      }
      return {
        primary: ['Monthly payment', usd2(pi + tax + ins + pmi + hoa)],
        donut: [['Principal and interest', pi, BLUE], ['Property tax', tax, TEAL], ['Home insurance', ins, GOLD], ['PMI and HOA', pmi + hoa, GREY]],
        rows: rows,
        note: pmi > 0 ? 'PMI is included because your down payment is under 20%. It usually ends once you reach 20% equity.' : ''
      };
    },

    auto: function (v) {
      var price = v.price, down = v.down || 0, trade = v.trade || 0, rate = v.rate, n = +v.months;
      if (!(price > 0) || isNaN(rate) || rate < 0 || !(n > 0)) return null;
      var tax = (Math.max(0, price - trade) * (v.tax || 0)) / 100;
      var loan = price - trade + tax - down;
      if (loan <= 0) return { error: 'Your down payment and trade-in cover the full cost, so there is nothing to finance. Lower them to see a payment.' };
      var pay = pmt(loan, rate / 1200, n), interest = pay * n - loan;
      return {
        primary: ['Monthly payment', usd2(pay)],
        donut: [['Amount financed', loan, BLUE], ['Total interest', interest, GOLD]],
        rows: [
          ['Amount financed', usd(loan)],
          ['Sales tax', usd(tax)],
          ['Total interest', usd(interest)],
          ['Total of all payments', usd(pay * n)],
          ['Total cost (price, tax and interest)', usd(price + tax + interest)],
          ['Loan term', n + ' months']
        ]
      };
    },

    compound: function (v) {
      var P = v.initial || 0, c = v.monthly || 0, rate = v.rate, yrs = v.years, m = +v.freq;
      if (isNaN(rate) || rate < 0 || !(yrs > 0) || (P <= 0 && c <= 0)) return null;
      var months = Math.round(yrs * 12), g = Math.pow(1 + rate / 100 / m, m / 12), bal = P;
      for (var k = 0; k < months; k++) bal = bal * g + c;
      var put = c * months, interest = bal - P - put;
      var rows = [['Starting balance', usd(P)], ['Total contributions', usd(put)], ['Interest earned', usd(interest)]];
      if (rate > 0) rows.push(['Years to double (rule of 72)', plain(72 / rate)]);
      return {
        primary: ['Future value', usd(bal)],
        donut: [['Starting balance', P, BLUE], ['Contributions', put, TEAL], ['Interest earned', interest, GOLD]],
        rows: rows
      };
    },

    retire: function (v) {
      var age = v.age, ret = v.retire, saved = v.saved || 0, mo = v.monthly || 0, er = v.employer || 0, rate = v.rate, inf = v.inflation || 0;
      if (isNaN(age) || isNaN(ret) || isNaN(rate) || rate < 0) return null;
      if (ret <= age) return { error: 'Retirement age must be higher than your current age.' };
      var months = Math.round((ret - age) * 12), g = Math.pow(1 + rate / 100, 1 / 12), bal = saved;
      for (var k = 0; k < months; k++) bal = bal * g + mo + er;
      var mine = mo * months, theirs = er * months, growth = bal - saved - mine - theirs;
      var real = bal / Math.pow(1 + inf / 100, months / 12);
      var limit = age >= 50 ? 32500 : 24500;
      var rows = [['In today\'s dollars', usd(real)], ['Current savings', usd(saved)], ['Your contributions', usd(mine)]];
      if (er > 0) rows.push(['Employer contributions', usd(theirs)]);
      rows.push(['Investment growth', usd(growth)]);
      rows.push(['Yearly income at 4% (today\'s dollars)', usd(real * 0.04)]);
      rows.push(['Monthly income at 4% (today\'s dollars)', usd((real * 0.04) / 12)]);
      return {
        primary: ['Projected savings at ' + ret, usd(bal)],
        donut: [['Current savings', saved, BLUE], ['Your contributions', mine, TEAL], ['Employer', theirs, NAVY], ['Growth', growth, GOLD]],
        rows: rows,
        note: mo * 12 > limit ? 'Your own contributions of ' + usd(mo * 12) + ' a year are above the 2026 401(k) limit of ' + usd(limit) + (age >= 50 ? ' (with catch-up)' : '') + '. Some of it would need to go to other accounts.' : ''
      };
    },

    card: function (v) {
      var B = v.balance, apr = v.apr, p = v.payment;
      if (!(B > 0) || isNaN(apr) || apr < 0 || !(p > 0)) return null;
      var r = apr / 1200, first = B * r;
      if (p <= first + 0.005) return { error: 'A payment of ' + usd2(p) + ' does not cover the first month of interest (' + usd2(first) + '). Raise the payment above that to bring the balance down.' };
      var a = payoff(B, r, p);
      if (!a.done) return { error: 'At this payment the balance would take more than 100 years to clear. Try a higher payment.' };
      var b = payoff(B, r, p + 50);
      return {
        primary: ['Debt-free in', yearsMonths(a.months)],
        donut: [['Balance', B, BLUE], ['Interest', a.interest, GOLD]],
        rows: [['Payoff date', monthYear(a.months)], ['Total interest', usd(a.interest)], ['Total paid', usd(B + a.interest)]],
        note: a.months > b.months ? 'Adding $50 a month would clear the balance ' + (a.months - b.months) + (a.months - b.months === 1 ? ' month' : ' months') + ' sooner and save ' + usd(a.interest - b.interest) + ' in interest.' : ''
      };
    },

    takehome: function (v) {
      var T = root.TAX2026, fs = T && T[v.status], g = v.salary, k = v.k401 || 0, st = Math.max(0, v.state || 0);
      if (!(g > 0) || !fs) return null;
      if (k < 0 || k > g) return { error: 'Your 401(k) contribution must be between $0 and your salary.' };
      var taxable = Math.max(0, g - k - fs.std), fed = bracketTax(taxable, fs.brackets);
      var ss = Math.min(g, T.ssBase) * T.ssRate;
      var med = g * T.medRate + Math.max(0, g - fs.medThreshold) * T.addMed;
      var state = (Math.max(0, g - k) * st) / 100;
      var net = g - k - fed - ss - med - state;
      var marginal = fs.brackets[0][1];
      fs.brackets.forEach(function (b) { if (taxable > b[0]) marginal = b[1]; });
      var rows = [
        ['Take-home per year', usd(net)],
        ['Every two weeks', usd(net / 26)],
        ['Federal income tax', usd(fed)],
        ['Social Security', usd(ss)],
        ['Medicare', usd(med)]
      ];
      if (state > 0) rows.push(['State income tax (estimate)', usd(state)]);
      if (k > 0) rows.push(['401(k) contributions', usd(k)]);
      rows.push(['Federal marginal rate', Math.round(marginal * 100) + '%']);
      rows.push(['Effective federal rate', plain((fed / g) * 100) + '%']);
      return {
        primary: ['Take-home per month', usd(net / 12)],
        donut: [['Take-home pay', net, BLUE], ['Federal tax', fed, GOLD], ['Social Security and Medicare', ss + med, TEAL], ['State tax', state, GREY], ['401(k)', k, NAVY]],
        rows: rows,
        note: 'Estimate using 2026 federal brackets and the standard deduction. Credits, itemized deductions, other income, local taxes and health premiums are not included.'
      };
    }
  });

  function parseDate(s) {
    if (!s) return null;
    var p = s.split('-');
    if (p.length !== 3) return null;
    var d = new Date(+p[0], +p[1] - 1, +p[2]);
    return isNaN(d) ? null : d;
  }

  /* ------------------------------------------------------------------ *
   * Unit conversion
   * ------------------------------------------------------------------ */
  var TEMP_FORMULAS = {
    'c>f': '°F = °C × 9/5 + 32', 'f>c': '°C = (°F − 32) × 5/9',
    'c>k': 'K = °C + 273.15', 'k>c': '°C = K − 273.15',
    'f>k': 'K = (°F − 32) × 5/9 + 273.15', 'k>f': '°F = (K − 273.15) × 9/5 + 32'
  };

  function factor(cat, id) {
    var us = root.UNITS[cat].units;
    for (var i = 0; i < us.length; i++) if (us[i].id === id) return us[i].f;
    return 1;
  }
  function toBase(cat, u, x) {
    if (cat === 'temperature') return u === 'c' ? x : u === 'f' ? ((x - 32) * 5) / 9 : x - 273.15;
    return x * factor(cat, u);
  }
  function fromBase(cat, u, b) {
    if (cat === 'temperature') return u === 'c' ? b : u === 'f' ? (b * 9) / 5 + 32 : b + 273.15;
    return b / factor(cat, u);
  }
  function convert(cat, from, to, x) { return fromBase(cat, to, toBase(cat, from, x)); }
  function fmtConv(n) {
    if (!isFinite(n)) return '—';
    var a = Math.abs(n);
    if (a !== 0 && (a >= 1e15 || a < 1e-6)) return n.toExponential(5);
    return nfConv.format(+n.toPrecision(12));
  }

  /* ------------------------------------------------------------------ *
   * Page wiring (browser only)
   * ------------------------------------------------------------------ */
  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    for (var k in attrs || {}) e.setAttribute(k, attrs[k]);
    if (html != null) e.innerHTML = html;
    return e;
  }

  function sliderFill(s) {
    var min = +s.min, max = +s.max, v = +s.value;
    var p = max > min ? Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100)) : 0;
    s.style.setProperty('--p', p + '%');
  }

  function readValues(form) {
    var vals = {};
    form.querySelectorAll('[data-field]').forEach(function (f) {
      var key = f.getAttribute('data-field');
      if (f.classList.contains('seg')) {
        var on = f.querySelector('button[aria-pressed="true"]');
        vals[key] = on ? on.getAttribute('data-v') : '';
      } else {
        var inp = f.querySelector('input[type="number"], input[type="date"]');
        vals[key] = inp.type === 'date' ? inp.value : (inp.value === '' ? NaN : parseFloat(inp.value));
      }
    });
    return vals;
  }

  function renderResult(out, r) {
    if (!r) { out.innerHTML = '<p class="empty">Fill in the values to see your result.</p>'; return; }
    if (r.error) { out.innerHTML = '<p class="empty">' + r.error + '</p>'; return; }
    var html = '<div class="primary"><span class="plabel">' + r.primary[0] + '</span><strong class="pvalue">' + r.primary[1] + '</strong></div>';
    if (r.donut) {
      var sum = r.donut.filter(function (d) { return d[1] > 0.005; }).reduce(function (s, d) { return s + d[1]; }, 0), acc = 0, stops = [], legend = '';
      r.donut.filter(function (d) { return d[1] > 0.005; }).forEach(function (d) {
        var s = (acc / sum) * 100; acc += d[1]; var e = (acc / sum) * 100;
        stops.push(d[2] + ' ' + s + '% ' + e + '%');
        legend += '<li><i style="background:' + d[2] + '"></i>' + d[0] + ' · ' + Math.round((d[1] / sum) * 100) + '%</li>';
      });
      html += '<div class="donut-wrap"><div class="donut" role="img" aria-label="Breakdown chart" style="background:conic-gradient(' + stops.join(',') + ')"></div><ul class="legend">' + legend + '</ul></div>';
    }
    if (r.rows) {
      html += '<dl class="rows">' + r.rows.map(function (x) { return '<div><dt>' + x[0] + '</dt><dd>' + x[1] + '</dd></div>'; }).join('') + '</dl>';
    }
    if (r.note) html += '<p class="note-line">' + r.note + '</p>';
    out.innerHTML = html;
  }

  function initCalc(form) {
    var fn = CALCS[form.getAttribute('data-calc')];
    var out = form.querySelector('.out');
    if (!fn || !out) return;

    var onDate = form.querySelector('input[name="on"]');
    if (onDate && !onDate.value) {
      var t = new Date();
      onDate.value = t.getFullYear() + '-' + String(t.getMonth() + 1).padStart(2, '0') + '-' + String(t.getDate()).padStart(2, '0');
    }

    function sync(field) {
      var inp = field.querySelector('input[type="number"]');
      var sl = field.querySelector('.slider');
      var hint = field.querySelector('.hint');
      if (sl && inp) { sl.value = inp.value; sliderFill(sl); }
      if (hint && field.hasAttribute('data-words')) hint.textContent = words(parseFloat(inp.value));
      var of = field.getAttribute('data-of');
      if (hint && of) {
        var src = form.querySelector('[data-field="' + of + '"] input[type="number"]');
        hint.textContent = src ? '= ' + usd((parseFloat(src.value) || 0) * (parseFloat(inp.value) || 0) / 100) : '';
      }
      field.querySelectorAll('.chip').forEach(function (c) {
        c.setAttribute('aria-pressed', String(parseFloat(inp.value) === parseFloat(c.getAttribute('data-v'))));
      });
    }
    function update() {
      form.querySelectorAll('[data-of]').forEach(sync);
      renderResult(out, fn(readValues(form)));
    }

    form.querySelectorAll('[data-field]').forEach(function (field) {
      var inp = field.querySelector('input[type="number"]');
      var sl = field.querySelector('.slider');
      if (sl && inp) sl.addEventListener('input', function () { inp.value = sl.value; sync(field); update(); });
      if (inp) inp.addEventListener('input', function () { sync(field); update(); });
      field.querySelectorAll('.chip').forEach(function (c) {
        c.addEventListener('click', function () { inp.value = c.getAttribute('data-v'); sync(field); update(); });
      });
      if (field.classList.contains('seg')) {
        field.querySelectorAll('button').forEach(function (b) {
          b.addEventListener('click', function () {
            field.querySelectorAll('button').forEach(function (o) { o.setAttribute('aria-pressed', String(o === b)); });
            update();
          });
        });
      }
      if (inp) sync(field);
    });
    form.addEventListener('input', function (e) { if (e.target.type === 'date') update(); });
    form.addEventListener('submit', function (e) { e.preventDefault(); });
    update();
  }

  function initConv(form) {
    var U = root.UNITS;
    var catSel = form.querySelector('[name="cat"]');
    var val = form.querySelector('[name="val"]');
    var from = form.querySelector('[name="from"]');
    var to = form.querySelector('[name="to"]');
    var out = form.querySelector('.cout');
    var formula = form.querySelector('.formula');
    var swap = form.querySelector('.swap');
    var cat = catSel ? catSel.value : form.getAttribute('data-cat');

    function fill(sel, want) {
      sel.innerHTML = '';
      U[cat].units.forEach(function (u) { sel.appendChild(el('option', { value: u.id }, u.name)); });
      sel.value = want;
    }
    function defaults() {
      var us = U[cat].units;
      return [us[0].id, (us[1] || us[0]).id];
    }
    function setCat(c, f, t) {
      cat = c;
      var d = defaults();
      fill(from, f || d[0]);
      fill(to, t || d[1]);
    }
    function update() {
      var x = parseFloat(val.value);
      var f = from.value, t = to.value;
      if (isNaN(x)) { out.textContent = '—'; }
      else { out.textContent = fmtConv(convert(cat, f, t, x)); }
      if (formula) {
        if (cat === 'temperature') {
          formula.innerHTML = f === t ? '' : '<strong>Formula:</strong> ' + TEMP_FORMULAS[f + '>' + t];
        } else {
          formula.innerHTML = '<strong>1 ' + unitLabel(f) + ' = ' + fmtConv(convert(cat, f, t, 1)) + ' ' + unitLabel(t) + '</strong>';
        }
      }
    }
    function unitLabel(id) {
      var us = U[cat].units;
      for (var i = 0; i < us.length; i++) if (us[i].id === id) { var m = us[i].name.match(/\(([^)]+)\)/); return m ? m[1] : us[i].name; }
      return id;
    }

    setCat(cat, form.getAttribute('data-from'), form.getAttribute('data-to'));
    if (catSel) catSel.addEventListener('change', function () { setCat(catSel.value); update(); });
    val.addEventListener('input', update);
    from.addEventListener('change', update);
    to.addEventListener('change', update);
    if (swap) swap.addEventListener('click', function () { var f = from.value; from.value = to.value; to.value = f; update(); });
    form.addEventListener('submit', function (e) { e.preventDefault(); });
    update();
  }

  function initSearch() {
    var box = document.getElementById('tool-search');
    if (!box) return;
    var items = document.querySelectorAll('[data-k]');
    var sections = document.querySelectorAll('.section[data-section]');
    var none = document.querySelector('.no-results');
    box.addEventListener('input', function () {
      var q = box.value.trim().toLowerCase(), shown = 0;
      items.forEach(function (li) {
        var hit = !q || li.getAttribute('data-k').indexOf(q) !== -1;
        li.style.display = hit ? '' : 'none';
        if (hit) shown++;
      });
      sections.forEach(function (s) {
        var any = Array.prototype.some.call(s.querySelectorAll('[data-k]'), function (li) { return li.style.display !== 'none'; });
        s.style.display = any ? '' : 'none';
      });
      if (none) none.style.display = shown ? 'none' : 'block';
    });
  }

  if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function () {
      document.querySelectorAll('form[data-calc]').forEach(initCalc);
      document.querySelectorAll('form[data-conv]').forEach(initConv);
      initSearch();
    });
  }

  root.MoneyMath = { CALCS: CALCS, convert: convert, fmtConv: fmtConv };
})(typeof window !== 'undefined' ? window : globalThis);
