from data.binance_api import get_price, get_candles


coins = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT"
]


print("🚀 Binance Live Scanner")
print("----------------------")


for coin in coins:

    price = get_price(coin)

    print(
        coin,
        ": $",
        price
    )


print("\nBTC Historical Data")

df = get_candles(
    "BTCUSDT"
)


print(df.tail())