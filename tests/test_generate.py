from datetime import datetime, timezone
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from scripts.generate import dna, fetch, render, snake, text

ROOT = Path(__file__).resolve().parents[1]


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'assets/activity.json').read_text())

    def test_svg_panels_are_valid_and_self_contained(self):
        for panel in [*render(self.data).values(), snake(self.data)]:
            ET.fromstring(panel)
            self.assertNotIn('href=', panel)
            self.assertNotIn('<script', panel)

    def test_untrusted_text_is_escaped(self):
        self.assertIn('&lt;script&gt;&amp;', text(0, 0, '<script>&'))
        self.data['name'] = '<tag> & "name"'
        ET.fromstring(render(self.data)['header.svg'])

    def test_dna_targets_and_caps(self):
        self.data.update(commits=30, reviews=10, prs=5, issues=5, repositories=10)
        self.assertEqual([score for _, score in dna(self.data)], [50, 50, 50, 50, 100])

    def test_zero_activity(self):
        self.data.update(commits=0, reviews=0, prs=0, issues=0, repositories=0, active_days=0)
        self.assertIn('QUIET SIGNAL', render(self.data)['telemetry.svg'])
        self.assertEqual([s for _, s in dna(self.data)], [0]*5)

    def test_snake_cells_match_calendar(self):
        panel = snake(self.data)
        count = sum(len(w['contributionDays']) for w in self.data['calendar'])
        self.assertEqual(panel.count(' contributions</title>'), count)
        self.assertEqual(panel.count('<animateTransform'), 5)

    def test_missing_token_fails_instead_of_faking_data(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'no synthetic data'):
                fetch('test', datetime.now(timezone.utc))

    def test_graphql_errors_fail(self):
        with patch.dict('os.environ', {'GH_TOKEN': 'test'}), patch('urllib.request.urlopen') as request:
            request.return_value.__enter__.return_value.read.return_value = b'{"errors":[{"message":"denied"}]}'
            with self.assertRaisesRegex(RuntimeError, 'GraphQL failed'):
                fetch('test', datetime.now(timezone.utc))


if __name__ == '__main__':
    unittest.main()
