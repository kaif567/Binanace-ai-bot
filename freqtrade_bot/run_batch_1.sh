#!/bin/bash
echo "Waiting for pip to finish..."
while pgrep -f "pip install" > /dev/null; do
    sleep 10
done
echo "Pip finished. Running Action 1 (Download Data)..."
./venv/bin/freqtrade download-data --pairs BTC/USDT -t 1h --timerange 20240601-20240831 --exchange binance -c user_data/config.json
echo "Data downloaded. Running Action 3 (Backtest)..."
./venv/bin/freqtrade backtesting --strategy DonchianStrategy -i 1h --timerange 20240601-20240831 -c user_data/config.json --export none
