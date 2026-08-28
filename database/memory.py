import sqlite3
from datetime import datetime


DB_NAME = (
    "strategy_memory.db"
)


def _ensure_schema(
    conn
):

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS strategies
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            strategy TEXT,
            profit REAL,
            win_rate REAL,
            profit_factor REAL,
            confidence REAL,
            status TEXT,
            report TEXT,
            created_at TEXT,
            strategy_quality REAL DEFAULT 0,
            oos_sample_quality TEXT DEFAULT ''
        )
        """
    )

    cursor.execute(
        "PRAGMA table_info(strategies)"
    )

    columns = {
        row[1]
        for row in cursor.fetchall()
    }

    if (
        "strategy_quality"
        not in columns
    ):

        cursor.execute(
            """
            ALTER TABLE strategies
            ADD COLUMN strategy_quality
            REAL DEFAULT 0
            """
        )

    if (
        "oos_sample_quality"
        not in columns
    ):

        cursor.execute(
            """
            ALTER TABLE strategies
            ADD COLUMN oos_sample_quality
            TEXT DEFAULT ''
            """
        )

    conn.commit()


def create_memory():

    conn = sqlite3.connect(
        DB_NAME
    )

    _ensure_schema(
        conn
    )

    conn.close()

    print(
        "✅ Memory database initialized"
    )


def save_strategy(
    symbol,
    strategy,
    report
):

    conn = sqlite3.connect(
        DB_NAME
    )

    _ensure_schema(
        conn
    )

    cursor = conn.cursor()

    strategy_quality = float(
        strategy.get(
            "strategy_quality",
            report.get(
                "strategy_quality",
                0
            )
        )
    )

    oos_sample_quality = (
        strategy.get(
            "sample_quality",
            report.get(
                "oos_sample_quality",
                "LOW_SAMPLE_SIZE"
            )
        )
    )

    if (
        oos_sample_quality
        !=
        "OOS_SUFFICIENT"
    ):

        status = (
            "INSUFFICIENT_OOS_SAMPLE"
        )

    elif strategy_quality >= 70:

        status = (
            "STRATEGY_VALIDATED"
        )

    else:

        status = (
            "STRATEGY_BELOW_THRESHOLD"
        )

    cursor.execute(
        """
        INSERT INTO strategies
        (
            symbol,
            strategy,
            profit,
            win_rate,
            profit_factor,
            confidence,
            status,
            report,
            created_at,
            strategy_quality,
            oos_sample_quality
        )

        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,

        (
            symbol,

            str(
                strategy
            ),

            strategy.get(
                "profit",
                0
            ),

            strategy.get(
                "win_rate",
                0
            ),

            strategy.get(
                "profit_factor",
                0
            ),

            # legacy DB column only.
            # New system does not use it.
            0,

            status,

            str(
                report
            ),

            datetime.now().isoformat(),

            strategy_quality,

            oos_sample_quality
        )
    )

    conn.commit()

    conn.close()

    print(
        "✅ Strategy saved to memory"
    )

    print(
        "Strategy Status:",
        status
    )


def get_best_memory():

    conn = sqlite3.connect(
        DB_NAME
    )

    _ensure_schema(
        conn
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *

        FROM strategies

        WHERE status='STRATEGY_VALIDATED'

        ORDER BY strategy_quality DESC

        LIMIT 5
        """
    )

    result = (
        cursor.fetchall()
    )

    conn.close()

    return result