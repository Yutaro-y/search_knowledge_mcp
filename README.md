# 目次
[search-knowledge-mcp](#search-knowledge-mcp)  
[特徴](#特徴)  
[提供ツール](##提供ツール)
[動作要件](##動作要件)  
[セットアップ](##セットアップ)  
[ローカル開発時](##ローカル開発時)  
[パッケージ利用時のtips](###パッケージ利用時の考え方)  
[起動](##起動)  
[LangChain / LangGraph 連携例](##LangChain/LangGraph連携例)  
[ローカルソースコードを使う場合](###ローカルソースコードを使う場合)  
[PyPI / uvx 経由で使う場合 ※今後対応](###PyPI/uvx経由で使う場合※今後対応)  
[環境変数](##環境変数)  
[戻り値で重視している情報](##戻り値で重視している情報)  
[注意事項](##注意事項)  
[テスト](##テスト)  
[開発](##開発)  
[GitHub 公開準備](##GitHub公開準備)  
[PyPI 公開準備](##PyPI公開準備)  
[ライセンス](##ライセンス)



# search-knowledge-mcp

OpenAI Responses API + Web Search を利用して、ネットワーク機器、OS、ライブラリ、CVE、既知バグ、リリースノートなどの**最新技術情報**を収集する MCP サーバです。

## 特徴
- FastMCP ベースの stdio MCP サーバ
- 統合検索ツール `search_network_knowledge`
- 用途別ラッパツールも提供
- 公式ベンダー/公式ドキュメント/PSIRT/NVD を優先しやすい検索クエリ生成
- GitHub / PyPI 公開を見据えた Python パッケージ構成

## 提供ツール
- `search_network_knowledge`
- `search_network_docs`
- `search_os_and_software_specs`
- `search_vulnerabilities_and_bugs`
- `search_release_notes_and_updates`
- `search_freeform_tech_info`

## 動作要件
- Python 3.11+
- uv
- OpenAI API Key

## セットアップ
### ローカル開発時
**原則ローカルで展開して利用**
```bash
cd /home/user/projects/mcpServers/search_knowledge_mcp
cp .env.example .env
# .env に OPENAI_API_KEY を設定
uv sync
```

### パッケージ利用時の考え方
PyPI / `uvx` 経由で利用する場合、`OPENAI_API_KEY` は **MCP クライアントがサーバ起動時に渡す環境変数** から与えることを前提とします。
`.env` はローカル開発や単体動作確認の補助手段です。

## 起動
目的: stdio で MCP サーバを起動する  
期待結果: MCP クライアントからツール一覧取得・ツール呼び出しができる

```bash
uv run python -m search_knowledge_mcp.server
```

PyPI 公開後は、次のような単体起動も想定します。

```bash
OPENAI_API_KEY="your-api-key" uvx search-knowledge-mcp
```

## LangChain/LangGraph連携例
### ローカルソースコードを使う場合
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient(
    {
        "search-knowledge": {
            "command": "/home/user/projects/mcpServers/search_knowledge_mcp/.venv/bin/python",
            "args": ["/home/user/projects/mcpServers/search_knowledge_mcp/src/search_knowledge_mcp/server.py"],
            "env": {
                "OPENAI_API_KEY": "client's API Key" # your API Key
                "OPENAI_MODEL": "model-name" # ex)"gpt-5.0"
                },
            "transport": "stdio"
        }
    }
)
```

### PyPI/uvx経由で使う場合※今後対応
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient(
    {
        "search-knowledge": {
            "command": "uvx",
            "args": ["search-knowledge-mcp"],
            "transport": "stdio",
            "env": {
                "OPENAI_API_KEY": "client's API Key",
                "OPENAI_MODEL": "gpt-4.1-mini",
            },
        }
    }
)
```

この MCP サーバは、クライアントごとに異なる API キーやモデル設定を利用できるよう、`OPENAI_API_KEY` と `OPENAI_MODEL` を起動時環境変数から読む設計です。共有サーバ側に固定キーを埋め込む前提ではありません。

## 環境変数
`.env.example` を参照してください。

主な項目:
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_TIMEOUT_SECONDS`
- `DEFAULT_LANGUAGE`
- `DEFAULT_MAX_RESULTS`
- `DEFAULT_FRESHNESS_DAYS`

優先方針:
- 配布利用: **MCP クライアントが `env` で渡す環境変数を利用**
- ローカル開発: 必要に応じて `.env` を利用

補足:
- `OPENAI_API_KEY` はクライアントごとに異なる値を渡せます
- `OPENAI_MODEL` もクライアント側 `env` から上書きできます
- `OPENAI_API_KEY`が超重要です。ほかは"env"に設定しなくてよいです。モデルのアップデートを加味して`OPENAI_MODEL` も上書きできるようにしています。
- `.env` はローカルで `uv run ...` する際の補助であり、配布利用の必須要件ではありません
## 戻り値で重視している情報
各 `results[]` には、クライアントAIがソースの性質を判断しやすいよう、以下を含めます。

- `url`: どのURLを参照したか
- `source_type`: 公式、セキュリティアドバイザリ、コミュニティ、ブログなどの大分類
- `content_kind`: リファレンス、設定例、リリースノート、コミュニティHowToなどの内容種別
- `content_observation`: そのURLから得られた要点の短い観測結果
- `extracted_facts`: URL本文から抽出した要点
- `possible_commands`: URL本文から見つかったコマンド候補
- `possible_procedures`: URL本文から見つかった手順候補
- `important_notes`: 注意点や制約の候補
- `source_excerpt`: URL本文の抜粋
- `page_content_summary`: 本文取得結果の件数要約
- `recommended_usage`: クライアントAI向けの利用方針ヒント
- `trust_level_hint`: `high` / `medium` / `low`
- `why_this_trust_level`: その信頼度ヒントの理由
- `trust_signals`: ドメイン、CVE有無、バージョン手掛かり、公式性などの簡易シグナル

これにより、クライアント側AIは「公式情報として強く採用する」「コミュニティ記事として参考値に留める」などの判断を行いやすくなります。

また、各ツールは `include_page_content` 引数を受け付けます。既定値は `true` で、検索結果URLの本文取得と構造化抽出を行います。速度や切り分けを優先したい場合のみ `false` を指定してください。

## 注意事項
- URL の生存確認を HTTP レベルで厳密検証する構成ではなく、まずは OpenAI Web Search の取得結果と構造化を優先しています。
- 今後、HEAD/GET による URL 再検証レイヤを追加する余地があります。
- Web 検索結果の実際の構造は OpenAI API 側の更新で変化しうるため、`parser.py` は壊れにくさを重視した実装にしています。
- `OPENAI_API_KEY` はクライアントごとに異なる値を渡せるよう、MCP クライアント設定の `env` から注入する運用を推奨します。
- `OPENAI_MODEL` もクライアント要件に応じて `env` から上書き可能です。
- API キーを README やコード例へ直書きしたまま共有しないでください。

## テスト
目的: 検索クエリ生成の基本動作を確認する  
期待結果: テスト成功

```bash
uv run pytest
```

## 開発
目的: lint を実行する  
期待結果: Ruff のエラーが出ない

```bash
uv run ruff check .
```

## GitHub公開準備
最低限、以下を置いています。
- `.gitignore`
- `LICENSE`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `.github/workflows/ci.yml`

公開前に差し替える項目:
- `pyproject.toml` の `authors`
- `pyproject.toml` の `project.urls`
- README 内の公開先URL

## PyPI公開準備
目的: ビルド成果物を作成する  
期待結果: `dist/` 配下に wheel / sdist が生成される

```bash
uv build
```

公開時の代表例:
```bash
uv tool install twine
uv run twine check dist/*
uv run twine upload dist/*
```

※ 実際の公開時には PyPI API Token を利用してください。

## ライセンス
MIT
