"""検索クエリ生成ロジック。"""

from search_knowledge_mcp.schemas import Category, SearchNetworkKnowledgeInput

VENDOR_DOMAINS: dict[str, str] = {
    "cisco": "site:cisco.com",
    "yamaha": "site:yamaha.com",
    "fortinet": "site:fortinet.com",
    "juniper": "site:juniper.net",
    "palo alto": "site:paloaltonetworks.com",
    "ubuntu": "site:ubuntu.com",
    "red hat": "site:access.redhat.com",
    "python": "site:python.org",
}

CATEGORY_HINTS: dict[Category, list[str]] = {
    "command_reference": ["command reference", "cli reference", "official documentation"],
    "config_example": ["configuration example", "configuration guide", "example"],
    "spec_detail": ["specification", "limitations", "behavior", "official documentation"],
    "cve": ["CVE", "security advisory", "NVD"],
    "bug": ["bug", "known issues", "resolved caveats"],
    "workaround": ["workaround", "mitigation", "fixed in"],
    "release_note": ["release notes", "new features", "known issues"],
    "update_info": ["latest update", "upgrade notes", "release information"],
}


def normalize_query(payload: SearchNetworkKnowledgeInput) -> str:
    """統合入力を検索しやすい単一文字列へ正規化します。"""

    parts = [payload.device_vendor, payload.device_model, payload.os_version, payload.query]
    return " ".join(part.strip() for part in parts if part and part.strip())


def build_search_queries(payload: SearchNetworkKnowledgeInput) -> list[str]:
    """カテゴリやベンダー情報をもとに複数検索クエリを生成します。"""

    normalized = normalize_query(payload)
    queries: list[str] = [normalized]

    vendor_key = (payload.device_vendor or "").strip().lower()
    domain_hint = VENDOR_DOMAINS.get(vendor_key)

    categories = payload.categories or ["spec_detail"]
    for category in categories:
        hints = CATEGORY_HINTS.get(category, [])
        for hint in hints[:2]:
            query = f"{normalized} {hint}".strip()
            if domain_hint and category in {
                "command_reference",
                "config_example",
                "release_note",
                "update_info",
            }:
                query = f"{query} {domain_hint}"
            queries.append(query)

    unique_queries: list[str] = []
    seen: set[str] = set()
    for query in queries:
        compact = " ".join(query.split())
        if compact and compact not in seen:
            seen.add(compact)
            unique_queries.append(compact)

    return unique_queries
