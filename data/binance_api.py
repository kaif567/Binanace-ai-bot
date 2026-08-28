import math
import time

import requests
import pandas as pd


BASE_URL = "https://api.binance.com"


_SERVER_TIME_OFFSET_MS = None

_SERVER_TIME_CACHE_UPDATED = 0.0

_SERVER_TIME_CACHE_TTL_SECONDS = 300


class CandleIntegrityError(Exception):

    def __init__(
        self,
        message,
        report=None
    ):

        super().__init__(
            message
        )

        self.report = (
            report
            if isinstance(
                report,
                dict
            )
            else {}
        )


class RecentCandleGapError(
        CandleIntegrityError
):
    pass


class PaginationError(Exception):
    pass


class RecoveryWindowTooLargeError(
        Exception
):
    pass


INTERVAL_MS = {

    "1m":
    60 * 1000,

    "3m":
    3 * 60 * 1000,

    "5m":
    5 * 60 * 1000,

    "15m":
    15 * 60 * 1000,

    "30m":
    30 * 60 * 1000,

    "1h":
    60 * 60 * 1000,

    "2h":
    2 * 60 * 60 * 1000,

    "4h":
    4 * 60 * 60 * 1000,

    "6h":
    6 * 60 * 60 * 1000,

    "8h":
    8 * 60 * 60 * 1000,

    "12h":
    12 * 60 * 60 * 1000,

    "1d":
    24 * 60 * 60 * 1000

}


def interval_to_milliseconds(
        interval
):

    if interval not in INTERVAL_MS:

        raise ValueError(
            f"Unsupported fixed interval: {interval}"
        )


    return (
        INTERVAL_MS[
            interval
        ]
    )


def get_price(
        symbol
):

    url = (
        f"{BASE_URL}/api/v3/ticker/price"
    )


    response = requests.get(

        url,

        params={
            "symbol":
            symbol
        },

        timeout=10

    )


    response.raise_for_status()


    data = response.json()


    return float(
        data[
            "price"
        ]
    )


def get_server_time(
        force_refresh=False
):

    global _SERVER_TIME_OFFSET_MS

    global _SERVER_TIME_CACHE_UPDATED


    now_monotonic = (
        time.monotonic()
    )


    local_now_ms = int(
        time.time()
        *
        1000
    )


    cache_valid = (

        not force_refresh

        and

        _SERVER_TIME_OFFSET_MS
        is not None

        and

        (
            now_monotonic
            -
            _SERVER_TIME_CACHE_UPDATED
        )
        <
        _SERVER_TIME_CACHE_TTL_SECONDS

    )


    if cache_valid:

        return int(
            local_now_ms
            +
            _SERVER_TIME_OFFSET_MS
        )


    url = (
        f"{BASE_URL}/api/v3/time"
    )


    local_before = int(
        time.time()
        *
        1000
    )


    response = requests.get(
        url,
        timeout=10
    )


    response.raise_for_status()


    local_after = int(
        time.time()
        *
        1000
    )


    server_time = int(
        response.json()[
            "serverTime"
        ]
    )


    local_midpoint = (
        local_before
        +
        local_after
    ) // 2


    _SERVER_TIME_OFFSET_MS = (
        server_time
        -
        local_midpoint
    )


    _SERVER_TIME_CACHE_UPDATED = (
        now_monotonic
    )


    return int(
        time.time()
        *
        1000
        +
        _SERVER_TIME_OFFSET_MS
    )


def _fetch_klines_page(
        symbol,
        interval="1h",
        limit=1000,
        end_time=None,
        start_time=None
):

    limit = int(
        limit
    )


    if limit <= 0:

        raise ValueError(
            "limit must be greater than 0"
        )


    limit = min(
        limit,
        1000
    )


    params = {

        "symbol":
        symbol,

        "interval":
        interval,

        "limit":
        limit

    }


    if end_time is not None:

        params[
            "endTime"
        ] = int(
            end_time
        )


    if start_time is not None:

        params[
            "startTime"
        ] = int(
            start_time
        )


    response = requests.get(

        f"{BASE_URL}/api/v3/klines",

        params=params,

        timeout=15

    )


    response.raise_for_status()


    data = response.json()


    if not isinstance(
        data,
        list
    ):

        raise Exception(
            "Unexpected Binance kline response"
        )


    return data


def _empty_kline_dataframe():

    return pd.DataFrame(

        columns=[

            "time",

            "open",

            "high",

            "low",

            "close",

            "volume",

            "close_time"

        ]

    )


def _normalize_klines(
        data
):

    if not data:

        return (
            _empty_kline_dataframe()
        )


    df = pd.DataFrame(
        data
    )


    if df.shape[
        1
    ] < 7:

        raise ValueError(
            "Invalid Binance kline data"
        )


    df = df.iloc[
        :,
        0:7
    ].copy()


    df.columns = [

        "time",

        "open",

        "high",

        "low",

        "close",

        "volume",

        "close_time"

    ]


    df[
        "time"
    ] = (
        df[
            "time"
        ]
        .astype(
            "int64"
        )
    )


    df[
        "close_time"
    ] = (
        df[
            "close_time"
        ]
        .astype(
            "int64"
        )
    )


    for column in [

        "open",

        "high",

        "low",

        "close",

        "volume"

    ]:

        df[
            column
        ] = (
            df[
                column
            ]
            .astype(
                float
            )
        )


    return df


def get_candles(
        symbol,
        interval="1h",
        limit=100
):

    data = (
        _fetch_klines_page(

            symbol,

            interval=interval,

            limit=min(
                int(
                    limit
                ),
                1000
            )

        )
    )


    df = (
        _normalize_klines(
            data
        )
    )


    if df.empty:

        return df.iloc[
            :,
            0:6
        ]


    return (
        df[[
            "time",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]]
        .copy()
        .reset_index(
            drop=True
        )
    )


def get_closed_candles(
        symbol,
        interval="1h",
        limit=100
):

    limit = int(
        limit
    )


    if limit <= 0:

        raise ValueError(
            "limit must be greater than 0"
        )


    if limit > 998:

        return (
            get_closed_candles_paginated(

                symbol,

                interval=interval,

                limit=limit

            )
        )


    fetch_limit = min(
        limit
        +
        2,
        1000
    )


    data = (
        _fetch_klines_page(

            symbol,

            interval=interval,

            limit=fetch_limit

        )
    )


    df = (
        _normalize_klines(
            data
        )
    )


    if df.empty:

        return df


    server_time = (
        get_server_time()
    )


    df = df[
        df[
            "close_time"
        ]
        <=
        server_time
    ].copy()


    return (
        df
        .sort_values(
            "time"
        )
        .drop_duplicates(
            subset=[
                "time"
            ],
            keep="last"
        )
        .tail(
            limit
        )
        .reset_index(
            drop=True
        )
    )


def get_latest_closed_candle(
        symbol,
        interval="1h"
):

    data = (
        _fetch_klines_page(

            symbol,

            interval=interval,

            limit=2

        )
    )


    df = (
        _normalize_klines(
            data
        )
    )


    if df.empty:

        return None


    server_time = (
        get_server_time()
    )


    closed = df[
        df[
            "close_time"
        ]
        <=
        server_time
    ].copy()


    if closed.empty:

        return None


    closed = (
        closed
        .sort_values(
            "time"
        )
        .drop_duplicates(
            subset=[
                "time"
            ],
            keep="last"
        )
    )


    latest = (
        closed.iloc[
            -1
        ]
    )


    return {

        "time":
        int(
            latest[
                "time"
            ]
        ),


        "close_time":
        int(
            latest[
                "close_time"
            ]
        ),


        "open":
        float(
            latest[
                "open"
            ]
        ),


        "high":
        float(
            latest[
                "high"
            ]
        ),


        "low":
        float(
            latest[
                "low"
            ]
        ),


        "close":
        float(
            latest[
                "close"
            ]
        ),


        "volume":
        float(
            latest[
                "volume"
            ]
        )

    }


def validate_candle_integrity(
        df,
        interval="1h",
        recent_gap_window_candles=24,
        truncate_historical_gaps=True
):

    if df is None:

        raise CandleIntegrityError(
            "Dataframe is None"
        )


    if len(
        df
    ) == 0:

        return (
            df.copy(),
            {

                "input_rows":
                0,

                "returned_rows":
                0,

                "duplicates_removed":
                0,

                "gap_count":
                0,

                "historical_gap_count":
                0,

                "recent_gap_count":
                0,

                "missing_candles":
                0,

                "truncated_rows":
                0,

                "continuous":
                True

            }
        )


    if (
        "time"
        not in
        df.columns
    ):

        raise CandleIntegrityError(
            "Missing time column"
        )


    expected_ms = (
        interval_to_milliseconds(
            interval
        )
    )


    working = (
        df.copy()
    )


    input_rows = len(
        working
    )


    working = (
        working
        .sort_values(
            "time"
        )
        .reset_index(
            drop=True
        )
    )


    before_dedup = len(
        working
    )


    working = (
        working
        .drop_duplicates(
            subset=[
                "time"
            ],
            keep="last"
        )
        .sort_values(
            "time"
        )
        .reset_index(
            drop=True
        )
    )


    duplicates_removed = (
        before_dedup
        -
        len(
            working
        )
    )


    if len(
        working
    ) < 2:

        return (
            working,
            {

                "input_rows":
                input_rows,

                "returned_rows":
                len(
                    working
                ),

                "duplicates_removed":
                duplicates_removed,

                "gap_count":
                0,

                "historical_gap_count":
                0,

                "recent_gap_count":
                0,

                "missing_candles":
                0,

                "truncated_rows":
                0,

                "continuous":
                True

            }
        )


    gap_records = []


    for index in range(
        1,
        len(
            working
        )
    ):

        difference = int(

            working.iloc[
                index
            ][
                "time"
            ]

            -

            working.iloc[
                index - 1
            ][
                "time"
            ]

        )


        if difference == expected_ms:

            continue


        if difference < expected_ms:

            raise CandleIntegrityError(
                (
                    "Unexpected sub-interval "
                    "timestamp spacing"
                )
            )


        if (
            difference
            %
            expected_ms
        ) != 0:

            raise CandleIntegrityError(
                (
                    "Candle timestamps are not "
                    "aligned to interval"
                )
            )


        missing = (
            difference
            //
            expected_ms
        ) - 1


        gap_records.append({

            "older_time":
            int(
                working.iloc[
                    index - 1
                ][
                    "time"
                ]
            ),


            "newer_time":
            int(
                working.iloc[
                    index
                ][
                    "time"
                ]
            ),


            "missing_candles":
            int(
                missing
            ),


            "index":
            index

        })


    newest_time = int(
        working.iloc[
            -1
        ][
            "time"
        ]
    )


    recent_cutoff = (
        newest_time
        -
        int(
            recent_gap_window_candles
        )
        *
        expected_ms
    )


    recent_gaps = [

        gap

        for gap in gap_records

        if gap[
            "newer_time"
        ]
        >=
        recent_cutoff

    ]


    historical_gaps = [

        gap

        for gap in gap_records

        if gap[
            "newer_time"
        ]
        <
        recent_cutoff

    ]


    missing_candles = sum(

        gap[
            "missing_candles"
        ]

        for gap in gap_records

    )


    report = {

        "input_rows":
        input_rows,


        "duplicates_removed":
        duplicates_removed,


        "gap_count":
        len(
            gap_records
        ),


        "historical_gap_count":
        len(
            historical_gaps
        ),


        "recent_gap_count":
        len(
            recent_gaps
        ),


        "missing_candles":
        missing_candles,


        "gaps":
        gap_records,


        "truncated_rows":
        0,


        "continuous":
        len(
            gap_records
        )
        ==
        0

    }


    if recent_gaps:

        report[
            "returned_rows"
        ] = len(
            working
        )


        raise RecentCandleGapError(

            (
                "Recent candle gap detected. "
                "Dataset blocked."
            ),

            report=report

        )


    if (
        historical_gaps
        and
        truncate_historical_gaps
    ):

        last_gap = (
            historical_gaps[
                -1
            ]
        )


        continuous_start_index = (
            last_gap[
                "index"
            ]
        )


        before = len(
            working
        )


        working = (
            working.iloc[
                continuous_start_index:
            ]
            .copy()
            .reset_index(
                drop=True
            )
        )


        report[
            "truncated_rows"
        ] = (
            before
            -
            len(
                working
            )
        )


        report[
            "continuous"
        ] = True


    elif historical_gaps:

        report[
            "returned_rows"
        ] = len(
            working
        )


        raise CandleIntegrityError(
            "Historical candle gap detected",
            report=report
        )


    if len(
        working
    ) >= 2:

        final_diffs = (
            working[
                "time"
            ]
            .astype(
                "int64"
            )
            .diff()
            .iloc[
                1:
            ]
        )


        if not (
            final_diffs
            ==
            expected_ms
        ).all():

            raise CandleIntegrityError(
                (
                    "Final continuous block failed "
                    "strict interval validation"
                ),
                report=report
            )


    report[
        "returned_rows"
    ] = len(
        working
    )


    return (
        working,
        report
    )


def get_closed_candles_paginated(
        symbol,
        interval="1h",
        limit=3000,
        page_size=1000,
        recent_gap_window_candles=24,
        truncate_historical_gaps=True,
        return_report=False
):

    limit = int(
        limit
    )


    if limit <= 0:

        raise ValueError(
            "limit must be greater than 0"
        )


    page_size = min(
        max(
            1,
            int(
                page_size
            )
        ),
        1000
    )


    server_time = (
        get_server_time()
    )


    pages = []

    page_count = 0

    end_time = server_time

    previous_oldest = None

    unique_count = 0

    raw_rows = 0


    max_pages = (
        math.ceil(
            limit
            /
            page_size
        )
        +
        10
    )


    while (
        unique_count < limit
        and
        page_count < max_pages
    ):

        remaining = (
            limit
            -
            unique_count
        )


        request_limit = min(
            page_size,
            max(
                2,
                remaining
                +
                2
            )
        )


        raw = (
            _fetch_klines_page(

                symbol,

                interval=interval,

                limit=request_limit,

                end_time=end_time

            )
        )


        page_count += 1


        if not raw:

            break


        page = (
            _normalize_klines(
                raw
            )
        )


        raw_rows += len(
            page
        )


        page = page[
            page[
                "close_time"
            ]
            <=
            server_time
        ].copy()


        if page.empty:

            break


        pages.append(
            page
        )


        combined_for_count = (
            pd.concat(
                pages,
                ignore_index=True
            )
        )


        unique_count = int(
            combined_for_count[
                "time"
            ]
            .nunique()
        )


        oldest_time = int(
            page[
                "time"
            ]
            .min()
        )


        if (
            previous_oldest
            is not None
            and
            oldest_time
            >=
            previous_oldest
        ):

            raise PaginationError(
                (
                    "Pagination stopped moving "
                    "backwards"
                )
            )


        previous_oldest = (
            oldest_time
        )


        end_time = (
            oldest_time
            -
            1
        )


    if not pages:

        empty = (
            _empty_kline_dataframe()
        )


        report = {

            "requested_limit":
            limit,

            "returned_rows":
            0,

            "pages":
            page_count,

            "raw_rows":
            raw_rows,

            "pagination_duplicates_removed":
            0

        }


        if return_report:

            return (
                empty,
                report
            )


        return empty


    combined = (
        pd.concat(
            pages,
            ignore_index=True
        )
        .sort_values(
            "time"
        )
        .reset_index(
            drop=True
        )
    )


    before_dedup = len(
        combined
    )


    combined = (
        combined
        .drop_duplicates(
            subset=[
                "time"
            ],
            keep="last"
        )
        .sort_values(
            "time"
        )
        .reset_index(
            drop=True
        )
    )


    pagination_duplicates_removed = (
        before_dedup
        -
        len(
            combined
        )
    )


    combined = (
        combined
        .tail(
            limit
        )
        .reset_index(
            drop=True
        )
    )


    cleaned, integrity = (
        validate_candle_integrity(

            combined,

            interval=interval,

            recent_gap_window_candles=
            recent_gap_window_candles,

            truncate_historical_gaps=
            truncate_historical_gaps

        )
    )


    report = dict(
        integrity
    )


    report.update({

        "requested_limit":
        limit,


        "returned_rows":
        len(
            cleaned
        ),


        "pages":
        page_count,


        "raw_rows":
        raw_rows,


        "pagination_duplicates_removed":
        pagination_duplicates_removed,


        "oldest_time":
        (
            None
            if cleaned.empty
            else
            int(
                cleaned.iloc[
                    0
                ][
                    "time"
                ]
            )
        ),


        "newest_time":
        (
            None
            if cleaned.empty
            else
            int(
                cleaned.iloc[
                    -1
                ][
                    "time"
                ]
            )
        )

    })


    if return_report:

        return (
            cleaned,
            report
        )


    return cleaned


def get_closed_candles_range(
        symbol,
        interval="1m",
        start_time=None,
        end_time=None,
        max_hours=72
):

    """
    Item 8 missed-window recovery.

    Hard safety:
    Any requested window greater than
    max_hours is rejected BEFORE any
    Binance API request is made.

    The first containing minute is included
    conservatively because 1m OHLC cannot
    resolve sub-minute ordering.
    """

    if (
        start_time is None
        or
        end_time is None
    ):

        raise ValueError(
            (
                "start_time and end_time "
                "are required"
            )
        )


    start_time = int(
        start_time
    )


    end_time = int(
        end_time
    )


    if end_time < start_time:

        raise ValueError(
            "end_time must be >= start_time"
        )


    max_window_ms = (
        float(
            max_hours
        )
        *
        60
        *
        60
        *
        1000
    )


    requested_window_ms = (
        end_time
        -
        start_time
    )


    # IMPORTANT:
    # This happens before get_server_time()
    # or any kline request.
    if (
        requested_window_ms
        >
        max_window_ms
    ):

        raise RecoveryWindowTooLargeError(
            (
                "Recovery window exceeds "
                f"{max_hours} hours."
            )
        )


    interval_ms = (
        interval_to_milliseconds(
            interval
        )
    )


    # Conservatively include the minute
    # containing last_checked_time.
    aligned_start_time = (
        start_time
        //
        interval_ms
        *
        interval_ms
    )


    server_time = (
        get_server_time()
    )


    effective_end = min(
        end_time,
        server_time
    )


    if (
        effective_end
        <
        aligned_start_time
    ):

        return (
            _empty_kline_dataframe()
        )


    pages = []


    next_start = (
        aligned_start_time
    )


    theoretical_candles = (
        (
            effective_end
            -
            aligned_start_time
        )
        //
        interval_ms
    ) + 1


    max_pages = (
        math.ceil(
            theoretical_candles
            /
            1000
        )
        +
        2
    )


    page_count = 0


    while (
        next_start
        <=
        effective_end
        and
        page_count
        <
        max_pages
    ):

        raw = (
            _fetch_klines_page(

                symbol,

                interval=interval,

                limit=1000,

                start_time=next_start,

                end_time=effective_end

            )
        )


        page_count += 1


        if not raw:

            break


        page = (
            _normalize_klines(
                raw
            )
        )


        if page.empty:

            break


        pages.append(
            page
        )


        newest_open_time = int(
            page[
                "time"
            ]
            .max()
        )


        new_next_start = (
            newest_open_time
            +
            interval_ms
        )


        if (
            new_next_start
            <=
            next_start
        ):

            raise PaginationError(
                (
                    "Recovery pagination stopped "
                    "moving forward"
                )
            )


        next_start = (
            new_next_start
        )


        if len(
            page
        ) < 1000:

            break


    if not pages:

        return (
            _empty_kline_dataframe()
        )


    combined = (
        pd.concat(
            pages,
            ignore_index=True
        )
        .sort_values(
            "time"
        )
        .drop_duplicates(
            subset=[
                "time"
            ],
            keep="last"
        )
        .reset_index(
            drop=True
        )
    )


    # Only fully-closed candles.
    combined = combined[

        (
            combined[
                "time"
            ]
            >=
            aligned_start_time
        )

        &

        (
            combined[
                "close_time"
            ]
            <=
            effective_end
        )

    ].copy()


    combined = (
        combined
        .sort_values(
            "time"
        )
        .drop_duplicates(
            subset=[
                "time"
            ],
            keep="last"
        )
        .reset_index(
            drop=True
        )
    )


    # Recovery gaps cannot be silently
    # ignored because the missing minute
    # could contain TP/SL execution.
    if len(
        combined
    ) >= 2:

        diffs = (
            combined[
                "time"
            ]
            .astype(
                "int64"
            )
            .diff()
            .iloc[
                1:
            ]
        )


        if not (
            diffs
            ==
            interval_ms
        ).all():

            raise CandleIntegrityError(
                (
                    "Missing candle inside paper "
                    "recovery window."
                )
            )


    return combined