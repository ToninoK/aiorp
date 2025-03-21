import aiohttp

from aiorp.context import ProxyContext


async def test_session_factory():
    context = ProxyContext(
        url="http://test.com",
        session_factory=lambda: aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(connect=10)
        ),
    )
    assert context.session is not None
    assert isinstance(context.session, aiohttp.ClientSession)
    assert context.session.timeout.connect == 10


async def test_context_no_session_factory():
    context = ProxyContext(url="http://test.com")
    assert context.session is not None


async def test_context_close_session():
    context = ProxyContext(url="http://test.com")
    session = context.session
    assert session is not None
    await context.close_session()
    assert session.closed
