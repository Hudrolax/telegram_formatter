from domain.services.telegram_formatter import format_markdown_for_telegram


def test_formatting_preserves_basic_markup():
    text = "Hello *world* and __strong__"
    result = format_markdown_for_telegram(text, 4096)
    assert result == ["Hello <i>world</i> and <b>strong</b>"]


def test_split_long_message():
    text = "a" * 5000
    parts = format_markdown_for_telegram(text, 4096)
    assert len(parts) == 2
    assert all(len(part) <= 4096 for part in parts)
    assert "".join(parts) == text


def test_control_chars_removed_and_escaped():
    text = "hi\x00 & <tag>"
    result = format_markdown_for_telegram(text, 4096)
    assert result == ["hi &amp; &lt;tag&gt;"]


def test_spoiler_formatting():
    text = "Hello ||secret||"
    result = format_markdown_for_telegram(text, 4096)
    assert result == ["Hello <span class=\"tg-spoiler\">secret</span>"]


def test_split_preserves_tags():
    text = "**hello world**"
    result = format_markdown_for_telegram(text, 6)
    assert result == ["<b>hello </b>", "<b>world</b>"]


def test_code_block_kept_intact_when_fits():
    text = "Intro\n\n```python\nprint(1)\n```"
    result = format_markdown_for_telegram(text, 10)
    assert result == ["Intro\n", "<pre><code class=\"language-python\">print(1)\n</code></pre>"]


def test_code_block_split_prefers_newline():
    text = "```\nline1\nline2\nline3\n```"
    result = format_markdown_for_telegram(text, 7)
    assert result == [
        "<pre><code>line1\n</code></pre>",
        "<pre><code>line2\n</code></pre>",
        "<pre><code>line3\n</code></pre>",
    ]


def test_custom_emoji_from_markdown_image():
    text = "![🙂](tg://emoji?id=123)"
    result = format_markdown_for_telegram(text, 4096)
    assert result == ["<tg-emoji emoji-id=\"123\">🙂</tg-emoji>"]
