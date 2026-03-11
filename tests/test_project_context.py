from __future__ import annotations

import unittest

from clipmato.utils.project_context import (
    build_project_helper_text,
    build_project_prompt_variables,
    compose_prompt_variables,
    normalize_project_context,
)


class ProjectContextTests(unittest.TestCase):
    def test_normalize_project_context_discards_blank_payload(self) -> None:
        self.assertIsNone(
            normalize_project_context(
                {
                    "project_name": " ",
                    "project_summary": "",
                    "project_topics": " , ",
                    "project_prompt_prefix": "",
                    "project_prompt_suffix": "",
                }
            )
        )

    def test_project_context_helpers_build_prompt_and_ui_text(self) -> None:
        project_context = normalize_project_context(
            {
                "project_name": "OpenStreetMap Deep Dives",
                "project_summary": "Contributor stories and mapping workflows.",
                "project_topics": "mapping, civic data, mapping",
                "project_prompt_prefix": "Keep the framing practical.",
                "project_prompt_suffix": "Close with a contributor takeaway.",
            }
        )

        variables = build_project_prompt_variables(project_context)
        merged = compose_prompt_variables({"transcript": "Source"}, project_context)
        helpers = build_project_helper_text(project_context)

        self.assertEqual(project_context["project_topics"], ["mapping", "civic data"])
        self.assertIn("Project context:", variables["project_context_block"])
        self.assertEqual(merged["transcript"], "Source")
        self.assertEqual(helpers["title_helper"], "OpenStreetMap Deep Dives | Contributor stories and mapping workflows.")
        self.assertIn("Topics: mapping, civic data", helpers["subtitle_helper"])


if __name__ == "__main__":
    unittest.main()
