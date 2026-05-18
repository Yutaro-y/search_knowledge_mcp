# OpenAI Web Searchで最新技術情報を引けるMCPサーバを作ってみた

## はじめに
LLM にネットワーク機器のコマンド、既知脆弱性、リリースノート、ライブラリ仕様を聞くと、どうしても学習時点の知識に引っ張られます。

特に以下のような情報は、できるだけ**最新の一次情報**に当たりたい場面が多いです。

- NW 機器のコマンドリファレンス
- ベンダー公式の設定例
- OS / ライブラリ / SDK の最新仕様
- CVE / 既知バグ / workaround / fixed-in
- リリースノート / 更新情報 / 仕様変更

そこで今回は、**OpenAI Responses API + Web Search** を使って、最新技術情報を検索できる MCP サーバ **`search-knowledge-mcp`** を作ってみました。

このサーバは、単に検索結果の文字列を返すだけではなく、**URL、ソース種別、信頼度ヒント、本文由来の要点**まで含む構造化 JSON を返すようにしています。

---

## 作ったもの
今回作ったのは、Python 製の MCP サーバ **`search-knowledge-mcp`** です。

- 配布名: `search-knowledge-mcp`
- import 名: `search_knowledge_mcp`
- 実行コマンド: `search-knowledge-mcp`

MCP クライアントから stdio で起動して使う前提です。

### できること
- NW 機器のコマンドリファレンス検索
- 設定例の検索
- OS / ライブラリ / SDK の仕様検索
- CVE / バグ / workaround / fixed-in の検索
- リリースノート / 更新情報 / 仕様変更の検索
- その他自由形式の技術検索

### 提供ツール
- `search_network_knowledge`
- `search_network_docs`
- `search_os_and_software_specs`
- `search_vulnerabilities_and_bugs`
- `search_release_notes_and_updates`
- `search_freeform_tech_info`

---

## どんな課題を解きたかったか
普通に Web 検索 API を叩いて文字列を返すだけでも MCP サーバとしては成立します。

ただ、エージェントに使わせることを考えると、以下の情報があった方が圧倒的に扱いやすいです。

- どの URL を見たのか
- それが公式情報か、コミュニティ情報か
- どのカテゴリの情報か
- 本文取得に成功したか
- 本文から何を抽出できたか
- どの程度信頼してよさそうか

そのため今回は、検索結果をそのまま返すのではなく、**LLM エージェントが根拠付きで判断しやすい構造**へ寄せました。

---

## アーキテクチャ
構成は以下です。

- MCP 実装: FastMCP
- Transport: stdio
- 言語: Python 3.11+
- パッケージ管理: uv
- 検索基盤: OpenAI Responses API + `web_search_preview`
- 設定管理: `pydantic-settings`
- 本文取得: `httpx`
- 入出力検証: Pydantic v2

### 現在のディレクトリ構成

```text
search_knowledge_mcp/
├─ .env
├─ .env.example
├─ .github/
│  └─ workflows/
│     └─ ci.yml
├─ CHANGELOG.md
├─ CONTRIBUTING.md
├─ LICENSE
├─ README.md
├─ docs/
│  ├─ qiita_article.md
│  └─ 仕様書.md
├─ pyproject.toml
├─ src/
│  └─ search_knowledge_mcp/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ logging_utils.py
│     ├─ schemas.py
│     ├─ server.py
│     ├─ clients/
│     │  ├─ fetch_client.py
│     │  └─ openai_client.py
│     ├─ search/
│     │  ├─ classifier.py
│     │  ├─ content_extractor.py
│     │  ├─ page_analyzer.py
│     │  ├─ parser.py
│     │  └─ query_builder.py
│     └─ tools/
├─ tests/
│  └─ test_query_builder.py
└─ uv.lock
```

ポイントは、**検索 API 呼び出し、URL 本文取得、HTML 抽出、本文解析、返却整形** を分離していることです。

---

## 実装方針
### 1. 統合ツールと用途別ラッパを両方用意する
人間が触るときと、エージェントが ReAct 的に使うときでは、欲しいツール粒度が少し違います。

そのため、なんでも横断検索できる `search_network_knowledge` に加えて、用途別ラッパも用意しました。

- ドキュメント検索向け
- 仕様検索向け
- 脆弱性・バグ向け
- リリースノート向け
- 自由検索向け

### 2. OpenAI Web Search の返却をそのまま返さない
生の検索結果文字列だけだと、エージェント側での再解釈が必要になります。

そこで、返却時には例えば以下のような情報を含めます。

- `title`
- `url`
- `source_type`
- `content_kind`
- `categories`
- `summary`
- `content_observation`
- `page_fetch_status`
- `page_content_available`
- `trust_level_hint`
- `why_this_trust_level`
- `trust_signals`
- `metadata`

これにより、クライアント側 AI が

- 公式ベンダー資料を強く採用する
- セキュリティアドバイザリを優先する
- コミュニティ記事は補助情報として使う

といった判断をしやすくなります。

### 3. 検索結果 URL の本文も取りにいく
今回の実装では、検索結果 URL をたどって本文を取得し、そこから追加情報を抽出します。

具体的には以下を行っています。

- HTTP GET で本文取得
- HTML からプレーンテキスト抽出
- 要点 / コマンド候補 / 手順候補 / 注意点の抽出
- `source_excerpt` や `page_content_summary` の生成

このあたりは `fetch_client.py`、`content_extractor.py`、`page_analyzer.py` に分離しています。

### 4. 日本語ページの文字化け対策を入れる
意外と効いたのがここです。

本文取得時に `response.text` 任せだと、日本語ページで文字化けすることがありました。そこで、以下の順でデコード候補を組み立てるようにしました。

- `Content-Type` の charset
- HTML の `meta charset`
- apparent encoding
- fallback (`utf-8`, `cp932`, `shift_jis`, `euc_jp`, `iso2022_jp`, `latin-1`)

これにより、日本語マニュアル系ページの扱いがかなり安定しました。

### 5. 改行や余分な空白も返却前に正規化する
HTML 由来の本文は、どうしても改行や空白が荒れがちです。

そのため、返却前に `normalize_text_for_output` で以下を行っています。

- 改行コードの統一
- 連続改行の圧縮
- 余分な空白の削除
- 配列要素も含めた一括正規化

地味ですが、クライアント UI や LLM が結果を扱う上でかなり効きます。

---

## セットアップ
### ローカル開発時
ローカル開発では `.env` を使えます。

```bash
cd /home/user/projects/mcpServers/search_knowledge_mcp
cp .env.example .env
# .env に OPENAI_API_KEY を設定
uv sync
```

### 配布利用時の考え方
ここは今回かなり大事にしたポイントです。

**本番/配布利用では env 優先、`.env` は開発補助** という方針にしています。

つまり、PyPI / `uvx` 経由で使う場合は、MCP クライアントがサーバ起動時に環境変数を渡す前提です。

不特定多数のクライアントが、それぞれ異なる API キーやモデルを使えるようにするためです。

---

## 起動方法
### ローカルソースコードから起動
```bash
uv run python -m search_knowledge_mcp.server
```

### PyPI / `uvx` 経由で起動
```bash
OPENAI_API_KEY="your-api-key" uvx search-knowledge-mcp
```

モデルを明示したい場合は、`OPENAI_MODEL` も渡せます。

```bash
OPENAI_API_KEY="your-api-key" OPENAI_MODEL="gpt-4.1-mini" uvx search-knowledge-mcp
```

---

## LangChain / LangGraph から使う
### ローカルソースコードを使う場合
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient(
    {
        "search-knowledge": {
            "command": "/home/user/projects/mcpServers/search_knowledge_mcp/.venv/bin/python",
            "args": ["/home/user/projects/mcpServers/search_knowledge_mcp/src/search_knowledge_mcp/server.py"],
            "transport": "stdio",
            "env": {
                "OPENAI_API_KEY": "client's API Key",
                "OPENAI_MODEL": "gpt-4.1-mini",
            },
        }
    }
)
```

### PyPI / `uvx` 経由で使う場合
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

この構成にしておくと、各クライアントが自分の `OPENAI_API_KEY` / `OPENAI_MODEL` を使えます。

つまり、サーバ側に固定キーを埋め込む必要がありません。

---

## 戻り値で意識したこと
各 `results[]` には、クライアント側 AI がソースを評価しやすいよう、以下のような情報を入れています。

- `url`: 参照先 URL
- `source_type`: 公式、セキュリティアドバイザリ、コミュニティ、ブログなど
- `content_kind`: リファレンス、設定例、仕様、リリースノートなど
- `content_observation`: その URL から得られた内容の短い説明
- `extracted_facts`: 本文から抽出した要点
- `possible_commands`: 本文から見つかったコマンド候補
- `possible_procedures`: 本文から見つかった手順候補
- `important_notes`: 注意点や制約
- `source_excerpt`: 本文抜粋
- `page_content_summary`: 本文取得結果の要約
- `recommended_usage`: どう使うとよいかのヒント
- `trust_level_hint`: `high` / `medium` / `low`
- `why_this_trust_level`: その理由
- `trust_signals`: ドメイン、CVE、有無、バージョン手掛かりなど

これにより、エージェントに「まず公式ソースを優先して採用して」と指示しやすくなりました。

---

## include_page_content の考え方
各ツールには `include_page_content` を持たせています。

- 既定値は `true`
- 通常は本文取得込みで使う
- 速度重視や原因切り分け時だけ `false`

本文取得と本文解析があることで、単なる検索結果一覧よりかなり実用的になります。

---

## 実装してみてよかった点
### 1. 公式情報とコミュニティ情報の区別を返せる
単なる検索ではなく、`source_type` や `trust_level_hint` を返すことで、エージェントが判断しやすくなりました。

### 2. URL 本文取得が想像以上に効く
タイトルとスニペットだけでは拾えない、具体的な手順やコマンド候補を補えるようになりました。

### 3. 文字コード対策と改行正規化が地味に重要
AI の推論品質だけでなく、クライアント画面での可読性にも効きました。

---

## 現時点の課題
まだ改善余地もあります。

- URL の HTTP HEAD / GET による厳密な生存確認
- ベンダー別のドメイン辞書強化
- CVE / JVN / NVD 向け抽出精度の改善
- キャッシュやレート制御
- HTML 本文抽出のノイズ除去強化
- README や PyPI メタデータの継続改善

---

## テストと品質確認
最低限の品質確認として、以下を通しています。

```bash
uv run pytest
uv run ruff check .
uv build
```

CI でもこれらを回す構成にしています。

---

## PyPI 公開を見据えた構成
このプロジェクトは、GitHub / PyPI 公開を見据えた Python パッケージ構成になっています。

- `pyproject.toml`
- `README.md`
- `LICENSE`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `.github/workflows/ci.yml`
- `project.scripts` による CLI エントリポイント

CLI は以下です。

```toml
[project.scripts]
search-knowledge-mcp = "search_knowledge_mcp.server:main"
```

このため、公開後は `uvx search-knowledge-mcp` でそのまま起動できる想定です。

---

## まとめ
OpenAI Web Search を使うと、MCP サーバでも「最新情報を根拠付きで引く」体験がかなり作りやすいと感じました。

今回の `search-knowledge-mcp` では、

- 最新情報を検索できる
- 構造化 JSON で返せる
- URL 本文まで補強できる
- 公式性や信頼度のヒントを返せる
- PyPI / `uvx` 経由で配布しやすい
- クライアントごとに異なる API キー / モデルを使える

というあたりを重視しています。

MCP サーバを「単なる API ラッパ」ではなく、**エージェントが判断しやすい情報整形レイヤ**として設計したい場合に、かなり相性の良い構成でした。

今後は、URL 検証レイヤやベンダー別抽出強化を足して、さらに実運用寄りにしていきたいです。

---

## リポジトリ
https://github.com/Yutaro-y/search_knowledge_mcp

## PyPI
※ 公開後に URL を追記予定
