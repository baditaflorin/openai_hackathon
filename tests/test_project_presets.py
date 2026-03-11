from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from clipmato.services.project_presets import ProjectPresetService


class ProjectPresetServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.service = ProjectPresetService(Path(self.tempdir.name) / "project_presets.json")

    def test_save_read_merge_and_delete_presets(self) -> None:
        osm = self.service.save_preset(
            {
                "label": "OpenStreetMap",
                "project_name": "OpenStreetMap Deep Dives",
                "project_summary": "Contributor workflows and map editing stories.",
                "project_topics": "mapping, civic data",
                "project_prompt_prefix": "Keep the framing practical.",
                "project_prompt_suffix": "End with a contributor takeaway.",
            }
        )
        geo = self.service.save_preset(
            {
                "label": "Geospatial AI",
                "project_name": "Geospatial AI",
                "project_summary": "Applied AI for maps and imagery.",
                "project_topics": ["imagery", "mapping"],
                "project_prompt_prefix": "Stay concrete.",
                "project_prompt_suffix": "Anchor the close in implementation detail.",
            }
        )

        presets = self.service.read_presets()
        self.assertEqual(len(presets), 2)
        self.assertEqual([preset["label"] for preset in presets], ["Geospatial AI", "OpenStreetMap"])

        merged = self.service.merge_context(
            [osm["id"], geo["id"]],
            {"project_topics": "open data, imagery", "project_summary": ""},
        )

        self.assertEqual(
            set(merged["project_name"].split(" + ")),
            {"OpenStreetMap Deep Dives", "Geospatial AI"},
        )
        self.assertEqual(set(merged["project_topics"]), {"mapping", "civic data", "imagery", "open data"})
        self.assertIn("Keep the framing practical.", merged["project_prompt_prefix"])
        self.assertIn("Anchor the close in implementation detail.", merged["project_prompt_suffix"])

        removed = self.service.delete_preset(osm["id"])
        self.assertEqual(removed["label"], "OpenStreetMap")
        self.assertEqual(len(self.service.read_presets()), 1)


if __name__ == "__main__":
    unittest.main()
