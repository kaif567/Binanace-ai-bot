import sys, time, datetime
import requests
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import precision_score, accuracy_score

def ts(year, month, day):
    return int(datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc).timestamp() * 1000)

def fetch_futures_klines(symbol, start_time, end_time):
    print("Fetching Futures Klines (15m)...")
    all_data = []
    current_start = start_time
    ms_per_candle = 15 * 60 * 1000
    
    while current_start < end_time:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=15m&limit=1000&startTime={current_start}&endTime={end_time}"
        res = requests.get(url)
        data = res.json()
        if not data: break
        all_data.extend(data)
        current_start = int(data[-1][0]) + ms_per_candle
        
    cols = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
    df = pd.DataFrame(all_data, columns=cols)
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume', 'taker_buy_volume']:
        df[col] = df[col].astype(float)
    return df

def fetch_funding_rates(symbol, start_time, end_time):
    print("Fetching Funding Rates...")
    url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1000&startTime={start_time}&endTime={end_time}"
    res = requests.get(url)
    data = res.json()
    df = pd.DataFrame(data)
    df['fundingTime'] = pd.to_datetime(df['fundingTime'], unit='ms')
    df['fundingRate'] = df['fundingRate'].astype(float)
    return df

def run():
    start = ts(2024, 1, 1)
    end = ts(2024, 8, 31)
    
    # 1. Fetch Data
    df_k = fetch_futures_klines("BTCUSDT", start, end)
    df_f = fetch_funding_rates("BTCUSDT", start, end)
    
    # 2. Merge and Align
    df_k = df_k.sort_values('open_time').reset_index(drop=True)
    df_f = df_f.sort_values('fundingTime').reset_index(drop=True)
    
    df_k['funding_rate'] = np.nan
    for _, row in df_f.iterrows():
        df_k.loc[df_k['open_time'] >= row['fundingTime'], 'funding_rate'] = row['fundingRate']
    df_k['funding_rate'] = df_k['funding_rate'].ffill().fillna(0)
    
    # Features (Shifted)
    cvd = df_k['taker_buy_volume'] / (df_k['volume'] + 1e-8)
    df_k['feat_cvd_ratio'] = cvd.shift(1)
    df_k['feat_funding'] = df_k['funding_rate'].shift(1)
    df_k['feat_ret_15m'] = df_k['close'].pct_change().shift(1)
    df_k['feat_ret_1h'] = df_k['close'].pct_change(4).shift(1)
    df_k['feat_volatility'] = df_k['close'].rolling(14).std().shift(1)
    
    # Target (Next 6h > 0.5%)
    df_k['future_6h_return'] = (df_k['close'].shift(-24) - df_k['close']) / df_k['close']
    df_k['target_y'] = (df_k['future_6h_return'] > 0.005).astype(int)
    
    df_clean = df_k.dropna(subset=['feat_cvd_ratio', 'feat_funding', 'feat_ret_15m', 'feat_ret_1h', 'feat_volatility', 'future_6h_return', 'target_y']).copy()
    
    print("\n--- XGBOOST (NON-LINEAR) BASELINE ---")
    
    features = ['feat_cvd_ratio', 'feat_funding', 'feat_ret_15m', 'feat_ret_1h', 'feat_volatility']
    
    split1_train = df_clean[(df_clean['open_time'] >= '2024-01-01') & (df_clean['open_time'] < '2024-04-01')]
    split1_test = df_clean[(df_clean['open_time'] >= '2024-04-01') & (df_clean['open_time'] < '2024-06-01')]
    
    split2_train = df_clean[(df_clean['open_time'] >= '2024-01-01') & (df_clean['open_time'] < '2024-06-01')]
    split2_test = df_clean[(df_clean['open_time'] >= '2024-06-01') & (df_clean['open_time'] < '2024-09-01')]
    
    def evaluate(train, test, name):
        X_tr, y_tr = train[features], train['target_y']
        X_te, y_te = test[features], test['target_y']
        
        # Calculate scale_pos_weight
        spw = sum(y_tr == 0) / (sum(y_tr == 1) + 1e-8)
        
        # Train XGBoost with thermal-safe parameters
        clf = xgb.XGBClassifier(
            max_depth=3,
            n_estimators=100,
            learning_rate=0.05,
            scale_pos_weight=spw,
            random_state=42,
            n_jobs=1
        )
        clf.fit(X_tr, y_tr)
        
        preds = clf.predict(X_te)
        prec = precision_score(y_te, preds, zero_division=0)
        acc = accuracy_score(y_te, preds)
        total_signals = sum(preds)
        
        # 95% CI for precision via bootstrap
        if total_signals > 0:
            sims = []
            for _ in range(1000):
                indices = np.random.choice(len(preds), len(preds), replace=True)
                sample_preds = preds[indices]
                sample_y = y_te.values[indices]
                if sum(sample_preds) > 0:
                    sims.append(precision_score(sample_y, sample_preds, zero_division=0))
                else:
                    sims.append(0)
            ci_lower = np.percentile(sims, 2.5) if len(sims)>0 else 0
        else:
            ci_lower = 0
            
        print(f"[{name}]")
        print(f"Test Samples: {len(test)} | Total 'YES' Signals: {total_signals}")
        print(f"Precision: {prec*100:.1f}% | Accuracy: {acc*100:.1f}%")
        print(f"95% CI Lower Bound (Precision): {ci_lower*100:.1f}%")
        if prec >= 0.55 and ci_lower > 0.50:
            print("Verdict: PASSED ✅ (Precision >= 55% AND CI Lower > 50%)")
        else:
            print("Verdict: FAILED ❌")
        print("-")
        
    evaluate(split1_train, split1_test, "Window 1 (Train: Jan-Mar | Test: Apr-May)")
    evaluate(split2_train, split2_test, "Window 2 (Train: Jan-May | Test: Jun-Aug)")

if __name__ == "__main__":
    run()
