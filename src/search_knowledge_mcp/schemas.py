"""MCPツールの入出力スキーマ定義。"""

from datetime import UTC, datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, HttpUrl, model_validator

from search_knowledge_mcp.search.content_extractor import normalize_text_for_output

Category = Literal[
    "command_reference",
    "config_example",
    "spec_detail",
    "cve",
    "bug",
    "workaround",
    "release_note",
    "update_info",
]

SourceType = Literal[
    "official_vendor",
    "security_advisory",
    "documentation",
    "community",
    "blog",
    "kb_article",
    "unknown",
]

ContentKind = Literal[
    "reference",
    "configuration_example",
    "specification",
    "security_advisory",
    "release_note",
    "knowledge_base",
    "community_howto",
    "blog_post",
    "general_information",
]

TrustLevelHint = Literal["high", "medium", "low"]


class SearchMetadata(BaseModel):
    vendor: str | None = None
    product: str | None = None
    version: str | None = None
    cve_id: str | None = None
    severity: str | None = None
    published_date: str | None = None
    fixed_in: str | None = None


class SearchResultItem(BaseModel):
    title: str
    url: HttpUrl | str
    source_type: SourceType = "unknown"
    content_kind: ContentKind = "general_information"
    categories: list[Category] = Field(default_factory=list)
    summary: str
    raw_snippet: str = ""
    content_observation: str = ""
    extracted_facts: list[str] = Field(default_factory=list)
    possible_commands: list[str] = Field(default_factory=list)
    possible_procedures: list[str] = Field(default_factory=list)
    important_notes: list[str] = Field(default_factory=list)
    source_excerpt: str = ""
    page_content_summary: str = ""
    recommended_usage: str = ""
    page_fetch_status: str = "not_fetched"
    page_content_available: bool = False
    trust_level_hint: TrustLevelHint = "medium"
    why_this_trust_level: str = ""
    trust_signals: dict[str, str | bool | None] = Field(default_factory=dict)
    metadata: SearchMetadata = Field(default_factory=SearchMetadata)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def normalize_text_fields(self) -> Self:
        """可読性を損なう連続改行や余分な空白を返却前に整えます。"""

        self.title = normalize_text_for_output(self.title)
        self.summary = normalize_text_for_output(self.summary)
        self.raw_snippet = normalize_text_for_output(self.raw_snippet)
        self.content_observation = normalize_text_for_output(self.content_observation)
        self.source_excerpt = normalize_text_for_output(self.source_excerpt)
        self.page_content_summary = normalize_text_for_output(self.page_content_summary)
        self.recommended_usage = normalize_text_for_output(self.recommended_usage)
        self.why_this_trust_level = normalize_text_for_output(self.why_this_trust_level)
        self.extracted_facts = [
            normalize_text_for_output(item) for item in self.extracted_facts
        ]
        self.possible_commands = [
            normalize_text_for_output(item) for item in self.possible_commands
        ]
        self.possible_procedures = [
            normalize_text_for_output(item) for item in self.possible_procedures
        ]
        self.important_notes = [
            normalize_text_for_output(item) for item in self.important_notes
        ]
        return self


class ErrorInfo(BaseModel):
    type: str
    message: str


class SearchResponse(BaseModel):
    query: str
    normalized_query: str
    results: list[SearchResultItem] = Field(default_factory=list)
    fetched_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    notes_for_llm: str = ""
    error: ErrorInfo | None = None


class SearchNetworkKnowledgeInput(BaseModel):
    query: str = Field(description="自由形式の技術検索クエリ")
    device_vendor: str | None = Field(default=None, description="Cisco, YAMAHA, Fortinet などメーカー名を示す")
    device_model: str | None = Field(default=None, description="IOS-XE, RTX830, FortiGate などメーカー製品モデルを示す。型番やシリーズ名など。")
    os_version: str | None = Field(default=None, description="17.9.3, 7.4.4, Ubuntu 24.04 などOSやファームウェアバージョンを示す")
    categories: list[Category] = Field(default_factory=list)
    max_results: int = Field(default=8, ge=1, le=20)
    language: Literal["ja", "en", "auto"] = "auto"
    freshness_days: int = Field(default=365, ge=1, le=3650)
    include_page_content: bool = Field(
        default=True,
        description="検索結果URLの本文取得と構造化抽出を行うかどうか。原則ONで、必要時のみOFFにできます。",
    )


class SearchNetworkDocsInput(BaseModel):
    vendor: str
    product_family: str | None = None # 製品ファミリーやシリーズ名を示す。例: Catalyst, Aironet, ASA, NVRなど
    version: str | None = None
    query: str
    max_results: int = Field(default=5, ge=1, le=20)


class SearchOsAndSoftwareSpecsInput(BaseModel):
    target_name: str
    category: str | None = None
    query: str
    max_results: int = Field(default=5, ge=1, le=20)


class SearchVulnerabilitiesAndBugsInput(BaseModel):
    product: str
    version: str | None = None
    cve_id: str | None = None
    query: str | None = None
    max_results: int = Field(default=10, ge=1, le=50)

    @model_validator(mode="after")
    def validate_query_or_cve(self) -> Self:
        if not self.cve_id and not self.query:
            raise ValueError("Either cve_id or query must be specified.")
        return self


class SearchReleaseNotesAndUpdatesInput(BaseModel):
    product: str
    current_version: str | None = None
    target_version: str | None = None
    query: str | None = None
    max_results: int = Field(default=5, ge=1, le=20)


class SearchFreeformTechInfoInput(BaseModel):
    query: str
    max_results: int = Field(default=5, ge=1, le=20)
