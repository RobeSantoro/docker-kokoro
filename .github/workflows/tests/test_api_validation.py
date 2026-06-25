import importlib
import pathlib
import sys
import types
import unittest


class _HTTPException(Exception):
    def __init__(self, status_code, detail=None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class _FastAPI:
    def __init__(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        return lambda func: func

    def post(self, *args, **kwargs):
        return lambda func: func


class _BaseModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def _install_stubs():
    fastapi = types.ModuleType("fastapi")
    fastapi.Depends = lambda *args, **kwargs: None
    fastapi.FastAPI = _FastAPI
    fastapi.Header = lambda *args, **kwargs: None
    fastapi.HTTPException = _HTTPException
    sys.modules["fastapi"] = fastapi

    responses = types.ModuleType("fastapi.responses")
    responses.Response = object
    responses.StreamingResponse = object
    sys.modules["fastapi.responses"] = responses

    pydantic = types.ModuleType("pydantic")
    pydantic.BaseModel = _BaseModel
    pydantic.Field = lambda default=..., **kwargs: default
    sys.modules["pydantic"] = pydantic

    numpy = types.ModuleType("numpy")
    numpy.ndarray = object
    sys.modules["numpy"] = numpy

    for name in ("soundfile", "uvicorn"):
        sys.modules[name] = types.ModuleType(name)


_install_stubs()
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
api_server = importlib.import_module("api_server")


class VoiceValidationTests(unittest.TestCase):
    def test_resolves_native_voice(self):
        self.assertEqual(api_server._resolve_voice("af_heart"), "af_heart")

    def test_resolves_openai_aliases(self):
        self.assertEqual(api_server._resolve_voice("alloy"), "af_alloy")
        self.assertEqual(api_server._resolve_voice("ballad"), "bm_lewis")
        self.assertEqual(api_server._resolve_voice("marin"), "af_nicole")
        self.assertEqual(api_server._resolve_voice("cedar"), "am_adam")

    def test_normalizes_voice_case_and_whitespace(self):
        self.assertEqual(api_server._resolve_voice(" Alloy "), "af_alloy")
        self.assertEqual(api_server._resolve_voice(" AF_HEART "), "af_heart")

    def test_resolves_voice_reference_object(self):
        voice = api_server.VoiceReference(id="marin")
        self.assertEqual(api_server._resolve_voice(voice), "af_nicole")

    def test_resolves_normalized_voice_reference_object(self):
        voice = api_server.VoiceReference(id=" Ballad ")
        self.assertEqual(api_server._resolve_voice(voice), "bm_lewis")

    def test_resolves_voice_dict(self):
        self.assertEqual(api_server._resolve_voice({"id": "cedar"}), "am_adam")

    def test_unknown_voice_returns_400(self):
        with self.assertRaises(api_server.HTTPException) as ctx:
            api_server._resolve_voice("not_a_voice")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("/v1/voices", ctx.exception.detail)

    def test_empty_voice_returns_400(self):
        with self.assertRaises(api_server.HTTPException) as ctx:
            api_server._resolve_voice("  ")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_invalid_voice_object_returns_400(self):
        with self.assertRaises(api_server.HTTPException) as ctx:
            api_server._resolve_voice({"name": "alloy"})
        self.assertEqual(ctx.exception.status_code, 400)

    def test_all_aliases_target_existing_kokoro_voices(self):
        missing = [
            voice_id
            for voice_id in api_server._OPENAI_VOICE_MAP.values()
            if voice_id not in api_server.KOKORO_VOICES
        ]
        self.assertEqual(missing, [])


class AudioFormatTests(unittest.TestCase):
    def test_wav_streaming_header_shape(self):
        header = api_server._wav_streaming_header(sample_rate=24000)
        self.assertEqual(len(header), 44)
        self.assertEqual(header[0:4], b"RIFF")
        self.assertEqual(header[8:12], b"WAVE")
        self.assertEqual(header[12:16], b"fmt ")
        self.assertEqual(header[36:40], b"data")

    def test_wav_streaming_header_uses_unknown_sizes(self):
        header = api_server._wav_streaming_header(sample_rate=24000)
        self.assertEqual(int.from_bytes(header[4:8], "little"), 0xFFFFFFFF)
        self.assertEqual(int.from_bytes(header[40:44], "little"), 0xFFFFFFFF)


if __name__ == "__main__":
    unittest.main()
