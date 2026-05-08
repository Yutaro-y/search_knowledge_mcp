"""URL本文から、クライアントAIが扱いやすい構造化情報を抽出する処理。"""

import re

from search_knowledge_mcp.search.content_extractor import normalize_text_for_output

COMMAND_PATTERN = re.compile(r"(?m)^(?:\s{0,8})[a-z][a-z0-9_-]*(?:\s+[\w./:-]+){0,6}$")
INLINE_COMMAND_PATTERN = re.compile(
    r"(?i)\b(hostname\s+[\w.-]+|host\s+name\s+[\w.-]+|set\s+[\w./:-]+(?:\s+[\w./:-]+){0,5})\b"
)
HOSTNAME_LINE_PATTERN = re.compile(r"(?i)(host\s*name|hostname|ホスト名|機器名)")
BULLET_SPLIT_PATTERN = re.compile(r"(?:^|\n)(?:\d+[.)]|[-*・])\s+")


def _split_sentences(text: str) -> list[str]:
    raw_parts = re.split(r"(?<=[。.!?])\s+", text)
    return [part.strip() for part in raw_parts if part.strip()]


def analyze_page_content(text: str, title: str, url: str) -> dict[str, object]:
    """本文から、要点・コマンド・手順・注意点を雑にでも構造化します。"""

    normalized_text = normalize_text_for_output(text, max_consecutive_newlines=1)
    sentences = _split_sentences(normalized_text[:8000])
    extracted_facts: list[str] = []
    possible_commands: list[str] = []
    possible_procedures: list[str] = []
    important_notes: list[str] = []

    for sentence in sentences:
        lowered = sentence.lower()
        if HOSTNAME_LINE_PATTERN.search(sentence) and len(extracted_facts) < 6:
            extracted_facts.append(sentence[:220])
        if (
            any(keyword in lowered for keyword in ["注意", "note", "caution", "制限", "補足"])
            and len(important_notes) < 4
        ):
            important_notes.append(sentence[:220])
        if (
            any(
                keyword in lowered
                for keyword in [
                    "手順",
                    "設定",
                    "click",
                    "入力",
                    "保存",
                    "ログイン",
                    "configure",
                    "set ",
                ]
            )
            and len(possible_procedures) < 6
        ):
            possible_procedures.append(sentence[:220])

    for line in normalized_text.splitlines():
        candidate = line.strip()
        if not candidate or len(candidate) > 180:
            continue
        if COMMAND_PATTERN.match(candidate) and any(
            token in candidate.lower()
            for token in ["host", "name", "set", "ip", "show", "configure"]
        ):
            if candidate not in possible_commands and len(possible_commands) < 8:
                possible_commands.append(candidate)

        for match in INLINE_COMMAND_PATTERN.findall(candidate):
            normalized_match = match.strip()
            if normalized_match not in possible_commands and len(possible_commands) < 8:
                possible_commands.append(normalized_match)

    if not possible_procedures:
        bullet_chunks = [
            part.strip()
            for part in BULLET_SPLIT_PATTERN.split(normalized_text[:5000])
            if part.strip()
        ]
        for chunk in bullet_chunks[:6]:
            if len(chunk) >= 20:
                possible_procedures.append(chunk[:220])

    source_excerpt = normalize_text_for_output(normalized_text[:800], max_consecutive_newlines=1)
    content_observation = (
        f"このURLは『{title}』に関する本文を含み、"
        f"{('設定手順' if possible_procedures else '補足説明')}"
        f"{('やコマンド例' if possible_commands else '')}"
        "を抽出できる可能性があります。"
    )
    page_content_summary = (
        f"本文取得{('済み' if text else '未取得')}。"
        f" 抽出fact {len(extracted_facts)}件、手順 {len(possible_procedures)}件、"
        f"コマンド候補 {len(possible_commands)}件、注意点 {len(important_notes)}件。"
    )
    recommended_usage = (
        "公式マニュアルとして一次参照に使い、抽出された手順やコマンド候補は"
        "対象機種・画面項目・CLI体系に照らして確認してください。"
    )

    if not extracted_facts:
        extracted_facts.append(f"ページ本文を取得しました。対象URL: {url}")

    extracted_facts = [normalize_text_for_output(item) for item in extracted_facts]
    possible_commands = [normalize_text_for_output(item) for item in possible_commands]
    possible_procedures = [normalize_text_for_output(item) for item in possible_procedures]
    important_notes = [normalize_text_for_output(item) for item in important_notes]
    content_observation = normalize_text_for_output(content_observation)
    page_content_summary = normalize_text_for_output(page_content_summary)
    recommended_usage = normalize_text_for_output(recommended_usage)

    return {
        "content_observation": content_observation,
        "extracted_facts": extracted_facts,
        "possible_commands": possible_commands,
        "possible_procedures": possible_procedures,
        "important_notes": important_notes,
        "source_excerpt": source_excerpt,
        "page_content_summary": page_content_summary,
        "recommended_usage": recommended_usage,
        "page_content_available": True,
    }
