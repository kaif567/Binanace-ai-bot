import os
import tempfile

import database.memory as memory


ORIGINAL_DB_NAME = (
    memory.DB_NAME
)


def main():

    print(
        "=============================="
    )

    print(
        "MEMORY REGRESSION TEST"
    )

    print(
        "=============================="
    )


    try:


        with tempfile.TemporaryDirectory() as temp_dir:


            memory.DB_NAME = os.path.join(

                temp_dir,

                "strategy_memory_test.db"

            )



            memory.create_memory()



            validated_strategy = {

                "strategy": {

                    "ema_fast":
                    20,

                    "ema_slow":
                    50,

                    "sl":
                    0.02,

                    "tp":
                    0.05

                },


                "profit":
                15.92,


                "win_rate":
                55,


                "profit_factor":
                1.8,


                "strategy_quality":
                82.0,


                "sample_quality":
                "OOS_SUFFICIENT"

            }



            validated_report = {

                "strategy_quality":
                82.0,


                "oos_sample_quality":
                "OOS_SUFFICIENT",


                "paper_status":
                "TEST"

            }



            memory.save_strategy(

                "BTCUSDT",

                validated_strategy,

                validated_report

            )



            # A higher numeric score but
            # insufficient OOS sample must
            # NOT enter validated ranking.


            insufficient_strategy = {

                "strategy": {

                    "ema_fast":
                    10,

                    "ema_slow":
                    50,

                    "sl":
                    0.01,

                    "tp":
                    0.05

                },


                "profit":
                50,


                "win_rate":
                80,


                "profit_factor":
                3,


                "strategy_quality":
                95.0,


                "sample_quality":
                "LOW_SAMPLE_SIZE"

            }



            insufficient_report = {

                "strategy_quality":
                95.0,


                "oos_sample_quality":
                "LOW_SAMPLE_SIZE"

            }



            memory.save_strategy(

                "BTCUSDT",

                insufficient_strategy,

                insufficient_report

            )



            best = (
                memory.get_best_memory()
            )



            if not best:

                raise AssertionError(
                    "No validated strategies returned"
                )



            first = best[
                0
            ]



            # Current schema:
            #
            # 0  id
            # 1  symbol
            # 2  strategy
            # 3  profit
            # 4  win_rate
            # 5  profit_factor
            # 6  confidence (legacy)
            # 7  status
            # 8  report
            # 9  created_at
            # 10 strategy_quality
            # 11 oos_sample_quality


            if (
                first[
                    7
                ]
                !=
                "STRATEGY_VALIDATED"
            ):

                raise AssertionError(
                    f"Wrong status: {first[7]}"
                )



            if (
                float(
                    first[
                        10
                    ]
                )
                !=
                82.0
            ):

                raise AssertionError(
                    "Strategy quality ranking incorrect"
                )



            if (
                first[
                    11
                ]
                !=
                "OOS_SUFFICIENT"
            ):

                raise AssertionError(
                    "OOS sample quality incorrect"
                )



            print(
                "SQLite Migration: PASS ✅"
            )


            print(
                "Strategy Quality Saved: PASS ✅"
            )


            print(
                "OOS Sample Quality Saved: PASS ✅"
            )


            print(
                "Validated Ranking: PASS ✅"
            )


            print(
                "Insufficient OOS Excluded: PASS ✅"
            )


            print(
                "Real strategy_memory.db NOT modified ✅"
            )



    finally:


        memory.DB_NAME = (
            ORIGINAL_DB_NAME
        )



    print(
        "\nMEMORY REGRESSION TEST: PASS ✅"
    )



if __name__ == "__main__":

    main()