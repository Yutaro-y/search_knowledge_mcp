from search_knowledge_mcp.clients.fetch_client import PageFetchClient
from search_knowledge_mcp.config import Settings
from search_knowledge_mcp.schemas import SearchNetworkKnowledgeInput
from search_knowledge_mcp.search.classifier import infer_content_kind, infer_trust_level
from search_knowledge_mcp.search.content_extractor import (
    extract_text_from_html,
    normalize_text_for_output,
)
from search_knowledge_mcp.search.page_analyzer import analyze_page_content
from search_knowledge_mcp.search.query_builder import build_search_queries, normalize_query


def test_normalize_query_includes_major_fields() -> None:
    payload = SearchNetworkKnowledgeInput(
        query="BGP configuration example",
        device_vendor="Cisco",
        device_model="IOS-XE",
        os_version="17.9.3",
        categories=["command_reference"],
    )
    normalized = normalize_query(payload)
    assert "Cisco" in normalized
    assert "IOS-XE" in normalized
    assert "17.9.3" in normalized
    assert "BGP configuration example" in normalized


def test_build_search_queries_adds_vendor_domain_hint() -> None:
    payload = SearchNetworkKnowledgeInput(
        query="OSPF",
        device_vendor="Cisco",
        device_model="IOS-XE",
        categories=["command_reference"],
    )
    queries = build_search_queries(payload)
    assert any("site:cisco.com" in query for query in queries)
    assert len(queries) >= 2


def test_settings_normalize_empty_openai_base_url_to_none() -> None:
    settings = Settings(
        OPENAI_API_KEY="dummy",
        OPENAI_BASE_URL="   ",
    )
    assert settings.openai_base_url is None


def test_settings_default_openai_base_url_defaults_to_openai_endpoint() -> None:
    settings = Settings(OPENAI_API_KEY="dummy")
    assert settings.openai_base_url == "https://api.openai.com/v1"


def test_infer_content_kind_and_trust_level_for_community_example() -> None:
    content_kind = infer_content_kind(
        "community",
        "How to configure OSPF on Cisco IOS-XE",
        "community example and troubleshooting notes",
    )
    trust_level, reason = infer_trust_level(
        source_type="community",
        title="How to configure OSPF on Cisco IOS-XE",
        snippet="community example and troubleshooting notes",
        has_cve_id=False,
        has_version_hint=True,
    )
    assert content_kind == "community_howto"
    assert trust_level == "medium"
    assert "コミュニティ" in reason


def test_extract_and_analyze_page_content_finds_hostname_steps() -> None:
    raw_html = """
    <html>
      <body>
        <h1>YAMAHA 設定例</h1>
        <p>ホスト名を設定します。</p>
        <ul>
          <li>管理画面にログインします。</li>
          <li>機器名の設定画面を開きます。</li>
          <li>hostname RTX1300 を入力して保存します。</li>
        </ul>
      </body>
    </html>
    """
    text = extract_text_from_html(raw_html)
    analyzed = analyze_page_content(
        text=text,
        title="YAMAHA 設定例",
        url="https://example.com/yamaha",
    )
    assert analyzed["page_content_available"] is True
    assert analyzed["possible_procedures"]
    assert any("hostname" in command.lower() for command in analyzed["possible_commands"])


def test_page_fetch_client_decodes_cp932_html() -> None:
    client = PageFetchClient()
    html_text = (
        "<html><head><meta charset=\"Shift_JIS\"></head>"
        "<body>ホスト名を変更します。</body></html>"
    )
    encoded = html_text.encode("cp932")

    decoded = client._decode_response_content(  # noqa: SLF001
        content=encoded,
        content_type="text/html",
        apparent_encoding=None,
    )

    assert "ホスト名を変更します" in decoded


def test_normalize_text_for_output_collapses_excessive_blank_lines() -> None:
    text = "見出し\n\n\n\n本文1\n\n\n本文2\n"
    normalized = normalize_text_for_output(text)
    assert normalized == "見出し\n本文1\n本文2"
