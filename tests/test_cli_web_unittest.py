import os
import unittest
from unittest.mock import patch

from clipmato.cli.web import _apply_runtime_env, build_parser


class ClipmatoWebCliTests(unittest.TestCase):
    def test_host_native_launch_sets_whisper_and_ollama_runtime(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "--host-native",
                "--whisper-model",
                "medium",
                "--whisper-device",
                "mps",
                "--ollama-model",
                "mistral-nemo:12b-instruct-2407-q3_K_S",
            ]
        )

        with patch.dict(os.environ, {}, clear=True):
            _apply_runtime_env(args)
            self.assertEqual(os.environ["CLIPMATO_HOST"], "127.0.0.1")
            self.assertEqual(os.environ["CLIPMATO_TRANSCRIPTION_BACKEND"], "local-whisper")
            self.assertEqual(os.environ["CLIPMATO_CONTENT_BACKEND"], "ollama")
            self.assertEqual(os.environ["CLIPMATO_LOCAL_WHISPER_MODEL"], "medium")
            self.assertEqual(os.environ["CLIPMATO_LOCAL_WHISPER_DEVICE"], "mps")
            self.assertEqual(os.environ["CLIPMATO_OLLAMA_MODEL"], "mistral-nemo:12b-instruct-2407-q3_K_S")

    def test_explicit_host_overrides_host_native_default(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--host-native", "--host", "0.0.0.0"])

        with patch.dict(os.environ, {}, clear=True):
            _apply_runtime_env(args)
            self.assertEqual(os.environ["CLIPMATO_HOST"], "0.0.0.0")


if __name__ == "__main__":
    unittest.main()
