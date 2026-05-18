"""MCPサーバのエントリポイント。"""

from mcp.server.fastmcp import FastMCP

from search_knowledge_mcp.clients.openai_client import OpenAIWebSearchClient
from search_knowledge_mcp.config import get_settings
from search_knowledge_mcp.logging_utils import configure_logging
from search_knowledge_mcp.schemas import (
    SearchFreeformTechInfoInput,
    SearchNetworkDocsInput,
    SearchNetworkKnowledgeInput,
    SearchOsAndSoftwareSpecsInput,
    SearchReleaseNotesAndUpdatesInput,
    SearchVulnerabilitiesAndBugsInput,
)

settings = get_settings()
configure_logging(settings.log_level)
client = OpenAIWebSearchClient(settings)
mcp = FastMCP("search-knowledge-mcp")


@mcp.tool()
def search_network_knowledge(
    query: str,
    device_vendor: str | None = None,
    device_model: str | None = None,
    os_version: str | None = None,
    categories: list[str] | None = None,
    max_results: int = 8,
    language: str = "auto",
    freshness_days: int = 365,
    include_page_content: bool = True,
) -> dict:
    """
    NW機器、OS、CVE、リリースノートなどを横断検索する統合ツール。
    query(str): 検索ワード。リクエスト時に必ず含める必要がある。 
    device_vendor(str): ベンダー/メーカー名。※デフォルト: None
    device_model(str):  モデル/型番名。※デフォルト: None
    os_version(str):  "device_model"のOSバージョン。※デフォルト: None
    categories(list[str]): 以下から選択するか、Noneを指定（全カテゴリ対象）。※デフォルト: None
        - `command_reference`
        - `config_example`
        - `spec_detail`
        - `cve`
        - `bug`
        - `workaround`
        - `release_note`
        - `update_info`
    max_results(int): Web Search で収集するアクセス先の件数。 ※デフォルト: 8
    language(str)  "auto", # 検索言語。多様な言語で広く情報を収集するポリシー
    freshness_days(int) 情報の"鮮度"。int型で日数を指定。設定した値の日数分までの期間で検索する。古い機器やOS、ファームウェアに関する内容のような「古くならざるを得ない」項目については十分に大きな値を設定する ※デフォルト: 365
    include_page_content: bool = True,
    """

    payload = SearchNetworkKnowledgeInput(
        query=query,
        device_vendor=device_vendor,
        device_model=device_model,
        os_version=os_version,
        categories=categories or [],
        max_results=max_results,
        language=language,
        freshness_days=freshness_days,
        include_page_content=include_page_content,
    )
    return client.search_network_knowledge(payload).model_dump(mode="json")


@mcp.tool()
def search_network_docs(
    vendor: str,
    query: str,
    product_family: str | None = None,
    version: str | None = None,
    max_results: int = 5,
    include_page_content: bool = True,
) -> dict:
    """NW機器のコマンドリファレンス・設定例・公式ドキュメントを検索するラッパ。"""

    payload = SearchNetworkDocsInput(
        vendor=vendor,
        product_family=product_family,
        version=version,
        query=query,
        max_results=max_results,
    )
    return client.search_network_knowledge(
        SearchNetworkKnowledgeInput(
            query=payload.query,
            device_vendor=payload.vendor,
            device_model=payload.product_family,
            os_version=payload.version,
            categories=["command_reference", "config_example"],
            max_results=payload.max_results,
            language=settings.default_language,
            freshness_days=settings.default_freshness_days,
            include_page_content=include_page_content,
        )
    ).model_dump(mode="json")


@mcp.tool()
def search_os_and_software_specs(
    target_name: str,
    query: str,
    category: str | None = None,
    max_results: int = 5,
    include_page_content: bool = True,
) -> dict:
    """OS、ライブラリ、SDKなどの仕様・制約・設定例を検索するラッパ。"""

    payload = SearchOsAndSoftwareSpecsInput(
        target_name=target_name,
        category=category,
        query=query,
        max_results=max_results,
    )
    categories = ["spec_detail"]
    if payload.category == "config":
        categories.append("config_example")
    return client.search_network_knowledge(
        SearchNetworkKnowledgeInput(
            query=f"{payload.target_name} {payload.query}",
            device_vendor=None,
            device_model=payload.target_name,
            os_version=None,
            categories=categories,
            max_results=payload.max_results,
            language=settings.default_language,
            freshness_days=settings.default_freshness_days,
            include_page_content=include_page_content,
        )
    ).model_dump(mode="json")


@mcp.tool()
def search_vulnerabilities_and_bugs(
    product: str,
    version: str | None = None,
    cve_id: str | None = None,
    query: str | None = None,
    max_results: int = 10,
    include_page_content: bool = True,
) -> dict:
    """CVE、既知バグ、回避策、修正版情報を検索するラッパ。"""

    payload = SearchVulnerabilitiesAndBugsInput(
        product=product,
        version=version,
        cve_id=cve_id,
        query=query,
        max_results=max_results,
    )
    merged_query = " ".join(
        part
        for part in [payload.product, payload.version, payload.cve_id, payload.query]
        if part
    )
    return client.search_network_knowledge(
        SearchNetworkKnowledgeInput(
            query=merged_query,
            device_vendor=None,
            device_model=payload.product,
            os_version=payload.version,
            categories=["cve", "bug", "workaround"],
            max_results=payload.max_results if payload.max_results <= 20 else 20,
            language=settings.default_language,
            freshness_days=settings.default_freshness_days,
            include_page_content=include_page_content,
        )
    ).model_dump(mode="json")


@mcp.tool()
def search_release_notes_and_updates(
    product: str,
    current_version: str | None = None,
    target_version: str | None = None,
    query: str | None = None,
    max_results: int = 5,
    include_page_content: bool = True,
) -> dict:
    """リリースノート、アップデート、仕様変更情報を検索するラッパ。"""

    payload = SearchReleaseNotesAndUpdatesInput(
        product=product,
        current_version=current_version,
        target_version=target_version,
        query=query,
        max_results=max_results,
    )
    merged_query = " ".join(
        part
        for part in [
            payload.product,
            payload.current_version,
            payload.target_version,
            payload.query,
            "release notes",
        ]
        if part
    )
    return client.search_network_knowledge(
        SearchNetworkKnowledgeInput(
            query=merged_query,
            device_vendor=None,
            device_model=payload.product,
            os_version=payload.target_version or payload.current_version,
            categories=["release_note", "update_info", "bug"],
            max_results=payload.max_results,
            language=settings.default_language,
            freshness_days=settings.default_freshness_days,
            include_page_content=include_page_content,
        )
    ).model_dump(mode="json")


@mcp.tool()
def search_freeform_tech_info(
    query: str,
    max_results: int = 5,
    include_page_content: bool = True,
) -> dict:
    """上記カテゴリ外の技術情報を自由形式で検索するラッパ。"""

    payload = SearchFreeformTechInfoInput(query=query, max_results=max_results)
    return client.search_network_knowledge(
        SearchNetworkKnowledgeInput(
            query=payload.query,
            categories=["spec_detail"],
            max_results=payload.max_results,
            language=settings.default_language,
            freshness_days=settings.default_freshness_days,
            include_page_content=include_page_content,
        )
    ).model_dump(mode="json")


def main() -> None:
    """stdio で MCP サーバを起動します。"""

    mcp.run()


if __name__ == "__main__":
    main()
