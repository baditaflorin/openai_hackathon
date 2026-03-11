import unittest

from clipmato.utils.local_ai import describe_transcript_basic


class DescribeTranscriptBasicTests(unittest.TestCase):
    def test_fallback_description_summarizes_instead_of_copying_opening_sentence(self) -> None:
        transcript = (
            "Consider că este un manifest de solidaritate cu colegii și un apel pentru sprijin public. "
            "Discuția insistă asupra magistratilor, solidarității și nevoii de suport instituțional. "
            "Vorbește și despre presiune publică, semnături și mobilizare."
        )

        result = describe_transcript_basic(transcript)

        self.assertNotEqual(result["short_description"], transcript.split(".")[0].strip() + ".")
        self.assertTrue(result["short_description"].startswith("This clip focuses on"))
        self.assertIn("summary was generated from the transcript fallback path", result["long_description"])
        self.assertNotIn("Consider că este un manifest", result["long_description"])


if __name__ == "__main__":
    unittest.main()
