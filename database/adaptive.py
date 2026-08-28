import sqlite3
import os


DB_NAME = os.path.join(
    os.path.dirname(__file__),
    "strategy_memory.db"
)



def analyze_memory(strategy):

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()


    cursor.execute(
        """
        SELECT
            confidence,
            status

        FROM strategies

        WHERE symbol = ?
        AND ema = ?
        AND stop_loss = ?
        AND take_profit = ?

        ORDER BY id DESC

        LIMIT 1
        """,

        (

            strategy.get(
                "symbol",
                "BTCUSDT"
            ),

            strategy.get(
                "ema"
            ),

            strategy.get(
                "sl"
            ),

            strategy.get(
                "tp"
            )

        )

    )


    result = cursor.fetchone()


    conn.close()



    if result is None:


        return {

            "found": False,

            "boost": 0,

            "message":
            "No Previous Memory"

        }



    confidence = result[0]

    status = result[1]



    if status == "APPROVED":


        boost = 15 if confidence >= 80 else 8


        return {

            "found": True,

            "boost": boost,

            "message":
            "Previous Success Found"

        }



    return {

        "found": True,

        "boost": 0,

        "message":
        "Previous Strategy Failed"

    }