import time

from scanner.coins import (
    scan_market,
    print_scanner
)


def main():

    while True:

        results = scan_market()

        print_scanner(results)

        print(
            "Refreshing in 60 seconds..."
        )

        time.sleep(60)


if __name__ == "__main__":

    main()