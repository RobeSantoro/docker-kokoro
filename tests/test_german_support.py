import os
import unittest
from unittest.mock import patch

import api_server


class GermanSupportTests(unittest.TestCase):
    def setUp(self):
        api_server._pipelines.clear()

    def tearDown(self):
        api_server._pipelines.clear()

    def test_german_voice_is_public_and_pinned(self):
        self.assertEqual(api_server._resolve_voice("DM_MARTIN"), "dm_martin")
        spec = api_server._GERMAN_VOICE_MODELS["dm_martin"]
        self.assertEqual(spec["repo_id"], "kikiri-tts/kikiri-german-martin")
        self.assertEqual(len(spec["revision"]), 40)
        self.assertEqual(spec["voice_filename"], "voices/martin.pt")
        self.assertEqual(len(api_server._BASE_MODEL_REVISION), 40)

    @patch("api_server._get_or_create_pipeline")
    def test_german_pipeline_is_cached_by_voice(self, get_or_create):
        get_or_create.return_value = object()
        api_server._get_pipeline("dm_martin")
        get_or_create.assert_called_once_with("voice:dm_martin", "d", "dm_martin")

    @patch("api_server._get_or_create_pipeline")
    def test_standard_pipeline_remains_cached_by_language(self, get_or_create):
        get_or_create.return_value = object()
        api_server._get_pipeline("af_heart")
        get_or_create.assert_called_once_with("a", "a")

    @patch("api_server._get_pipeline")
    def test_german_lang_preloads_martin(self, get_pipeline):
        with patch.dict(
            os.environ,
            {"KOKORO_LANG_CODE": "d", "KOKORO_VOICE": "af_heart"},
            clear=False,
        ):
            api_server._load_model()
        get_pipeline.assert_called_once_with("dm_martin")


if __name__ == "__main__":
    unittest.main()
