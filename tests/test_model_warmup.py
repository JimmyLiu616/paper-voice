import asyncio
import httpx
import pytest
from fastapi.testclient import TestClient
import app

HEADERS = {'X-PaperVoice': 'local-ui'}


@pytest.mark.parametrize('failure', [None, 'http', 'timeout', 'incomplete'])
def test_preparation_has_no_document_and_preserves_context(monkeypatch, failure):
    requests = []
    client_type = httpx.AsyncClient
    async def transport(request):
        import json
        requests.append(json.loads(request.content))
        if failure == 'timeout':
            raise httpx.ReadTimeout('timeout', request=request)
        return httpx.Response(404 if failure == 'http' else 200,
                              json={'done': failure != 'incomplete'})
    monkeypatch.setattr(app.httpx, 'AsyncClient', lambda **kw:
                        client_type(transport=httpx.MockTransport(transport), **kw))
    with TestClient(app.app) as client:
        response = client.post('/api/warmup', headers=HEADERS)
        assert response.status_code == (503 if failure else 200)
        if not failure:
            assert response.json()['status'] == 'ready'
        assert requests == [{'model': app.MODEL, 'prompt': '', 'stream': False,
                             'keep_alive': '5m', 'options': {'num_ctx': 8192}}]
        assert not app.model_lock.locked()
        assert not app.jobs


def test_preparation_does_not_queue_behind_an_active_document(monkeypatch):
    lock = asyncio.Lock()
    monkeypatch.setattr(app, 'model_lock', lock)
    async def check():
        await lock.acquire()
        try:
            assert await app.warmup() == {'status': 'busy'}
        finally:
            lock.release()
    asyncio.run(check())


def test_preparation_requires_local_ui_header():
    with TestClient(app.app) as client:
        assert client.post('/api/warmup').status_code == 403
