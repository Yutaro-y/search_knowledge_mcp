"""HTML本文から、LLMに渡しやすいプレーンテキストを抽出する処理。"""

import html
import re

SCRIPT_STYLE_PATTERN = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
TAG_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"[ \t\f\v]+")


def normalize_text_for_output(text: str, max_consecutive_newlines: int = 1) -> str:
    """返却用テキストの空白と改行を整形し、可読性を保ちます。"""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\u00a0", " ")
    normalized = re.sub(r"[ \t\f\v]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    newline_pattern = r"\n{" + str(max_consecutive_newlines + 1) + r",}"
    normalized = re.sub(newline_pattern, "\n" * max_consecutive_newlines, normalized)
    return normalized.strip()


def extract_text_from_html(raw_html: str, max_chars: int = 12000) -> str:
    """HTMLからスクリプト等を除去し、可読テキストを取り出します。"""

    cleaned = SCRIPT_STYLE_PATTERN.sub(" ", raw_html)
    cleaned = cleaned.replace("</p>", "\n").replace("</li>", "\n")
    cleaned = cleaned.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    cleaned = cleaned.replace("</div>", "\n").replace("</section>", "\n")
    cleaned = cleaned.replace("</article>", "\n").replace("</tr>", "\n")
    cleaned = TAG_PATTERN.sub(" ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = normalize_text_for_output(cleaned, max_consecutive_newlines=1)
    return cleaned[:max_chars]
