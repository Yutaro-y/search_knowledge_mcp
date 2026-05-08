"""ロギング設定ユーティリティ。"""

import logging


def configure_logging(level: str = "INFO") -> None:
    """アプリケーション全体の基本ログ設定を初期化します。"""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
