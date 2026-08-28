import argparse
import datetime
import os
import shutil

from database import paper_store


LEGACY_ARCHIVE_STATUS = (
    "LEGACY_ARCHIVED"
)


def utc_now():

    return (
        datetime.datetime
        .now(
            datetime.timezone.utc
        )
    )


def iso_now():

    return (
        utc_now()
        .isoformat()
    )


def timestamp_for_filename():

    return (
        utc_now()
        .strftime(
            "%Y%m%d_%H%M%S"
        )
    )


def is_legacy_open_position(
        trade
):

    if not isinstance(
        trade,
        dict
    ):

        return False


    if (
        trade.get(
            "status"
        )
        !=
        "OPEN"
    ):

        return False


    schema_version = int(
        trade.get(
            "schema_version",
            0
        )
        or
        0
    )


    return (
        schema_version
        <
        2
    )


def create_backup():

    source = os.path.abspath(
        paper_store.TRADE_FILE
    )


    if not os.path.exists(
        source
    ):

        raise FileNotFoundError(
            (
                "paper_trades.json does not exist. "
                "Nothing can be archived."
            )
        )


    directory = os.path.dirname(
        source
    )


    backup_name = (
        "paper_trades_backup_"
        +
        timestamp_for_filename()
        +
        ".json"
    )


    backup_path = os.path.join(
        directory,
        backup_name
    )


    shutil.copy2(
        source,
        backup_path
    )


    return backup_path


def preview_legacy_positions(
        trades
):

    legacy_positions = []


    for index, trade in enumerate(
        trades
    ):

        if not is_legacy_open_position(
            trade
        ):

            continue


        legacy_positions.append({

            "index":
            index,


            "symbol":
            trade.get(
                "symbol"
            ),


            "entry_price":
            trade.get(
                "entry_price"
            ),


            "time":
            trade.get(
                "time"
            ),


            "status":
            trade.get(
                "status"
            )

        })


    return legacy_positions


def archive_legacy_positions(
        trades
):

    updated = []


    archived_count = 0


    archive_time = (
        iso_now()
    )


    for trade in trades:

        if not is_legacy_open_position(
            trade
        ):

            updated.append(
                trade
            )

            continue


        archived = dict(
            trade
        )


        archived[
            "status"
        ] = (
            LEGACY_ARCHIVE_STATUS
        )


        archived[
            "legacy_resolution"
        ] = (
            "ARCHIVED_NO_PNL"
        )


        archived[
            "legacy_resolution_reason"
        ] = (
            "Pre-Item-8 paper position; "
            "execution history cannot be "
            "reconstructed reliably."
        )


        archived[
            "archived_time"
        ] = (
            archive_time
        )


        # Intentionally do NOT create:
        #
        # exit_price
        # profit
        # return
        # exit_fee
        #
        # because those values are unknown.


        updated.append(
            archived
        )


        archived_count += 1


    return (
        updated,
        archived_count
    )


def main():

    parser = argparse.ArgumentParser(

        description=(
            "Safely archive pre-Item-8 "
            "legacy OPEN paper positions."
        )

    )


    parser.add_argument(

        "--apply",

        action="store_true",

        help=(
            "Actually archive legacy positions. "
            "Without this flag only preview."
        )

    )


    args = parser.parse_args()


    print(
        "======================================"
    )

    print(
        "LEGACY PAPER POSITION RESOLUTION"
    )

    print(
        "======================================"
    )


    trades = (
        paper_store.load_trades()
    )


    legacy_positions = (
        preview_legacy_positions(
            trades
        )
    )


    if not legacy_positions:

        print(
            "No legacy OPEN positions found."
        )

        print(
            "Nothing changed."
        )

        return


    print(
        "Legacy OPEN positions found:",
        len(
            legacy_positions
        )
    )


    for position in legacy_positions:

        print(
            "\n------------------------------"
        )

        print(
            "Index:",
            position[
                "index"
            ]
        )

        print(
            "Symbol:",
            position[
                "symbol"
            ]
        )

        print(
            "Entry Price:",
            position[
                "entry_price"
            ]
        )

        print(
            "Original Time:",
            position[
                "time"
            ]
        )

        print(
            "Current Status:",
            position[
                "status"
            ]
        )


    if not args.apply:

        print(
            "\nPREVIEW ONLY ✅"
        )

        print(
            "No file was modified."
        )

        print(
            "\nTo archive safely run:"
        )

        print(
            "python resolve_legacy_paper.py --apply"
        )

        return


    backup_path = (
        create_backup()
    )


    updated_trades, archived_count = (
        archive_legacy_positions(
            trades
        )
    )


    paper_store.save_trades_atomic(
        updated_trades
    )


    print(
        "\n✅ BACKUP CREATED:"
    )

    print(
        backup_path
    )


    print(
        "\n✅ LEGACY POSITIONS ARCHIVED:",
        archived_count
    )


    print(
        "No PnL was invented."
    )

    print(
        "No exit price was invented."
    )

    print(
        "Original legacy data preserved."
    )


    # Reload from disk to verify persistence.

    verification = (
        paper_store.load_trades()
    )


    remaining_legacy_open = [

        trade

        for trade in verification

        if is_legacy_open_position(
            trade
        )

    ]


    if remaining_legacy_open:

        raise AssertionError(
            (
                "Legacy archive verification "
                "failed."
            )
        )


    print(
        "\nLEGACY ARCHIVE VERIFICATION: PASS ✅"
    )


if __name__ == "__main__":

    main()