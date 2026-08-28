import json
import os
import tempfile


TRADE_FILE = "paper_trades.json"


class PaperStateError(RuntimeError):
    pass


def load_trades():

    if not os.path.exists(
        TRADE_FILE
    ):

        return []


    try:

        with open(
            TRADE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

    except Exception as error:

        raise PaperStateError(
            (
                "Paper trade state could not be read. "
                "Trading is blocked until the JSON "
                "state is repaired."
            )
        ) from error


    if not isinstance(
        data,
        list
    ):

        raise PaperStateError(
            "Paper trade state must be a JSON list."
        )


    return data


def save_trades_atomic(
        trades
):

    if not isinstance(
        trades,
        list
    ):

        raise PaperStateError(
            "Paper trades must be saved as a list."
        )


    absolute_file = os.path.abspath(
        TRADE_FILE
    )


    directory = os.path.dirname(
        absolute_file
    )


    os.makedirs(
        directory,
        exist_ok=True
    )


    temp_path = None


    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=".paper_trades_",
            suffix=".tmp",
            delete=False
        ) as temp_file:

            temp_path = temp_file.name


            json.dump(
                trades,
                temp_file,
                indent=4
            )


            temp_file.flush()

            os.fsync(
                temp_file.fileno()
            )


        os.replace(
            temp_path,
            absolute_file
        )


    except Exception as error:

        if (
            temp_path
            and
            os.path.exists(
                temp_path
            )
        ):

            try:

                os.remove(
                    temp_path
                )

            except Exception:
                pass


        raise PaperStateError(
            "Atomic paper-state save failed."
        ) from error


def append_trade(
        trade
):

    trades = load_trades()

    trades.append(
        trade
    )

    save_trades_atomic(
        trades
    )


def replace_trade(
        updated_trade
):

    position_id = updated_trade.get(
        "position_id"
    )


    if not position_id:

        raise PaperStateError(
            "Cannot replace trade without position_id."
        )


    trades = load_trades()

    found = False


    for index, trade in enumerate(
        trades
    ):

        if (
            trade.get(
                "position_id"
            )
            ==
            position_id
        ):

            trades[
                index
            ] = updated_trade

            found = True

            break


    if not found:

        raise PaperStateError(
            (
                "Paper position was not found while "
                "attempting persistent update."
            )
        )


    save_trades_atomic(
        trades
    )


def clear_trade_file_for_test():

    if os.path.exists(
        TRADE_FILE
    ):

        os.remove(
            TRADE_FILE
        )