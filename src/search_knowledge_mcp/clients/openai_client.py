"""OpenAI Responses API + Web Search を利用するクライアント。"""

import logging
from typing import Any

from openai import OpenAI

from search_knowledge_mcp.clients.fetch_client import PageFetchClient
from search_knowledge_mcp.config import Settings
from search_knowledge_mcp.schemas import SearchNetworkKnowledgeInput, SearchResponse
from search_knowledge_mcp.search.content_extractor import extract_text_from_html
from search_knowledge_mcp.search.page_analyzer import analyze_page_content
from search_knowledge_mcp.search.parser import (
    build_notes_for_llm,
    parse_openai_response_to_items,
)
from search_knowledge_mcp.search.query_builder import build_search_queries, normalize_query

logger = logging.getLogger(__name__)


class OpenAIWebSearchClient:
    """OpenAI Responses API を利用して Web Search を実行するクライアント。"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: OpenAI | None = None
        self._page_fetch_client = PageFetchClient(
            timeout_seconds=min(settings.openai_timeout_seconds, 15)
        )
        if settings.openai_api_key:
            client_kwargs: dict[str, Any] = {
                "api_key": settings.openai_api_key,
                "timeout": settings.openai_timeout_seconds,
                "base_url": settings.openai_base_url or "https://api.openai.com/v1",
            }
            self._client = OpenAI(**client_kwargs)

    def search_network_knowledge(self, payload: SearchNetworkKnowledgeInput) -> SearchResponse:
        """統合検索を実行し、構造化レスポンスを返します。"""

        normalized_query = normalize_query(payload)
        search_queries = build_search_queries(payload)
        instruction = self._build_instruction(payload, search_queries)
        logger.info(
            "Executing OpenAI web search",
            extra={
                "normalized_query": normalized_query,
                "queries": search_queries,
            },
        )

        if self._client is None:
            return SearchResponse(
                query=payload.query,
                normalized_query=normalized_query,
                results=[],
                notes_for_llm=(
                    "OPENAI_API_KEY が未設定です。"
                    ".env または環境変数に設定してください。"
                ),
                error={
                    "type": "ConfigurationError",
                    "message": "OPENAI_API_KEY is not configured.",
                },
            )

        try:
            response = self._client.responses.create(
                model=self._settings.openai_model,
                tools=[{"type": "web_search_preview"}],
                input=instruction,
            )
            response_payload = response.model_dump()
            items = parse_openai_response_to_items(response_payload, payload.max_results)
            if payload.include_page_content:
                items = self._enrich_items_with_page_content(items)
            return SearchResponse(
                query=payload.query,
                normalized_query=normalized_query,
                results=items,
                notes_for_llm=build_notes_for_llm(items),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("OpenAI web search failed")
            return SearchResponse(
                query=payload.query,
                normalized_query=normalized_query,
                results=[],
                notes_for_llm="検索処理でエラーが発生しました。時間をおいて再試行するか、クエリを具体化してください。",
                error={"type": exc.__class__.__name__, "message": str(exc)},
            )

    def _enrich_items_with_page_content(self, items: list) -> list:
        """検索結果URLを取得し、本文由来の構造化情報を各結果に補強します。"""

        enriched_items = []
        for item in items:
            raw_html, fetch_status = self._page_fetch_client.fetch_text(str(item.url))
            item.page_fetch_status = fetch_status
            if not raw_html:
                enriched_items.append(item)
                continue

            page_text = extract_text_from_html(raw_html)
            if not page_text:
                enriched_items.append(item)
                continue

            analyzed = analyze_page_content(
                text=page_text,
                title=item.title,
                url=str(item.url),
            )
            item.content_observation = str(
                analyzed.get("content_observation", item.content_observation)
            )
            item.extracted_facts = list(analyzed.get("extracted_facts", []))
            item.possible_commands = list(analyzed.get("possible_commands", []))
            item.possible_procedures = list(analyzed.get("possible_procedures", []))
            item.important_notes = list(analyzed.get("important_notes", []))
            item.source_excerpt = str(analyzed.get("source_excerpt", ""))
            item.page_content_summary = str(analyzed.get("page_content_summary", ""))
            item.recommended_usage = str(analyzed.get("recommended_usage", ""))
            item.page_content_available = bool(analyzed.get("page_content_available", False))
            enriched_items.append(item)
        return enriched_items

    def _build_instruction(
        self,
        payload: SearchNetworkKnowledgeInput,
        search_queries: list[str],
    ) -> str:
        """Responses API へ渡す検索指示文を生成します。"""

        category_text = ", ".join(payload.categories) if payload.categories else "spec_detail"
        return f"""
あなたは技術調査アシスタントです。以下の条件を満たす最新情報を Web Search で収集してください。
- 対象クエリ: {payload.query}
- 正規化クエリ: {normalize_query(payload)}
- 追加検索クエリ候補: {search_queries}
- ベンダー: {payload.device_vendor or 'unspecified'}
- 製品/モデル: {payload.device_model or 'unspecified'}
- バージョン: {payload.os_version or 'unspecified'}
- カテゴリ: {category_text}
- 希望言語: {payload.language}
- 鮮度条件: 直近 {payload.freshness_days} 日を優先
- 最大件数: {payload.max_results}
- URL本文取得補強: {'enabled' if payload.include_page_content else 'disabled'}

要件:
1. まず公式ベンダー、公式ドキュメント、PSIRT、NVD、CVE を優先してください。
2. URL が実在しそうな結果を優先し、リンク切れが疑わしい場合は避けてください。
3. コマンドリファレンス、設定例、仕様差分、CVE、既知不具合、
   リリースノート、アップデート情報を横断的に確認してください。
4. 回答内には、結果ごとにタイトル、URL、要点、バージョン差分、
   CVE、fixed-in、公開日が分かる情報を含めてください。
5. 可能であれば複数の信頼できるソースを含めてください。
""".strip()
