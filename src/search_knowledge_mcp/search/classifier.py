"""検索結果の簡易分類ロジック。"""

from urllib.parse import urlparse

from search_knowledge_mcp.schemas import Category, ContentKind, SourceType, TrustLevelHint


def classify_source_type(url: str) -> SourceType:
    """URLのドメインから大まかなソース種別を推定します。"""

    hostname = (urlparse(url).hostname or "").lower()
    if not hostname:
        return "unknown"

    security_domains = [
        "nvd.nist.gov",
        "cve.org",
        "cert.org",
        "jvn.jp",
        "osv.dev",
        "ubuntu.com/security",
    ]
    if any(domain in url.lower() for domain in security_domains):
        return "security_advisory"

    documentation_domains = [
        "documentation.ubuntu.com",
        "docs.",
        "developer.",
        "learn.",
    ]
    if any(domain in hostname for domain in documentation_domains):
        return "documentation"

    official_domains = [
        "cisco.com",
        "fortinet.com",
        "juniper.net",
        "yamaha.com",
        "paloaltonetworks.com",
        "openssh.org",
        "ubuntu.com",
        "canonical.com",
    ]
    if any(domain in hostname for domain in official_domains):
        return "official_vendor"

    if any(domain in hostname for domain in ["community.", "forum.", "discuss."]):
        return "community"
    if "kb" in hostname or "support" in hostname:
        return "kb_article"
    return "blog"


def infer_content_kind(source_type: SourceType, title: str, snippet: str) -> ContentKind:
    """結果の内容種別を推定します。"""

    haystack = f"{title} {snippet}".lower()
    if source_type == "security_advisory" or "cve-" in haystack or "vulnerability" in haystack:
        return "security_advisory"
    if "release note" in haystack or "what's new" in haystack or "release notes" in haystack:
        return "release_note"
    if source_type == "kb_article":
        return "knowledge_base"
    if source_type == "community":
        return "community_howto"
    if source_type == "blog":
        return "blog_post"
    if any(
        keyword in haystack
        for keyword in [
            "configuration example",
            "config example",
            "configuration guide",
        ]
    ):
        return "configuration_example"
    if any(
        keyword in haystack for keyword in ["command reference", "cli reference", "reference"]
    ):
        return "reference"
    if any(
        keyword in haystack for keyword in ["specification", "compatibility", "behavior", "limit"]
    ):
        return "specification"
    return "general_information"


def infer_trust_level(
    source_type: SourceType,
    title: str,
    snippet: str,
    has_cve_id: bool,
    has_version_hint: bool,
) -> tuple[TrustLevelHint, str]:
    """クライアントAIが使いやすい信頼度ヒントを返します。"""

    haystack = f"{title} {snippet}".lower()
    if source_type in {"official_vendor", "documentation", "security_advisory"}:
        reason = (
            "公式ドメインまたはセキュリティアドバイザリ由来のため、"
            "一次情報として扱いやすい結果です。"
        )
        if has_cve_id or has_version_hint:
            reason += " さらにCVEやバージョンの手掛かりを含みます。"
        return "high", reason
    if source_type in {"community", "kb_article"}:
        reason = (
            "コミュニティまたはナレッジベース由来です。"
            "実運用の具体例として有用ですが、適用前に公式情報との照合が望まれます。"
        )
        if "example" in haystack or "how to" in haystack or "troubleshoot" in haystack:
            reason += " 設定例やトラブルシュート文脈が含まれる可能性があります。"
        return "medium", reason
    return (
        "low",
        "ブログや一般情報に見えるため、参考情報として扱い、"
        "重要判断には追加の裏取りを推奨します。",
    )


def infer_categories(title: str, snippet: str) -> list[Category]:
    """タイトルとスニペットからカテゴリを推定します。"""

    haystack = f"{title} {snippet}".lower()
    matched: list[Category] = []
    rules: list[tuple[Category, tuple[str, ...]]] = [
        ("command_reference", ("command reference", "cli reference", "command")),
        ("config_example", ("configuration example", "config example", "configuration guide")),
        ("spec_detail", ("specification", "limit", "behavior", "compatibility")),
        ("cve", ("cve-", "cve ", "vulnerability")),
        ("bug", ("bug", "known issue", "resolved caveat")),
        ("workaround", ("workaround", "mitigation", "fixed in")),
        ("release_note", ("release note", "new feature", "what's new")),
        ("update_info", ("update", "upgrade", "firmware", "advisory")),
    ]
    for category, keywords in rules:
        if any(keyword in haystack for keyword in keywords):
            matched.append(category)
    return matched or ["spec_detail"]
