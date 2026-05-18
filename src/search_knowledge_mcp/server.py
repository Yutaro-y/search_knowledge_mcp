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
    An integrated cross-domain search tool for network devices, operating systems, CVEs, release notes, and related technical information.

    Parameters:
        query (str):
            The search keyword. This parameter is mandatory for every request.

        device_vendor (str | None):
            The vendor/manufacturer name of the device.
            Default: None

        device_model (str | None):
            The model or product name/number of the device.
            Default: None

        os_version (str | None):
            The OS version corresponding to the specified "device_model".
            Default: None

        categories (list[str] | None):
            A list of categories to filter the search.  
            If None, all categories are included.  
            Default: None  
            Available categories:
                - `command_reference`
                - `config_example`
                - `spec_detail`
                - `cve`
                - `bug`
                - `workaround`
                - `release_note`
                - `update_info`

        max_results (int):
            The number of target URLs to collect using "OpenAI_API + Web Search".
            Default: 8

        language (str):
            The language used for searching.  
            The policy is to gather information broadly across multiple languages.  
            Default: "auto"

        freshness_days (int):
            The "freshness" threshold of the information, specified in days.  
            Only content published within the specified number of days will be included.  
            For topics that inherently involve older information—such as legacy devices, OS versions, or firmware—set this value sufficiently high.  
            Default: 365

        include_page_content (bool):
            Whether to fetch and structurally extract the body content of each result URL.  
            This should generally remain enabled.  
            Default: True
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
    product_family: str | None = None, # 製品ファミリーやシリーズ名を示す。例: Catalyst, Aironet, ASA, NVRなど
    version: str | None = None,
    max_results: int = 5,
    include_page_content: bool = True,
) -> dict:
    """
    NW機器のコマンドリファレンス・設定例・公式ドキュメントを検索するラッパ。
    Seaching Reference, Configuration Examples, Official Documentation, and other Documentation/informaition for Network Devices.
    Parameters:
        vendor (str):
            The vendor/manufacturer name of the device.  
            Example: Cisco, YAMAHA, Fortinet

        query (str):
            The search keyword. This parameter is mandatory for every request.
            
        product_family (str | None):
            The product family or series name of the device.  
            Example: Catalyst, Aironet, ASA, NVR, Yamaha_RTX, etc. "None" for default.
            Default: None
        
        version (str | None):
            The version(mainly for OS versions) corresponding to the specified "product_family".
            Default: None
        
        max_results (int):
            The number of target URLs to collect using "OpenAI_API + Web Search".
            Default: 8
            
        include_page_content (bool):
            Whether to fetch and structurally extract the body content of each result URL.  
            This should generally remain enabled.  
            Default: True
    """

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
    """
    OS、ライブラリ、SDKなどの仕様・制約・設定例を検索するラッパ。
    Searching technical specifications. Using for OS, libraries, SDKs, and other software. This can include details such as supported features, configuration examples, limitations, and best practices.
    
    Parameters:
        target_name (str):
            The name of the target OS, library, or SDK for which to search specifications.
        query (str):
            The search keyword. This parameter is mandatory for every request.
        categories (list[str] | None):
            A list of categories to filter the search.  
            If None, all categories are included.  
            Default: None  
            Available categories:
                - `command_reference`
                - `config_example`
                - `spec_detail`
                - `cve`
                - `bug`
                - `workaround`
                - `release_note`
                - `update_info`
        max_results (int):
            The number of target URLs to collect using "OpenAI_API + Web Search".
            Default: 5
        include_page_content (bool):
            Whether to fetch and structurally extract the body content of each result URL.  
            This should generally remain enabled.  
            Default: True
    """

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
    """
    CVE、既知バグ、回避策、修正版情報を検索するラッパ。
    Searching CVEs, known bugs, workarounds, and patch information. This can include vulnerability details, affected versions, mitigation strategies, and links to official advisories or community discussions.
    parameters:
        product (str):
            The product name for which to search vulnerabilities or bugs.
            example: "Cisco IOS-XE", "FortiGate", "Yamaha RTX830", "Ubuntu 24.04LTS", "Windows11 pro", "Docker", "Apache", "pyMuPDF", etc.
        version (str | None):
            The version associated with the product. This can help narrow down the search to specific vulnerabilities or bugs that affect that version.
            example: "17.9.3", "7.4.4", "20H2", "3.0.0", etc.
        cve_id (str | None):
            A specific CVE ID to search for, such as "CVE-2024-12345". If provided, the search will focus on this particular vulnerability.
        query (str | None):
            free keywords to add to the search. This can include specific features, components, or other relevant terms to further refine the search results.
        max_results (int):
            The number of target URLs to collect using "OpenAI_API + Web Search".
            Default: 10
        include_page_content (bool):
            Whether to fetch and structurally extract the body content of each result URL.  
            This should generally remain enabled.  
            Default: True
    """

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
    """
    リリースノート、アップデート、仕様変更情報を検索するラッパ。
    Searching release notes, updates, and specification changes. This can include information about new features, bug fixes, deprecations, and other changes introduced in different versions of a product.
    parameters:
        product (str):
            The product name for which to search release notes or updates.
            example: "Cisco IOS-XE", "FortiGate", "Yamaha RTX830", "Ubuntu 24.04LTS", "Windows11 pro", "Docker", "Apache", "pyMuPDF", etc.
        current_version (str | None):
            The current version of the product that the user is using. This can help identify relevant updates or release notes that pertain to the user's existing setup.
            example: "17.9.3", "7.4.4", "20H2", "3.0.0", etc.
        target_version (str | None):
            The specific version that the user is interested in upgrading to or learning about. This can help focus the search on release notes or updates that are relevant to the target version.
            example: "17.10.1", "7.5.0", "21H1", "3.1.0", etc.
        query (str | None):
            free keywords to add to the search. This can include specific features, components, or other relevant terms to further refine the search results.
        max_results (int):
            The number of target URLs to collect using "OpenAI_API + Web Search".
            Default: 5
        include_page_content (bool):
            Whether to fetch and structurally extract the body content of each result URL.  
            This should generally remain enabled.  
            Default: True
    """

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
