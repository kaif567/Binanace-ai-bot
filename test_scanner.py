import time

from scanner.coins import (
    scan_market,
    print_scanner
)



while True:


    results = scan_market()


    print_scanner(results)


    print(
        "Refreshing in 60 seconds..."
    )


    time.sleep(60)