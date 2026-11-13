"""Run the production report queries against deterministic, offline relational data."""
import json
from copy import deepcopy
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from app.services import hide_service, report_service, settings_service

FIXTURE_PATH = Path(__file__).parent / 'fixtures' / 'report_cases.json'
SCHEMA = """
CREATE TABLE invoicebase (
 id INTEGER, invoicenumber TEXT, name TEXT, grandtotal REAL, ordereddate TIMESTAMP,
 wanteddate TIMESTAMP, offpendingdate TIMESTAMP, pickupdate TIMESTAMP,
 locationchangedate TIMESTAMP, account_id INTEGER, contact_id INTEGER,
 documentlocation_id INTEGER, holdstate_id INTEGER, isdeleted BOOLEAN DEFAULT false,
 voided BOOLEAN DEFAULT false, onpendinglist BOOLEAN DEFAULT false,
 readytopickup BOOLEAN DEFAULT false
);
CREATE TABLE invoice (id INTEGER);
CREATE TABLE account (id INTEGER, title TEXT);
CREATE TABLE contact (id INTEGER);
CREATE TABLE party (id INTEGER, firstname TEXT, lastname TEXT);
CREATE TABLE productionlocations (id INTEGER, name TEXT);
CREATE TABLE holdstate (id INTEGER, name TEXT, isdeleted BOOLEAN DEFAULT false);
CREATE TABLE accounthistorydata (
 id INTEGER, invoicenumber TEXT, name TEXT, recordtype TEXT, total REAL,
 posteddate TIMESTAMP, finalpaypaymethod TEXT, partialpaypaymethod TEXT,
 finalpaytotal REAL, partialpaytotal REAL, isdeleted BOOLEAN DEFAULT false
);
CREATE TABLE tapedepositrecord (
 id INTEGER, invoicenumber TEXT, paymode TEXT, isdeposittake BOOLEAN DEFAULT false,
 isdepositreturned BOOLEAN DEFAULT false, isdeleted BOOLEAN DEFAULT false
);
CREATE TABLE tapeinvoicepayrecord (
 invoicenumber TEXT, totalpay REAL, isdeleted BOOLEAN DEFAULT false
);
CREATE TABLE tapedepositappliedrecord (
 invoicenumber TEXT, totaldeposits REAL, isdeleted BOOLEAN DEFAULT false
);
CREATE TABLE tapesalerecord (
 invoicenumber TEXT, amountpaid REAL, paymode TEXT, isdeleted BOOLEAN DEFAULT false
);
"""


class ReportConnection:
    """Adapt PostgreSQL syntax only; SQLite executes all filtering and joins."""

    def __init__(self, database):
        self.database = database

    def cursor(self, **kwargs):
        return ReportCursor(self.database.cursor())

    def close(self):
        pass  # The fixture context owns the shared in-memory database.


class ReportCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, sql, params=()):
        lateral = re.search(r'LEFT JOIN LATERAL \((.*?)\) tdr ON true', sql, re.S)
        if lateral:
            sql = sql[:lateral.start()] + sql[lateral.end():]
            sql = sql.replace('tdr.paymode', '(' + lateral.group(1) + ')')
        sql = re.sub(r'SELECT SUM\((\w+)\) FROM', r'SELECT SUM(\1) AS sum FROM', sql)
        params = tuple(value.isoformat() if isinstance(value, date) else value for value in params)
        self.cursor.execute(sql.replace('%s', '?'), params)

    def fetchall(self):
        return [dict(row) for row in self.cursor.fetchall()]

    def fetchone(self):
        row = self.cursor.fetchone()
        return dict(row) if row is not None else None

    def close(self):
        self.cursor.close()


def report_snapshot(report):
    """Stable public values used by both regression and release comparison."""
    return {
        'paid': {
            row['invoicenumber']: {
                'amount': f"{row['grandtotal']:.2f}",
                'invoice_total': f"{row['invoice_total']:.2f}",
                'type': row['transaction_type'],
                'method': row['pay_method_display'],
                'balance': f"{row['current_balance']:.2f}",
                'partial': row['is_partial'],
            }
            for row in report['paid']
        },
        **{
            key: sorted(row['invoicenumber'] for row in report[key])
            for key in ('new_today', 'in_progress', 'ready', 'picked_up')
        },
    }


@contextmanager
def fixture_reports(fixture, settings=None):
    sqlite3.register_converter('TIMESTAMP', lambda value: datetime.fromisoformat(value.decode()))
    database = sqlite3.connect(':memory:', detect_types=sqlite3.PARSE_DECLTYPES)
    database.row_factory = sqlite3.Row
    database.create_function('CONCAT', -1, lambda *values: ''.join(str(v) for v in values if v is not None))
    database.executescript(SCHEMA)
    for table, rows in fixture['tables'].items():
        for row in rows:
            columns = ','.join(row)
            placeholders = ','.join('?' for _ in row)
            database.execute(f'INSERT INTO {table} ({columns}) VALUES ({placeholders})', tuple(row.values()))
    try:
        with tempfile.TemporaryDirectory() as directory:
            hidden = Path(directory) / 'hidden.json'
            hidden.write_text(json.dumps(fixture['hidden']))
            settings_path = Path(directory) / 'settings.json'
            if settings is not None:
                settings_path.write_text(json.dumps(settings))
            with patch.object(report_service, 'get_conn', lambda: ReportConnection(database)), \
                 patch.object(hide_service, 'HIDDEN_FILE', str(hidden)), \
                 patch.object(settings_service, 'SETTINGS_FILE', str(settings_path)):
                yield report_service.get_report_data
    finally:
        database.close()


class TestReportRegressions(unittest.TestCase):
    def test_estimates_cannot_change_invoice_report_values(self):
        fixture = json.loads(FIXTURE_PATH.read_text())
        without_estimates = deepcopy(fixture)
        invoice_ids = {row['id'] for row in fixture['tables']['invoice']}
        without_estimates['tables']['invoicebase'] = [
            row for row in fixture['tables']['invoicebase'] if row['id'] in invoice_ids
        ]
        with fixture_reports(fixture, fixture['settings']) as get_report:
            expected = {
                case['date']: report_snapshot(get_report(date.fromisoformat(case['date'])))
                for case in fixture['cases']
            }
        with fixture_reports(without_estimates, fixture['settings']) as get_report:
            for day, snapshot in expected.items():
                with self.subTest(day=day):
                    self.assertEqual(report_snapshot(get_report(date.fromisoformat(day))), snapshot)

    def test_accounting_and_classification_snapshots(self):
        fixture = json.loads(FIXTURE_PATH.read_text())
        with fixture_reports(fixture, fixture['settings']) as get_report:
            for case in fixture['cases']:
                with self.subTest(case=case['name']):
                    self.assertEqual(report_snapshot(get_report(date.fromisoformat(case['date']))), case['expected'])

    def test_subsidiary_exclusions_survive_missing_and_stale_settings(self):
        fixture = json.loads(FIXTURE_PATH.read_text())
        for settings in (None, {'excluded_paid_accounts': []}, fixture['settings']):
            with self.subTest(settings=settings), fixture_reports(fixture, settings) as get_report:
                paid = {row['invoicenumber'] for row in get_report(date(2026, 8, 2))['paid']}
                self.assertTrue(paid.isdisjoint({'810', '811', '812'}))
                self.assertEqual('813' in paid, settings != fixture['settings'])


if __name__ == '__main__':
    unittest.main()
