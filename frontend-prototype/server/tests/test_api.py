from __future__ import annotations

from collections.abc import AsyncIterator, Iterable

import httpx
import pytest
from fastapi.testclient import TestClient

from server.app import UpstreamAPIError, app, open_tts_stream, transcribe_audio


class FakeClient:
    async def aclose(self) -> None:
        return None


class FakeUpstreamResponse:
    def __init__(self, chunks: Iterable[bytes]) -> None:
        self._chunks = iter(chunks)

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk

    async def aclose(self) -> None:
        return None


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_get_voices_returns_static_list(client: TestClient) -> None:
    response = client.get('/api/voices')

    assert response.status_code == 200
    payload = response.json()
    assert 'voices' in payload
    assert isinstance(payload['voices'], list)
    assert payload['voices']
    assert all('voice_id' in voice and 'name' in voice for voice in payload['voices'])


def test_stt_missing_audio_returns_422(client: TestClient) -> None:
    response = client.post('/api/stt', data={'language': 'en'})

    assert response.status_code == 422


def test_stt_short_audio_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('MISTRAL_API_KEY', 'test-key')

    response = client.post(
        '/api/stt',
        data={'language': 'en'},
        files={'audio': ('sample.webm', b'123', 'audio/webm')},
    )

    assert response.status_code == 400
    assert 'too short' in response.json()['detail'].lower()


def test_stt_oversized_audio_returns_413(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('MISTRAL_API_KEY', 'test-key')
    monkeypatch.setenv('STT_MAX_UPLOAD_BYTES', '8')

    response = client.post(
        '/api/stt',
        data={'language': 'en'},
        files={'audio': ('sample.webm', b'a' * 16, 'audio/webm')},
    )

    assert response.status_code == 413
    assert 'too large' in response.json()['detail'].lower()


def test_stt_missing_api_key_returns_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('MISTRAL_API_KEY', raising=False)

    response = client.post(
        '/api/stt',
        data={'language': 'en'},
        files={'audio': ('sample.webm', b'a' * 4096, 'audio/webm')},
    )

    assert response.status_code == 500
    assert 'MISTRAL_API_KEY' in response.json()['detail']


def test_stt_success_returns_contract(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('MISTRAL_API_KEY', 'test-key')

    async def fake_transcribe(**_: object) -> str:
        return 'hello world'

    monkeypatch.setattr('server.app.transcribe_audio', fake_transcribe)

    response = client.post(
        '/api/stt',
        data={'language': 'en'},
        files={'audio': ('sample.webm', b'a' * 4096, 'audio/webm')},
    )

    assert response.status_code == 200
    assert response.json() == {'text': 'hello world', 'language': 'en'}


def test_stt_maps_upstream_rate_limit(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('MISTRAL_API_KEY', 'test-key')

    async def fake_transcribe(**_: object) -> str:
        raise UpstreamAPIError(status_code=429, detail='rate limited')

    monkeypatch.setattr('server.app.transcribe_audio', fake_transcribe)

    response = client.post(
        '/api/stt',
        data={'language': 'en'},
        files={'audio': ('sample.webm', b'a' * 4096, 'audio/webm')},
    )

    assert response.status_code == 429


def test_stt_maps_upstream_auth_error(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('MISTRAL_API_KEY', 'test-key')

    async def fake_transcribe(**_: object) -> str:
        raise UpstreamAPIError(status_code=401, detail='invalid key')

    monkeypatch.setattr('server.app.transcribe_audio', fake_transcribe)

    response = client.post(
        '/api/stt',
        data={'language': 'en'},
        files={'audio': ('sample.webm', b'a' * 4096, 'audio/webm')},
    )

    assert response.status_code == 502


def test_tts_missing_api_key_returns_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('ELEVENLABS_API_KEY', raising=False)

    response = client.post('/api/tts', json={'text': 'hello', 'voice_id': 'voice-1'})

    assert response.status_code == 500
    assert 'ELEVENLABS_API_KEY' in response.json()['detail']


def test_tts_empty_text_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ELEVENLABS_API_KEY', 'test-key')

    response = client.post('/api/tts', json={'text': '   ', 'voice_id': 'voice-1'})

    assert response.status_code == 422
    assert 'text' in str(response.json()['detail']).lower()


def test_tts_success_returns_audio(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ELEVENLABS_API_KEY', 'test-key')

    async def fake_open_stream(**_: object) -> tuple[FakeClient, FakeUpstreamResponse]:
        return FakeClient(), FakeUpstreamResponse([b'ID3', b'audio-bytes'])

    monkeypatch.setattr('server.app.open_tts_stream', fake_open_stream)

    response = client.post('/api/tts', json={'text': 'hello', 'voice_id': 'voice-1'})

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('audio/mpeg')
    assert response.content.startswith(b'ID3')


def test_tts_reads_upstream_stream_in_single_pass(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ELEVENLABS_API_KEY', 'test-key')

    class SinglePassResponse:
        def __init__(self) -> None:
            self._iterated = False
            self._chunks = [b'ID3', b'audio-bytes']

        async def aiter_bytes(self) -> AsyncIterator[bytes]:
            if self._iterated:
                raise httpx.StreamConsumed()
            self._iterated = True
            for chunk in self._chunks:
                yield chunk

        async def aclose(self) -> None:
            return None

    async def fake_open_stream(**_: object) -> tuple[FakeClient, SinglePassResponse]:
        return FakeClient(), SinglePassResponse()

    monkeypatch.setattr('server.app.open_tts_stream', fake_open_stream)

    response = client.post('/api/tts', json={'text': 'hello', 'voice_id': 'voice-1'})

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('audio/mpeg')
    assert response.content == b'ID3audio-bytes'


def test_tts_maps_upstream_errors(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ELEVENLABS_API_KEY', 'test-key')

    async def fake_open_stream(**_: object) -> tuple[FakeClient, FakeUpstreamResponse]:
        raise UpstreamAPIError(status_code=502, detail='upstream failure')

    monkeypatch.setattr('server.app.open_tts_stream', fake_open_stream)

    response = client.post('/api/tts', json={'text': 'hello', 'voice_id': 'voice-1'})

    assert response.status_code == 502


def test_tts_empty_upstream_audio_returns_502(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ELEVENLABS_API_KEY', 'test-key')

    async def fake_open_stream(**_: object) -> tuple[FakeClient, FakeUpstreamResponse]:
        return FakeClient(), FakeUpstreamResponse([])

    monkeypatch.setattr('server.app.open_tts_stream', fake_open_stream)

    response = client.post('/api/tts', json={'text': 'hello', 'voice_id': 'voice-1'})

    assert response.status_code == 502


def test_tts_midstream_failure_aborts_response(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ELEVENLABS_API_KEY', 'test-key')

    class MidStreamFailingResponse:
        def __init__(self) -> None:
            self._stream_started = False

        async def aiter_bytes(self) -> AsyncIterator[bytes]:
            if self._stream_started:
                raise httpx.StreamConsumed()
            self._stream_started = True
            yield b'ID3'
            raise httpx.ReadError('stream broke')

        async def aclose(self) -> None:
            return None

    async def fake_open_stream(**_: object) -> tuple[FakeClient, MidStreamFailingResponse]:
        return FakeClient(), MidStreamFailingResponse()

    monkeypatch.setattr('server.app.open_tts_stream', fake_open_stream)

    with pytest.raises(RuntimeError, match='TTS stream interrupted mid-response'):
        client.post('/api/tts', json={'text': 'hello', 'voice_id': 'voice-1'})


@pytest.mark.anyio
async def test_transcribe_audio_transport_error_maps_to_upstream_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class TransportFailingClient:
        def __init__(self, *_: object, **__: object) -> None:
            return

        async def __aenter__(self) -> TransportFailingClient:
            return self

        async def __aexit__(self, *_: object) -> None:
            return

        async def post(self, *_: object, **__: object) -> object:
            raise httpx.ConnectError('network down')

    monkeypatch.setattr('server.app.httpx.AsyncClient', TransportFailingClient)

    with pytest.raises(UpstreamAPIError) as exc:
        await transcribe_audio(
            api_key='key',
            audio_bytes=b'audio',
            filename='sample.webm',
            content_type='audio/webm',
            language='en',
        )

    assert exc.value.status_code == 502
    assert 'transport error' in exc.value.detail.lower()


@pytest.mark.anyio
async def test_transcribe_audio_invalid_json_maps_to_upstream_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class InvalidJsonResponse:
        status_code = 200
        text = ''

        def json(self) -> dict[str, str]:
            raise ValueError('bad json')

    class InvalidJsonClient:
        def __init__(self, *_: object, **__: object) -> None:
            return

        async def __aenter__(self) -> InvalidJsonClient:
            return self

        async def __aexit__(self, *_: object) -> None:
            return

        async def post(self, *_: object, **__: object) -> InvalidJsonResponse:
            return InvalidJsonResponse()

    monkeypatch.setattr('server.app.httpx.AsyncClient', InvalidJsonClient)

    with pytest.raises(UpstreamAPIError) as exc:
        await transcribe_audio(
            api_key='key',
            audio_bytes=b'audio',
            filename='sample.webm',
            content_type='audio/webm',
            language='en',
        )

    assert exc.value.status_code == 502
    assert 'invalid json' in exc.value.detail.lower()


@pytest.mark.anyio
async def test_open_tts_stream_transport_error_maps_to_upstream_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class TransportFailingClient:
        def __init__(self, *_: object, **__: object) -> None:
            return

        def build_request(self, *_: object, **__: object) -> object:
            return object()

        async def send(self, *_: object, **__: object) -> object:
            raise httpx.ConnectError('network down')

        async def aclose(self) -> None:
            return

    monkeypatch.setattr('server.app.httpx.AsyncClient', TransportFailingClient)

    with pytest.raises(UpstreamAPIError) as exc:
        await open_tts_stream(api_key='key', text='hello', voice_id='voice-1')

    assert exc.value.status_code == 502
    assert 'transport error' in exc.value.detail.lower()
