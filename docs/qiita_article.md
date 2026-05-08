# OpenAI Web Searchで最新技術情報を引けるMCPサーバを作ってみた

## はじめに
LLMにネットワーク機器のコマンドやCVE、リリースノートを聞くと、どうしても学習時点の情報に引っ張られます。

そこで今回は、**OpenAI Responses API + Web Search** を使って、
**Cisco / YAMAHA / Fortinet / Juniper / Ubuntu / Python / CVE / リリースノート** などの最新情報を引ける MCP サーバを作ってみました。

この記事では、以下を目標に実装しています。
- 最新の公式情報を検索できる
- LangGraph / LangChain から MCP ツールとして呼べる
- 統合検索 + 用途別ラッパで使いやすい
- 後で GitHub / PyPI に公開しやすい構成にする

---

## 作ったもの
今回作ったのは `search-knowledge-mcp` という Python 製の MCP サーバです。

### できること
- NW機器のコマンドリファレンス検索
- 設定例の検索
- OS / ライブラリ / SDK の仕様検索
- CVE / バグ / workaround / fixed-in の検索
- リリースノート / 更新情報 / 仕様変更の検索
- その他自由形式の技術検索

### 公開ツール
- `search_network_knowledge`
- `search_network_docs`
- `search_os_and_software_specs`
- `search_vulnerabilities_and_bugs`
- `search_release_notes_and_updates`
- `search_freeform_tech_info`

---

## 背景
普通のMCPサーバ実装であれば、単に検索APIを叩いて文字列を返すだけでも動きます。

ただ、今回やりたかったのは、**LLMエージェントがそのまま判断材料に使いやすい形** にすることでした。

つまり、単に検索結果一覧を返すのではなく、最低限以下が欲しかったです。
- URL
- 公式かどうか
- 何のカテゴリか（command reference / cve / release note など）
- バージョン
- CVE ID
- fixed-in
- 要約

このあたりを JSON で返せると、LangGraph の ReAct エージェントがかなり扱いやすくなります。

---

## 構成
```text
search_knowledge_mcp/
├─ pyproject.toml
├─ .env.example
├─ README.md
├─ docs/
├─ src/
│  └─ search_knowledge_mcp/
│     ├─ server.py
│     ├─ config.py
│     ├─ schemas.py
│     ├─ clients/openai_client.py
│     └─ search/
│        ├─ query_builder.py
│        ├─ classifier.py
│        └─ parser.py
└─ tests/
```

### ここでこのスクショを投入予定
- ディレクトリ構成のツリー

---

## 実装方針
ポイントは以下です。

### 1. MCPサーバ本体は FastMCP
Python で MCP を作るなら、まずは FastMCP ベースが扱いやすいです。
今回は stdio で起動する構成にしました。

### 2. 検索は OpenAI Responses API + Web Search
最新情報を引きたいので、OpenAI の Web Search を使います。

### 3. ただし出力はそのまま返さず、構造化する
OpenAI の返却をそのまま文字列で返すだけだと、あとでエージェントが扱いづらいです。
そこで、
- URL
- title
- source_type
- categories
- metadata
- confidence
を持つ JSON に正規化するようにしました。

### 4. 統合ツール + 用途別ラッパの両方を出す
人間が使う場合と、エージェントが使う場合で最適なツール粒度は少し違います。
そのため、
- なんでも横断検索する `search_network_knowledge`
- 用途別ラッパ
の両方を提供しています。

---

## セットアップ
```bash
cd /home/user/projects/mcpServers/search_knowledge_mcp
cp .env.example .env
# OPENAI_API_KEY を設定
uv sync
```

### ここでこのスクショを投入予定
- `.env` 設定画面
- `uv sync` 実行結果

---

## 起動方法
```bash
uv run python -m search_knowledge_mcp.server
```

### ここでこのスクショを投入予定
- MCPサーバ起動ログ

---

## コードの見どころ

### クエリ生成
ユーザ入力をそのまま検索に投げるのではなく、カテゴリごとに補助語を足しています。

例:
- `Cisco IOS-XE 17.9 OSPF configuration example site:cisco.com`
- `FortiOS 7.4 CVE security advisory`
- `Ubuntu 24.04 netplan VLAN configuration`

こうすることで、公式ドキュメントや関連性の高い情報を引きやすくしています。

### 結果分類
URL ドメインや本文のキーワードから、
- official_vendor
- security_advisory
- documentation
- community
などを推定しています。

### パース戦略
OpenAI Web Search の返却形式は今後変わる可能性があるため、
- annotations に URL があるケース
- 本文に URL が埋まっているケース
の両方を拾うようにしました。

---

## LangChain / LangGraph から使う
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient(
    {
        "search-knowledge": {
            "command": "uv",
            "args": ["run", "python", "-m", "search_knowledge_mcp.server"],
            "transport": "stdio",
        }
    }
)
```

### ここでこのスクショを投入予定
- クライアント設定コード
- MCPツール一覧が見えている画面

---

## 使ってみた感想
この構成の良いところは、**LLMに「必ずMCPで確認してから答えて」と指示しやすい** ことです。

特に以下の用途と相性が良いと感じました。
- NW機器の設定案レビュー
- 既知脆弱性を踏まえたバージョン検討
- リリースノートを踏まえたアップグレード設計
- 最新仕様が絡む構成検討

逆に、まだ今後詰めたい点もあります。
- URL生存確認の追加
- ベンダー別パーサ強化
- キャッシュ
- HTTP transport 対応

---

## まとめ
OpenAI Web Search を使うことで、MCPサーバでも「最新情報を根拠付きで引く」体験がかなり作りやすくなりました。

今回の `search-knowledge-mcp` は、
- 最新情報を検索できる
- JSONで構造化して返せる
- LangGraph から使いやすい
- GitHub / PyPI 公開しやすい
というバランスを狙った実装になっています。

もし次にやるなら、URL検証レイヤや vendor-specific parser を足して、さらに実運用寄りにしたいです。

---

## リポジトリ
※ここに GitHub URL を記載予定

## PyPI
※ここに PyPI URL を記載予定
