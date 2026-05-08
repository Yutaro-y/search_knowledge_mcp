"""検索結果URLの本文取得を担当するHTTPクライアント。"""

import logging
import re

import httpx

logger = logging.getLogger(__name__)

_META_CHARSET_PATTERN = re.compile(
    rb"<meta[^>]+charset=[\"']?([a-zA-Z0-9_\-]+)",
    re.IGNORECASE,
)

DEFAULT_HEADERS = {
    "User-Agent": (
        "search-knowledge-mcp/0.1.0 "
        "(+https://github.com/Yutaro-y/search_knowledge_mcp.git)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


class PageFetchClient:
    """検索結果URLからページ本文取得に必要な生データを得るクライアント。"""

    def __init__(self, timeout_seconds: int = 15) -> None:
        self._timeout_seconds = timeout_seconds

    def fetch_text(self, url: str) -> tuple[str | None, str]:
        """URLからHTML本文を取得し、本文文字列と状態を返します。"""

        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                follow_redirects=True,
                headers=DEFAULT_HEADERS,
            ) as client:
                response = client.get(url)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                decoded_text = self._decode_response_content(
                    content=response.content,
                    content_type=content_type,
                    apparent_encoding=response.encoding,
                )
                if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    return decoded_text, "fetched_non_html"
                return decoded_text, "fetched"
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Page fetch failed with HTTP status",
                extra={"url": url, "status": exc.response.status_code},
            )
            return None, f"http_error_{exc.response.status_code}"
        except httpx.TimeoutException:
            logger.warning("Page fetch timed out", extra={"url": url})
            return None, "timeout"
        except Exception:
            logger.exception("Unexpected page fetch error", extra={"url": url})
            return None, "fetch_error"

    def _decode_response_content(
        self,
        content: bytes,
        content_type: str,
        apparent_encoding: str | None,
    ) -> str:
        """HTTPレスポンス本文を、charset推定を考慮して安全にUnicodeへ変換する。"""

        encodings = self._build_encoding_candidates(
            content=content,
            content_type=content_type,
            apparent_encoding=apparent_encoding,
        )
        for encoding in encodings:
            try:
                return content.decode(encoding)
            except (LookupError, UnicodeDecodeError):
                continue
        return content.decode("utf-8", errors="replace")

    def _build_encoding_candidates(
        self,
        content: bytes,
        content_type: str,
        apparent_encoding: str | None,
    ) -> list[str]:
        """header/meta/apparent encoding をもとにデコード候補を組み立てる。"""

        candidates: list[str] = []
        header_charset = self._extract_charset_from_content_type(content_type)
        meta_charset = self._extract_meta_charset(content)

        for candidate in [header_charset, meta_charset, apparent_encoding]:
            normalized = self._normalize_encoding_name(candidate)
            if normalized and normalized not in candidates:
                candidates.append(normalized)

        for fallback in ["utf-8", "cp932", "shift_jis", "euc_jp", "iso2022_jp", "latin-1"]:
            if fallback not in candidates:
                candidates.append(fallback)
        return candidates

    def _extract_charset_from_content_type(self, content_type: str) -> str | None:
        """Content-Type ヘッダから charset を抽出する。"""

        parts = [part.strip() for part in content_type.split(";")]
        for part in parts[1:]:
            if part.lower().startswith("charset="):
                return part.split("=", 1)[1].strip().strip('"').strip("'")
        return None

    def _extract_meta_charset(self, content: bytes) -> str | None:
        """HTML先頭付近の meta charset を抽出する。"""

        head = content[:4096]
        match = _META_CHARSET_PATTERN.search(head)
        if match:
            return match.group(1).decode("ascii", errors="ignore")
        return None

    def _normalize_encoding_name(self, encoding: str | None) -> str | None:
        """同義表記を吸収して Python codec 名へ寄せる。"""

        if not encoding:
            return None
        normalized = encoding.strip().lower().replace("_", "-")
        alias_map = {
            "shift-jis": "cp932",
            "shift_jis": "cp932",
            "sjis": "cp932",
            "windows-31j": "cp932",
            "x-sjis": "cp932",
            "utf8": "utf-8",
        }
        return alias_map.get(normalized, normalized)
