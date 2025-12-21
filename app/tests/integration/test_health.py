from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
@pytest.mark.integration
async def test_health_check(client: AsyncClient, api_url):
    response = await client.get(api_url("/v1/healthcheck"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
