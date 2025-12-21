from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Привет, **мир**", [{"text": "Привет, <b>мир</b>"}]),
        ("Hello *world*", [{"text": "Hello <i>world</i>"}]),
        ("Hello ~~world~~", [{"text": "Hello <s>world</s>"}]),
        ("`code`", [{"text": "<code>code</code>"}]),
        (
            "```python\nprint(1)\n```",
            [{"text": "<pre><code class=\"language-python\">print(1)\n</code></pre>"}],
        ),
        ("[OpenAI](https://openai.com)", [{"text": "<a href=\"https://openai.com\">OpenAI</a>"}]),
        ("||secret||", [{"text": "<span class=\"tg-spoiler\">secret</span>"}]),
        ("> quote", [{"text": "<blockquote>quote\n</blockquote>"}]),
        ("- one\n- two", [{"text": "• one\n• two"}]),
        ("1. one\n2. two", [{"text": "1. one\n2. two"}]),
        ("# Title", [{"text": "<b>Title</b>"}]),
        ("<u>under</u>", [{"text": "<u>under</u>"}]),
        ("<blockquote expandable>more</blockquote>", [{"text": "<blockquote expandable>more</blockquote>"}]),
        (
            "| A | B |\n| - | - |\n| 1 | 2 |",
            [{"text": "| A | B |\n| - | - |\n| 1 | 2 |"}],
        ),
        (
            "<tg-emoji emoji-id=\"123\">🙂</tg-emoji>",
            [{"text": "<tg-emoji emoji-id=\"123\">🙂</tg-emoji>"}],
        ),
        (
            "![🙂](tg://emoji?id=123)",
            [{"text": "<tg-emoji emoji-id=\"123\">🙂</tg-emoji>"}],
        ),
    ],
)
async def test_format_endpoint(client: AsyncClient, api_url, text: str, expected: list[dict[str, str]]):
    response = await client.post(api_url("/v1/format"), json={"text": text})
    assert response.status_code == 200
    assert response.json() == expected
