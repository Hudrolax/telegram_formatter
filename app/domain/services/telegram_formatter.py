from __future__ import annotations

from dataclasses import dataclass
import html
from html.parser import HTMLParser
import re
import uuid

from markdown_it import MarkdownIt


_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_CODE_BLOCK_RE = re.compile(r"```(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_SPOILER_RE = re.compile(r"\|\|(.+?)\|\|", re.DOTALL)
_TG_EMOJI_ID_RE = re.compile(r"^tg://emoji\?id=(\d+)$", re.IGNORECASE)


@dataclass(frozen=True)
class _HtmlToken:
    kind: str
    tag: str | None = None
    attrs: dict[str, str] | None = None
    text: str | None = None


def format_markdown_for_telegram(text: str, max_length: int) -> list[str]:
    cleaned = _sanitize_text(text)
    if cleaned.strip() == "":
        return []

    prepared = _replace_spoilers(cleaned)
    html_text = _markdown_to_html(prepared)
    tokens = _sanitize_html(html_text)
    tokens = _trim_trailing_newlines(tokens)
    return _split_tokens(tokens, max_length)


def _sanitize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return _CONTROL_CHARS_RE.sub("", normalized)


def _replace_spoilers(text: str) -> str:
    tokens: list[tuple[str, str]] = []

    def stash(match: re.Match[str]) -> str:
        placeholder = _unique_placeholder(text)
        tokens.append((placeholder, match.group(0)))
        return placeholder

    protected = _CODE_BLOCK_RE.sub(stash, text)
    protected = _INLINE_CODE_RE.sub(stash, protected)

    protected = _SPOILER_RE.sub(r'<span class="tg-spoiler">\1</span>', protected)

    for placeholder, original in tokens:
        protected = protected.replace(placeholder, original)

    return protected


def _markdown_to_html(text: str) -> str:
    md = MarkdownIt("commonmark", {"html": True})
    md.enable("strikethrough")
    return md.render(text)


def _sanitize_html(text: str) -> list[_HtmlToken]:
    parser = _TelegramHTMLSanitizer()
    parser.feed(text)
    parser.close()
    return parser.tokens


def _escape_text(text: str) -> str:
    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
    return escaped


def _escape_attr(value: str) -> str:
    return _escape_text(value)


def _literal_start_tag(tag: str, attrs: list[tuple[str, str | None]]) -> str:
    if not attrs:
        return f"<{tag}>"
    rendered = " ".join(
        f'{name}="{value or ""}"' if value is not None else name
        for name, value in attrs
    )
    return f"<{tag} {rendered}>"


def _render_tokens(tokens: list[_HtmlToken], open_tags: list[_HtmlToken]) -> str:
    parts: list[str] = []

    for token in tokens:
        if token.kind == "text" and token.text is not None:
            parts.append(_escape_text(token.text))
            continue
        if token.kind == "start" and token.tag:
            parts.append(_render_start_tag(token))
            continue
        if token.kind == "end" and token.tag:
            parts.append(f"</{token.tag}>")
            continue

    for open_tag in reversed(open_tags):
        if open_tag.tag:
            parts.append(f"</{open_tag.tag}>")

    return "".join(parts)


def _render_start_tag(token: _HtmlToken) -> str:
    tag = token.tag or ""
    attrs = token.attrs or {}

    if tag == "a":
        href = attrs.get("href")
        if href:
            return f'<a href="{_escape_attr(href)}">'
        return "<a>"
    if tag == "span" and attrs.get("class") == "tg-spoiler":
        return '<span class="tg-spoiler">'
    if tag == "blockquote" and attrs.get("expandable") == "true":
        return "<blockquote expandable>"
    if tag == "code" and "class" in attrs:
        return f'<code class="{_escape_attr(attrs["class"])}">'
    if tag == "tg-emoji":
        emoji_id = attrs.get("emoji-id")
        if emoji_id:
            return f'<tg-emoji emoji-id="{_escape_attr(emoji_id)}">'
        return "<tg-emoji>"

    return f"<{tag}>"


def _split_tokens(tokens: list[_HtmlToken], max_length: int) -> list[str]:
    if max_length <= 0:
        return [
            _render_tokens(tokens, _collect_open_tags(tokens)),
        ]

    parts: list[str] = []
    current: list[_HtmlToken] = []
    open_tags: list[_HtmlToken] = []
    current_len = 0

    for index, token in enumerate(tokens):
        if token.kind == "start" and token.tag:
            if token.tag == "pre":
                block_len = _measure_pre_block_length(tokens, index)
                remaining = max_length - current_len
                if (
                    block_len is not None
                    and block_len <= max_length
                    and current_len > 0
                    and block_len > remaining
                ):
                    parts.append(_render_tokens(current, open_tags))
                    current = _reopen_tags(open_tags)
                    current_len = 0
            current.append(token)
            open_tags.append(token)
            continue
        if token.kind == "end" and token.tag:
            if open_tags and open_tags[-1].tag == token.tag:
                open_tags.pop()
                current.append(token)
            continue
        if token.kind == "text" and token.text is not None:
            text = token.text
            while text:
                remaining = max_length - current_len
                if remaining <= 0:
                    parts.append(_render_tokens(current, open_tags))
                    current = _reopen_tags(open_tags)
                    current_len = 0
                    continue

                if len(text) <= remaining:
                    current.append(_HtmlToken(kind="text", text=text))
                    current_len += len(text)
                    text = ""
                    continue

                in_code_block = any(tag.tag == "pre" for tag in open_tags)
                split_at = _find_split_position(text, remaining, in_code_block)
                current.append(_HtmlToken(kind="text", text=text[:split_at]))
                current_len += len(text[:split_at])
                parts.append(_render_tokens(current, open_tags))
                current = _reopen_tags(open_tags)
                current_len = 0
                text = text[split_at:]

    if current:
        parts.append(_render_tokens(current, open_tags))

    return parts


def _find_split_position(text: str, limit: int, prefer_newline: bool) -> int:
    if prefer_newline:
        split_at = text.rfind("\n", 0, limit)
        if split_at <= 0:
            return limit
        return split_at + 1

    split_at = max(text.rfind("\n", 0, limit), text.rfind(" ", 0, limit))
    if split_at <= 0:
        return limit
    return split_at + 1


def _reopen_tags(open_tags: list[_HtmlToken]) -> list[_HtmlToken]:
    reopened: list[_HtmlToken] = []
    for tag in open_tags:
        reopened.append(tag)
    return reopened


def _collect_open_tags(tokens: list[_HtmlToken]) -> list[_HtmlToken]:
    stack: list[_HtmlToken] = []
    for token in tokens:
        if token.kind == "start" and token.tag:
            stack.append(token)
        if token.kind == "end" and token.tag:
            if stack and stack[-1].tag == token.tag:
                stack.pop()
    return stack


def _unique_placeholder(source: str) -> str:
    while True:
        placeholder = f"TGPHTOKEN{uuid.uuid4().hex}X"
        if placeholder not in source:
            return placeholder


def _trim_trailing_newlines(tokens: list[_HtmlToken]) -> list[_HtmlToken]:
    while tokens:
        last = tokens[-1]
        if last.kind != "text" or last.text is None:
            break
        trimmed = last.text.rstrip("\n")
        if trimmed == last.text:
            break
        if trimmed == "":
            tokens.pop()
            continue
        tokens[-1] = _HtmlToken(kind="text", text=trimmed)
        break
    return tokens


def _measure_pre_block_length(tokens: list[_HtmlToken], start_index: int) -> int | None:
    token = tokens[start_index]
    if token.kind != "start" or token.tag != "pre":
        return None

    depth = 0
    length = 0
    for current in tokens[start_index:]:
        if current.kind == "start" and current.tag == "pre":
            depth += 1
            continue
        if current.kind == "end" and current.tag == "pre":
            depth -= 1
            if depth == 0:
                return length
            continue
        if current.kind == "text" and current.text is not None:
            length += len(current.text)
    return None


class _TelegramHTMLSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.tokens: list[_HtmlToken] = []
        self._open_tags: list[_HtmlToken] = []
        self._list_stack: list[dict[str, int | str]] = []
        self._blockquote_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()

        if tag in {"ul", "ol"}:
            self._start_list(tag)
            return
        if tag == "li":
            self._start_list_item()
            return
        if tag == "br":
            self._append_text("\n")
            return
        if tag == "p":
            self._ensure_block_break()
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._ensure_block_break()
            self._open_tag("b", {})
            return
        if tag == "blockquote":
            self._start_blockquote(attrs)
            return
        if tag == "img":
            attrs_dict = {name.lower(): value for name, value in attrs if name}
            alt_text = attrs_dict.get("alt")
            src = attrs_dict.get("src")
            emoji_id = _extract_emoji_id(src)
            if emoji_id and alt_text:
                self._open_tag("tg-emoji", {"emoji-id": emoji_id})
                self._append_text(alt_text)
                self._close_tag("tg-emoji")
                return
            if alt_text:
                self._append_text(alt_text)
            return

        normalized, out_attrs = self._normalize_tag(tag, attrs)
        if normalized is None:
            self._append_text(_literal_start_tag(tag, attrs))
            return

        self._open_tag(normalized, out_attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag in {"ul", "ol"}:
            self._end_list()
            return
        if tag == "li":
            self._append_text("\n")
            return
        if tag == "p":
            self._append_text("\n")
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._close_tag("b")
            self._append_text("\n")
            return
        if tag == "blockquote":
            self._end_blockquote()
            return
        if tag == "img":
            return
        normalized = self._normalize_end_tag(tag)
        if normalized is None:
            self._append_text(f"</{tag}>")
            return

        self._close_tag(normalized)

    def handle_data(self, data: str) -> None:
        if data.strip() == "" and "\n" in data and not self._preserve_whitespace():
            return
        self._append_text(data)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_entityref(self, name: str) -> None:
        self._append_text(html.unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self._append_text(html.unescape(f"&#{name};"))

    def _normalize_tag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> tuple[str | None, dict[str, str]]:
        mapped = {
            "strong": "b",
            "b": "b",
            "em": "i",
            "i": "i",
            "ins": "u",
            "u": "u",
            "strike": "s",
            "s": "s",
            "del": "s",
            "code": "code",
            "pre": "pre",
            "a": "a",
            "span": "span",
            "tg-spoiler": "span",
            "blockquote": "blockquote",
            "tg-emoji": "tg-emoji",
        }.get(tag)

        if mapped is None:
            return None, {}

        out_attrs: dict[str, str] = {}
        attrs_dict = {name.lower(): value for name, value in attrs if name}

        if mapped == "a":
            href = attrs_dict.get("href")
            if not href or not _is_allowed_href(href):
                return None, {}
            out_attrs["href"] = href
            return mapped, out_attrs

        if mapped == "code":
            class_value = attrs_dict.get("class")
            if class_value and class_value.startswith("language-"):
                out_attrs["class"] = class_value
            return mapped, out_attrs

        if mapped == "span":
            if attrs_dict.get("class") == "tg-spoiler" or tag == "tg-spoiler":
                out_attrs["class"] = "tg-spoiler"
                return mapped, out_attrs
            return None, {}

        if mapped == "blockquote":
            if "expandable" in attrs_dict:
                out_attrs["expandable"] = "true"
            return mapped, out_attrs

        if mapped == "tg-emoji":
            emoji_id = attrs_dict.get("emoji-id")
            if emoji_id:
                out_attrs["emoji-id"] = emoji_id
                return mapped, out_attrs
            return None, {}

        return mapped, out_attrs

    def _normalize_end_tag(self, tag: str) -> str | None:
        return {
            "strong": "b",
            "b": "b",
            "em": "i",
            "i": "i",
            "ins": "u",
            "u": "u",
            "strike": "s",
            "s": "s",
            "del": "s",
            "code": "code",
            "pre": "pre",
            "a": "a",
            "span": "span",
            "tg-spoiler": "span",
            "blockquote": "blockquote",
            "tg-emoji": "tg-emoji",
        }.get(tag)

    def _start_list(self, tag: str) -> None:
        self._ensure_block_break()
        list_type = "ol" if tag == "ol" else "ul"
        self._list_stack.append({"type": list_type, "index": 0})

    def _end_list(self) -> None:
        if self._list_stack:
            self._list_stack.pop()
        self._append_text("\n")

    def _start_list_item(self) -> None:
        if not self._list_stack:
            self._append_text("\n")
            return

        list_ctx = self._list_stack[-1]
        list_ctx["index"] = int(list_ctx["index"]) + 1

        if self.tokens and not self._endswith_newline():
            self._append_text("\n")

        if list_ctx["type"] == "ol":
            prefix = f"{list_ctx['index']}. "
        else:
            prefix = "• "
        self._append_text(prefix)

    def _start_blockquote(self, attrs: list[tuple[str, str | None]]) -> None:
        if self._blockquote_depth > 0:
            self._blockquote_depth += 1
            return

        expandable = any(name == "expandable" for name, _ in attrs)
        out_attrs = {"expandable": "true"} if expandable else {}
        self._ensure_block_break()
        self._open_tag("blockquote", out_attrs)
        self._blockquote_depth = 1

    def _end_blockquote(self) -> None:
        if self._blockquote_depth == 0:
            return
        self._blockquote_depth -= 1
        if self._blockquote_depth == 0:
            self._close_tag("blockquote")
            self._append_text("\n")

    def _open_tag(self, tag: str, attrs: dict[str, str]) -> None:
        token = _HtmlToken(kind="start", tag=tag, attrs=attrs)
        self.tokens.append(token)
        self._open_tags.append(token)

    def _close_tag(self, tag: str) -> None:
        if not self._open_tags:
            return
        if self._open_tags[-1].tag != tag:
            return
        self._open_tags.pop()
        self.tokens.append(_HtmlToken(kind="end", tag=tag))

    def _append_text(self, text: str) -> None:
        if text == "":
            return
        if self.tokens and self.tokens[-1].kind == "text" and self.tokens[-1].text is not None:
            merged = self.tokens[-1].text + text
            self.tokens[-1] = _HtmlToken(kind="text", text=merged)
            return
        self.tokens.append(_HtmlToken(kind="text", text=text))

    def _ensure_block_break(self) -> None:
        if not self.tokens:
            return
        last = self.tokens[-1]
        if last.kind == "text" and last.text is not None and not last.text.endswith("\n"):
            self._append_text("\n")
        if last.kind == "end":
            self._append_text("\n")

    def _endswith_newline(self) -> bool:
        if not self.tokens:
            return False
        last = self.tokens[-1]
        return last.kind == "text" and last.text is not None and last.text.endswith("\n")

    def _preserve_whitespace(self) -> bool:
        return any(tag.tag in {"pre", "code"} for tag in self._open_tags)


def _is_allowed_href(href: str) -> bool:
    return href.startswith("http://") or href.startswith("https://") or href.startswith("tg://user?id=")


def _extract_emoji_id(src: str | None) -> str | None:
    if not src:
        return None
    match = _TG_EMOJI_ID_RE.match(src)
    if not match:
        return None
    return match.group(1)
