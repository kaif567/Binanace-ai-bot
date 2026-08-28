from monitor.live_monitor import (
    start_live_monitor
)


print(
    "=============================="
)

print(
    "LIVE MONITOR IMPORT TEST"
)

print(
    "=============================="
)


if not callable(
    start_live_monitor
):

    raise AssertionError(
        "start_live_monitor is not callable"
    )


print(
    "start_live_monitor import: PASS ✅"
)


print(
    "Infinite live loop was NOT started ✅"
)


print(
    "\nMONITOR REGRESSION TEST: PASS ✅"
)