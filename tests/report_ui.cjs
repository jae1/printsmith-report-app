// Run with Playwright available to Node: node tests/report_ui.cjs
// All requests are intercepted; no database, mail, or runtime state is touched.
const assert = require('node:assert/strict');
const { readFileSync, mkdtempSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const { chromium } = require('playwright');

const template = readFileSync(join(__dirname, '../app/templates/index.html'), 'utf8');
const invoice = (number, amount) => ({
  invoicenumber: number, grandtotal: amount,
  account_display: 'Seattle Neighborhood Arts and Community Printing Association',
  contact_display: 'Morgan Lee', job_name: 'Full color event programs — folded, trimmed, and packed for delivery',
  ordereddate: '2026-10-28', wanteddate: '2026-10-30', pickupdate: '2026-10-29', status: 'Printing',
});
const data = {
  date: '2026-10-30',
  new_today: [{ ...invoice('60002', 250), is_partial: true, current_balance: 25 }, invoice('60001', 100)],
  in_progress: [{ ...invoice('10000', 500), wanteddate: '2026-10-29' }, { ...invoice('9999', 100), wanteddate: null }], ready: [invoice('59800', 300)],
  picked_up: [invoice('59700', 400)],
  paid: [{ ...invoice('59600', 75), transaction_type: 'AR PAYMENT', is_partial: true,
    current_balance: 125, invoice_total: 999, pay_method_display: 'Credit Card' }],
};

// Prior-workday Paid Today totals for the chart; 10/24-25 is a weekend (10/29 has no money).
const history = { '2026-10-22': 1200, '2026-10-23': 300, '2026-10-26': 2400, '2026-10-27': 600, '2026-10-28': 450, '2026-10-29': 0 };

(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  const artifacts = mkdtempSync(join(tmpdir(), 'printsmith-ui-'));
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
    const errors = [], requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('dialog', dialog => dialog.accept());
    const handleRoute = route => {
      const request = route.request(), url = new URL(request.url());
      requests.push({ path: url.pathname + url.search, method: request.method(), body: request.postDataJSON() });
      if (url.pathname === '/') return route.fulfill({ contentType: 'text/html', body: template });
      if (url.pathname === '/logo.png') return route.fulfill({ path: join(__dirname, '../app/static/email-logo.png') });
      let body = {};
      const day = url.searchParams.get('target_date');
      if (url.pathname === '/api/report') body = history[day] === undefined ? data
        : { ...data, date: day, paid: [{ grandtotal: history[day], invoice_total: 99999 }] };
      if (url.pathname === '/api/settings') body = { boss_emails: [], auto_send_days: [], report_title_prefix: 'Overnight', auto_send_enabled: false };
      if (url.pathname === '/api/spending') body = [{ id: 'sample', vendor: 'Paper Shop', description: 'Stock', card: '1234', amount: 25.5 }];
      if (url.pathname === '/api/vendors') body = ['Paper Shop'];
      if (url.pathname === '/api/hidden') body = [invoice('59000', 42)];
      return route.fulfill({ json: body });
    };
    await page.route('https://printsmith.test/**', handleRoute);
    await page.goto('https://printsmith.test/');
    await page.locator('#report tbody tr').first().waitFor();
    await page.locator('#spendingTableContainer .spend-row').waitFor();
    await page.waitForFunction(() => document.querySelectorAll('#trendChart li').length === 7
      && !document.querySelector('#trendChart li[title$="loading"]'));
    assert.ok(await page.locator('.brand-logo').evaluate(img => img.complete && img.naturalWidth > 0));
    assert.deepEqual(await page.locator('.trend-amount').allTextContents(), ['$1.2k', '$300', '$2.4k', '$600', '$450', '$0', '$75']);
    assert.deepEqual(await page.locator('.trend-day').allTextContents(), ['Thu10/22', 'Fri10/23', 'Mon10/26', 'Tue10/27', 'Wed10/28', 'Thu10/29', 'Fri10/30']);
    assert.deepEqual(await page.locator('.trend-bar').evaluateAll(els => els.map(el => el.style.getPropertyValue('--h'))),
      ['46px', '12px', '92px', '23px', '17px', '0px', '3px']);
    assert.equal(await page.locator('.trend li.current').getAttribute('title'), 'Fri 10/30 · $75.00');
    assert.equal(await page.locator('.trend li.zero').count(), 1);
    assert.deepEqual(await page.locator('.jobs-legend strong').allTextContents(), ['2', '2', '1', '1']);
    assert.deepEqual(await page.locator('.jobs-bar span').evaluateAll(els => els.map(el => el.style.flexGrow)), ['2', '2', '1', '1']);
    assert.equal(requests.filter(r => r.path.startsWith('/api/report?target_date=2026-10-2')).length, 6);
    assert.ok(!requests.some(r => /target_date=2026-10-2[45]/.test(r.path)), 'weekend days are not loaded');
    await page.locator('.trend-btn[data-date="2026-10-26"]').click();
    await page.waitForFunction(() => document.querySelector('#trendChart .current .trend-btn')?.dataset.date === '2026-10-26');
    assert.equal(await page.locator('#dateInput').inputValue(), '2026-10-26');
    assert.equal(await page.locator('#summaryCollected').innerText(), '$2,400.00');
    assert.equal(await page.locator('.trend-btn[aria-current="date"]').getAttribute('data-date'), '2026-10-26');
    assert.deepEqual(await page.locator('.trend-btn').evaluateAll(els => els.map(el => el.dataset.date)),
      ['2026-10-16', '2026-10-19', '2026-10-20', '2026-10-21', '2026-10-22', '2026-10-23', '2026-10-26']);
    await page.locator('.trend-btn[data-date="2026-10-23"]').focus();
    await page.keyboard.press('Enter');
    await page.waitForFunction(() => document.querySelector('#trendChart .current .trend-btn')?.dataset.date === '2026-10-23');
    assert.equal(await page.locator('#summaryCollected').innerText(), '$300.00');
    assert.equal(await page.getByRole('button', { name: 'Load Report' }).count(), 0);
    await Promise.all([
      page.waitForRequest(request => request.url().endsWith('/api/report?target_date=2026-10-27')),
      page.locator('#dateInput').fill('2026-10-27'),
    ]);
    await page.waitForFunction(() => reportData.date === '2026-10-27' && !document.querySelector('#overview').hidden);
    const reportCalls = requests.length;
    await page.locator('#dateInput').fill('');
    await page.locator('#dateInput').evaluate(el => { el.value = '0002-10-27'; el.dispatchEvent(new Event('change')); });
    assert.equal(requests.filter((r, index) => index >= reportCalls && r.path.startsWith('/api/report')).length, 0);
    await page.getByRole('button', { name: 'Today', exact: true }).click();
    assert.equal(await page.locator('#dateInput').inputValue(), await page.evaluate(() => new Date().toLocaleDateString('en-CA')));
    await page.waitForFunction(() => reportData.date === '2026-10-30' && !document.querySelector('#overview').hidden);
    assert.equal(await page.locator('#tableViewBtn').getAttribute('aria-pressed'), 'true');
    assert.equal(await page.locator('#report tbody tr').count(), 7);
    assert.equal(await page.locator('#summaryCollected').innerText(), '$75.00');
    assert.equal(await page.locator('#summaryOrders').innerText(), '2');
    assert.equal(await page.locator('#summaryOrderValue').innerText(), '$350.00 order value');
    assert.equal(await page.locator('#summaryStuck').innerText(), '0');
    assert.equal(await page.locator('#summaryOldest').innerText(), 'Oldest 2 days · since 10/28');
    assert.equal(await page.locator('#summaryReady').innerText(), '1');
    assert.equal(await page.locator('#summaryWaiting').innerText(), '0 waiting 5+ days');
    assert.deepEqual(await page.locator('.in_progress .age-badge').allTextContents(), ['2 days', '2 days']);
    assert.equal(await page.locator('.new_today .age-badge, .picked_up .age-badge').count(), 0);
    await page.locator('#hiddenNote:visible').waitFor();
    assert.match(await page.locator('#hiddenNote').innerText(), /^1 invoice hidden, not in totals · View$/);
    const overviewBefore = await page.locator('#overview').innerText();
    const rowsBefore = await page.locator('#report tbody tr').allTextContents();
    const totalsBefore = await page.locator('#report tfoot').allTextContents();
    await page.locator('.chk-new_today').first().check();
    const reportRequestsBefore = requests.filter(r => r.path.startsWith('/api/report')).length;
    await page.getByRole('button', { name: 'Board', exact: true }).click();
    assert.equal(await page.locator('#overview').innerText(), overviewBefore);
    assert.deepEqual((await page.locator('#report tbody tr').allTextContents()).sort(), [...rowsBefore].sort());
    assert.deepEqual(await page.locator('#report tfoot').allTextContents(), totalsBefore);
    for (const row of await page.locator('#report .section:not(.paid) tbody tr').all()) {
      assert.deepEqual(await row.locator('td[data-label]:visible').evaluateAll(cells => cells.map(cell => cell.dataset.label)),
        ['Invoice #', 'Account', 'Job Description']);
    }
    assert.equal(await page.locator('.new_today .badge-type:visible, .new_today .badge-bal:visible').count(), 0);
    assert.equal(await page.locator('.new_today th button:visible').count(), 0);
    assert.deepEqual(await page.locator('.chk-new_today').evaluateAll(els => els.map(el => el.value)), ['60001', '60002']);
    assert.deepEqual(await page.locator('.chk-in_progress').evaluateAll(els => els.map(el => el.value)), ['9999', '10000']);
    assert.equal(await page.locator('.chk-new_today:checked').inputValue(), '60002');
    assert.ok(await page.locator('.new_today tbody tr').first().evaluate(el => el.getBoundingClientRect().height < 180));
    assert.equal(await page.locator('.chk-new_today:checked').count(), 1);
    assert.equal(requests.filter(r => r.path.startsWith('/api/report')).length, reportRequestsBefore);
    assert.equal(await page.locator('#report').evaluate(el => getComputedStyle(el).gridTemplateColumns.split(' ').length), 4);
    assert.equal(await page.locator('.paid').evaluate(el => getComputedStyle(el).gridColumn), '1 / -1');
    assert.match(await page.locator('.paid').innerText(), /AR PAYMENT[\s\S]*PARTIAL[\s\S]*BAL DUE: \$125\.00/);
    await page.screenshot({ path: join(artifacts, 'board-desktop.png'), fullPage: true });

    // Summary uses the report date, ordered-date ages, and actual new money.
    const summaryInput = await page.evaluate(() => {
      const base = { ...reportData.new_today[0], grandtotal: 10, is_partial: false };
      const job = (number, ordered) => ({ ...base, invoicenumber: number, ordereddate: ordered });
      reportData = {
        date: '2026-10-27',
        new_today: [job('10', '2026-10-27'), job('20', '2026-10-27')],
        in_progress: [job('60', '2026-10-20T09:30:00'), job('61', '2026-10-21'), job('62', '2026-10-26'), job('63', null), job('64', 'not a date'), { ...job('65', '2026-10-01'), hold_name: 'Credit Hold' }],
        ready: [job('50', '2026-10-22'), job('51', '2026-10-23'), job('52', '2026-10-26')], picked_up: [job('70', '2026-10-01')],
        paid: [{ ...job('10', null), grandtotal: 12.5, invoice_total: 999, current_balance: 900 }],
      };
      const input = JSON.stringify(reportData);
      renderReport();
      return input;
    });
    assert.equal(await page.evaluate(() => JSON.stringify(reportData)), summaryInput);
    assert.equal(await page.locator('#overview time').innerText(), '2026-10-27');
    assert.equal(await page.locator('#summaryCollected').innerText(), '$12.50');
    assert.equal(await page.locator('#summaryOrderValue').innerText(), '$20.00 order value');
    assert.equal(await page.locator('#summaryStuck').innerText(), '1');
    assert.equal(await page.locator('#summaryOldest').innerText(), 'Oldest 7 days · since 10/20 · 1 on hold');
    assert.deepEqual(await page.locator('.in_progress .badge-hold:visible').allTextContents(), ['Credit Hold']);
    assert.equal(await page.locator('#summaryWaiting').innerText(), '1 waiting 5+ days');
    assert.deepEqual(await page.locator('.in_progress .age-badge').allTextContents(), ['7 days', '6 days', '1 day', '26 days']);
    assert.deepEqual(await page.locator('.in_progress .age-old, .ready .age-old').allTextContents(), ['7 days', '5 days']);
    assert.equal(await page.locator('.due-bar, .due-legend, #summaryAttention').count(), 0);
    await page.evaluate(() => { reportData.date = '2026-10-28'; renderReport(); });
    assert.equal(await page.locator('#summaryStuck').innerText(), '2');
    assert.equal(await page.locator('#summaryWaiting').innerText(), '2 waiting 5+ days');
    assert.equal(await page.evaluate(() => { loadReport(); return document.getElementById('overview').hidden; }), true);

    // Board stays oldest first; switching back restores Table sorting and keyboard controls.
    await page.reload();
    await page.locator('#report tbody tr').first().waitFor();
    assert.equal(await page.locator('#boardViewBtn').getAttribute('aria-pressed'), 'true');
    for (const mode of ['Table', 'Board']) {
      await page.getByRole('button', { name: mode, exact: true }).click();
      if (mode === 'Table') {
        assert.equal(await page.locator('.new_today tbody tr').first().locator('td[data-label]:visible').count(), 7);
        assert.equal(await page.locator('.new_today .badge-bal:visible').count(), 1);
        const sort = page.locator('.new_today th button').filter({ hasText: 'Invoice #' });
        await sort.focus(); await page.keyboard.press('Enter');
      }
      const expected = mode === 'Table' ? ['60002', '60001'] : ['60001', '60002'];
      assert.deepEqual(await page.locator('.chk-new_today').evaluateAll(els => els.map(el => el.value)), expected);
      const collapse = page.locator('.new_today .section-toggle');
      await collapse.focus(); await page.keyboard.press('Space');
      assert.equal(await collapse.getAttribute('aria-expanded'), 'false');
      assert.equal(await page.locator('.new_today table').isVisible(), false);
      await page.keyboard.press('Enter');
      assert.equal(await collapse.getAttribute('aria-expanded'), 'true');
    }
    await page.getByRole('button', { name: 'Table', exact: true }).click();
    assert.deepEqual(await page.locator('.chk-new_today').evaluateAll(els => els.map(el => el.value)), ['60002', '60001']);
    await page.getByRole('button', { name: 'Board', exact: true }).click();
    await Promise.all([
      page.waitForResponse(response => new URL(response.url()).pathname === '/api/report'),
      page.getByRole('button', { name: 'Refresh', exact: true }).click(),
    ]);
    await page.waitForFunction(() => document.querySelector('.chk-new_today').value === '60001');
    await page.locator('.new_today .selection-heading input').check();
    await page.locator('#btnHide-new_today').click();
    await page.waitForFunction(() => document.querySelectorAll('.new_today tbody tr').length === 2);
    assert.deepEqual(requests.find(r => r.path === '/api/hide-batch').body, {
      invoice_numbers: ['60001', '60002'], target_date: await page.locator('#dateInput').inputValue(),
    });
    await page.locator('.ready .btn-hide').click();
    await page.waitForFunction(() => document.querySelector('.ready table'));
    assert.ok(requests.some(r => r.method === 'POST' && r.path === '/api/hide/59800?target_date=' + new Date().toLocaleDateString('en-CA')));

    // Both views fit the document; wide tables scroll inside their own containers.
    for (const width of [375, 768, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      for (const mode of ['Table', 'Board']) {
        await page.getByRole('button', { name: mode, exact: true }).click();
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${mode} overflows at ${width}px`);
        if (width === 1440 && mode === 'Table') await page.screenshot({ path: join(artifacts, 'table-desktop.png'), fullPage: true });
      }
    }
    await page.setViewportSize({ width: 375, height: 900 });
    await page.screenshot({ path: join(artifacts, 'board-mobile.png'), fullPage: true });
    await page.getByRole('button', { name: 'Settings', exact: true }).click();
    assert.ok(await page.locator('.modal-content').evaluate(el => el.getBoundingClientRect().right <= innerWidth));
    await page.keyboard.press('Shift+Tab');
    assert.equal(await page.evaluate(() => document.activeElement.textContent.trim()), 'Save');
    await page.keyboard.press('Tab');
    assert.equal(await page.locator('.close-modal').evaluate(el => el === document.activeElement), true);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('.btn-settings').evaluate(el => el === document.activeElement), true);
    assert.equal(await page.locator('.spend-row .actions').evaluate(el => getComputedStyle(el).opacity), '1');

    // Print restores expanded tables and removes all report interaction controls.
    await page.setViewportSize({ width: 1440, height: 1100 });
    await page.locator('.new_today .section-toggle').click();
    await page.locator('#spendingSection .section-toggle').click();
    await page.locator('#hiddenSection .section-toggle').click();
    await page.emulateMedia({ media: 'print' });
    assert.equal(await page.locator('.new_today table').isVisible(), true);
    assert.equal(await page.locator('.new_today table').evaluate(el => getComputedStyle(el).display), 'table');
    assert.equal(await page.locator('.new_today tbody td[data-label]').first().evaluate(el => getComputedStyle(el).display), 'table-cell');
    assert.equal(await page.locator('.controls').isVisible(), false);
    assert.equal(await page.locator('#report input:visible').count(), 0);
    assert.equal(await page.locator('.btn-hide:visible').count(), 0);
    assert.equal(await page.locator('.new_today th button:visible').count(), 7);
    assert.equal(await page.locator('.new_today tbody tr').first().locator('td[data-label]:visible').count(), 7);
    assert.equal(await page.locator('.new_today .badge-bal:visible').count(), 1);
    assert.ok(await page.locator('.new_today .date-cell').first().evaluate(el => el.getBoundingClientRect().width < el.closest('table').getBoundingClientRect().width / 3));
    assert.equal(await page.locator('.spending-input-row').isVisible(), false);
    assert.equal(await page.locator('#spendingTableContainer table').isVisible(), true);
    assert.equal(await page.locator('#hiddenTableContainer table').isVisible(), true);
    assert.match(await page.locator('#printDate').innerText(), /Report date:/);
    assert.equal(await page.locator('#overview').isVisible(), true);
    assert.equal(await page.locator('#summaryCollected').innerText(), '$75.00');
    assert.equal(await page.locator('.chart-card:visible').count(), 2);
    assert.equal(await page.locator('.brand-logo').isVisible(), true);
    assert.ok(await page.locator('#report .table-scroll').evaluateAll(els => els.every(el => getComputedStyle(el).overflowX === 'visible')));
    await page.pdf({ path: join(artifacts, 'report.pdf'), format: 'A4', landscape: true, printBackground: true });
    await page.screenshot({ path: join(artifacts, 'print.png'), fullPage: true });
    await page.emulateMedia({ media: 'screen' });
    await page.getByRole('button', { name: 'Table', exact: true }).click();
    await page.emulateMedia({ media: 'print' });
    assert.equal(await page.locator('.new_today table').isVisible(), true);
    assert.equal(await page.locator('.new_today th button:visible').count(), 7);
    assert.equal(await page.locator('.spending-input-row').isVisible(), false);
    await page.emulateMedia({ media: 'screen' });

    // Long desktop columns scroll independently, with headings and finances outside.
    await page.getByRole('button', { name: 'Board', exact: true }).click();
    await page.evaluate(() => {
      reportData.in_progress = Array.from({ length: 30 }, (_, index) => ({
        ...reportData.in_progress[0], invoicenumber: String(20000 + index),
      }));
      renderReport();
    });
    const lane = page.locator('.in_progress .table-scroll');
    assert.ok(await lane.evaluate(el => el.scrollHeight > el.clientHeight));
    assert.ok(await page.locator('#report').evaluate(el => el.getBoundingClientRect().top < 400));
    assert.ok(await page.locator('.paid').evaluate(el => el.getBoundingClientRect().top < innerHeight));
    const headingTop = await page.locator('.in_progress h2').evaluate(el => el.getBoundingClientRect().top);
    await lane.focus();
    await page.keyboard.press('End');
    await page.waitForFunction(() => document.querySelector('.in_progress .table-scroll').scrollTop > 0);
    assert.equal(await page.locator('.in_progress h2').evaluate(el => el.getBoundingClientRect().top), headingTop);
    const scrollTop = await lane.evaluate(el => el.scrollTop);
    await page.evaluate(() => renderReport());
    assert.equal(await lane.evaluate(el => el.scrollTop), scrollTop);
    await lane.evaluate(el => el.scrollTop = 0);
    await page.screenshot({ path: join(artifacts, 'board-scroll-desktop.png'), fullPage: true });
    for (const width of [768, 375]) {
      await page.setViewportSize({ width, height: 900 });
      assert.equal(await lane.evaluate(el => getComputedStyle(el).maxHeight), 'none');
      assert.equal(await lane.evaluate(el => el.scrollHeight > el.clientHeight), false);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    }
    await page.setViewportSize({ width: 1440, height: 1100 });
    await page.emulateMedia({ media: 'print' });
    assert.equal(await lane.evaluate(el => getComputedStyle(el).maxHeight), 'none');
    assert.equal(await page.locator('.in_progress tbody tr:visible').count(), 30);
    assert.equal(await lane.evaluate(el => el.scrollHeight > el.clientHeight), false);
    await page.emulateMedia({ media: 'screen' });

    // Returning to Table removes the Board height cap as well.
    await page.getByRole('button', { name: 'Table', exact: true }).click();
    assert.equal(await lane.evaluate(el => getComputedStyle(el).maxHeight), 'none');

    // Empty groups and unavailable browser storage must still load in default Table mode.
    await page.evaluate(() => { reportData = { date: '2026-10-30', new_today: [], in_progress: [], ready: [], picked_up: [], paid: [] }; renderReport(); });
    assert.equal(await page.locator('#report .empty').count(), 5);
    assert.equal(await page.locator('#summaryCollected').innerText(), '$0.00');
    assert.equal(await page.locator('#summaryOrders').innerText(), '0');
    assert.equal(await page.locator('#summaryStuck').innerText(), '0');
    assert.equal(await page.locator('#summaryOldest').innerText(), 'No jobs in progress');
    assert.equal(await page.locator('#summaryReady').innerText(), '0');
    assert.equal(await page.locator('.jobs-bar span').count(), 0);
    assert.deepEqual(await page.locator('.jobs-legend strong').allTextContents(), ['0', '0', '0', '0']);
    const blockedStorage = await browser.newPage();
    blockedStorage.on('pageerror', error => errors.push(error.message));
    await blockedStorage.route('https://printsmith.test/**', handleRoute);
    await blockedStorage.addInitScript(() => { Storage.prototype.getItem = Storage.prototype.setItem = () => { throw Error('Storage disabled'); }; });
    await blockedStorage.goto('https://printsmith.test/');
    await blockedStorage.locator('#report tbody tr').first().waitFor();
    assert.equal(await blockedStorage.locator('#tableViewBtn').getAttribute('aria-pressed'), 'true');
    await blockedStorage.getByRole('button', { name: 'Board', exact: true }).click();
    assert.equal(await blockedStorage.locator('#boardViewBtn').getAttribute('aria-pressed'), 'true');
    assert.deepEqual(errors, []);
    console.log(`UI checks passed. Screenshots and print PDF: ${artifacts}`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
