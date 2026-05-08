"""OpenAI応答から検索結果を正規化する処理。"""

import re
from typing import Any

from search_knowledge_mcp.schemas import SearchMetadata, SearchResultItem
from search_knowledge_mcp.search.classifier import (
    classify_source_type,
    infer_categories,
    infer_content_kind,
    infer_trust_level,
)
from search_knowledge_mcp.search.content_extractor import normalize_text_for_output

CVE_PATTERN = re.compile(r"(CVE-\d{4}-\d{4,})", re.IGNORECASE)
VERSION_PATTERN = re.compile(r"\b\d+(?:\.\d+){1,3}\b")


def _extract_text_block(response_payload: dict[str, Any]) -> str:
    output = response_payload.get("output", [])
    texts: list[str] = []
    for item in output:
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                texts.append(content["text"])
    return "\n".join(texts)


def parse_openai_response_to_items(
    response_payload: dict[str, Any],
    max_results: int,
) -> list[SearchResultItem]:
    """Responses API の結果を、扱いやすい構造へ変換します。

    実際の Web Search 返却形式は将来的に変化しうるため、ここでは
    1) annotations にURLが含まれる場合
    2) 本文テキストに URL 箇条書きが含まれる場合
    の両方を吸収する、壊れにくい実装を採用します。
    """

    items: list[SearchResultItem] = []
    seen_urls: set[str] = set()
    output = response_payload.get("output", [])

    for item in output:
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            text = content.get("text", "") or ""
            annotations = content.get("annotations", []) or []
            for annotation in annotations:
                url = annotation.get("url") or annotation.get("uri")
                title = annotation.get("title") or annotation.get("text") or "Search Result"
                if not url:
                    continue
                normalized_url = str(url).rstrip("/ ")
                if normalized_url in seen_urls:
                    continue
                seen_urls.add(normalized_url)

                start_index = annotation.get("start_index", 0)
                end_index = annotation.get("end_index", 0)
                snippet_window_start = max(0, start_index - 220)
                snippet_window_end = min(len(text), end_index + 220)
                snippet = normalize_text_for_output(
                    text[snippet_window_start:snippet_window_end].strip()
                    or text[:500].strip()
                )

                cve_match = CVE_PATTERN.search(f"{title} {snippet}")
                version_match = VERSION_PATTERN.search(f"{title} {snippet}")
                source_type = classify_source_type(url)
                categories = infer_categories(title, snippet)
                has_cve_id = cve_match is not None
                has_version_hint = version_match is not None
                trust_level_hint, why_this_trust_level = infer_trust_level(
                    source_type=source_type,
                    title=title,
                    snippet=snippet,
                    has_cve_id=has_cve_id,
                    has_version_hint=has_version_hint,
                )
                items.append(
                    SearchResultItem(
                        title=title,
                        url=normalized_url,
                        source_type=source_type,
                        content_kind=infer_content_kind(source_type, title, snippet),
                        categories=categories,
                        summary=normalize_text_for_output(
                            snippet or "OpenAI Web Search により取得された結果です。"
                        ),
                        raw_snippet=normalize_text_for_output(snippet),
                        content_observation=normalize_text_for_output(
                            snippet or "検索結果本文から抽出された要点は限定的でした。"
                        ),
                        trust_level_hint=trust_level_hint,
                        why_this_trust_level=why_this_trust_level,
                        trust_signals={
                            "domain": (
                                normalized_url.split("/")[2] if "://" in normalized_url else None
                            ),
                            "is_official_source": source_type
                            in {"official_vendor", "documentation"},
                            "is_security_advisory": source_type == "security_advisory",
                            "has_cve_id": has_cve_id,
                            "has_version_hint": has_version_hint,
                        },
                        metadata=SearchMetadata(
                            cve_id=cve_match.group(1).upper() if cve_match else None,
                            version=version_match.group(0) if version_match else None,
                        ),
                        confidence=0.8,
                    )
                )

    if items:
        return items[:max_results]

    text_block = normalize_text_for_output(_extract_text_block(response_payload))
    urls = re.findall(r"https?://[^\s)\]>]+", text_block)
    deduped_urls: list[str] = []
    for url in urls:
        cleaned = url.rstrip(".,")
        if cleaned not in deduped_urls:
            deduped_urls.append(cleaned)

    for index, url in enumerate(deduped_urls[:max_results], start=1):
        snippet = normalize_text_for_output(text_block[:500].strip())
        source_type = classify_source_type(url)
        categories = infer_categories(text_block[:120], snippet)
        has_cve_id = CVE_PATTERN.search(snippet) is not None
        has_version_hint = VERSION_PATTERN.search(snippet) is not None
        trust_level_hint, why_this_trust_level = infer_trust_level(
            source_type=source_type,
            title=f"Search Result {index}",
            snippet=snippet,
            has_cve_id=has_cve_id,
            has_version_hint=has_version_hint,
        )
        items.append(
            SearchResultItem(
                title=f"Search Result {index}",
                url=url,
                source_type=source_type,
                content_kind=infer_content_kind(source_type, text_block[:120], snippet),
                categories=categories,
                summary=normalize_text_for_output(
                    snippet or "OpenAI Web Search により取得された結果です。"
                ),
                raw_snippet=normalize_text_for_output(snippet),
                content_observation=normalize_text_for_output(
                    snippet or "検索結果本文から抽出された要点は限定的でした。"
                ),
                trust_level_hint=trust_level_hint,
                why_this_trust_level=why_this_trust_level,
                trust_signals={
                    "domain": url.split("/")[2] if "://" in url else None,
                    "is_official_source": source_type
                    in {"official_vendor", "documentation"},
                    "is_security_advisory": source_type == "security_advisory",
                    "has_cve_id": has_cve_id,
                    "has_version_hint": has_version_hint,
                },
                confidence=0.6,
            )
        )

    return items[:max_results]


def build_notes_for_llm(items: list[SearchResultItem]) -> str:
    """LLM向けの利用上の注意を生成します。"""

    if not items:
        return "検索結果が少ないため、バージョンやベンダー名を追加して再検索を推奨します。"

    official_count = sum(1 for item in items if item.source_type == "official_vendor")
    advisory_count = sum(1 for item in items if item.source_type == "security_advisory")
    return (
        "結果を利用する際は URL・公開日・対象バージョンを確認してください。"
        f" 公式ベンダー由来 {official_count} 件、"
        f"セキュリティアドバイザリ {advisory_count} 件を含みます。"
    )
