import time
import json
import os
import math
from datetime import datetime
from data.binance_api import get_price

# ==============================
# CONFIGURATION
# ==============================
SYMBOL = "BTCUSDT"
LOWER_BOUND = 75000.0   # 3-month support approx
UPPER_BOUND = 95000.0   # 3-month resistance approx
GRID_SPACING_PERCENT = 1.5 
TOTAL_CAPITAL = 1000.0  # Simulated USDT
FEE_RATE = 0.001        # 0.1% Binance Standard

STATE_FILE = "grid_state.json"
POLL_INTERVAL = 10      # Seconds

def generate_grid():
    levels = []
    p = LOWER_BOUND
    while p <= UPPER_BOUND:
        levels.append({
            "price": round(p, 2),
            "has_inventory": False,
            "base_amount": 0.0,
            "cost_basis": 0.0
        })
        p = p * (1 + GRID_SPACING_PERCENT/100.0)
    return levels

def init_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
            
    levels = generate_grid()
    current_price = float(get_price(SYMBOL))
    
    state = {
        "status": "RUNNING",
        "fiat": TOTAL_CAPITAL,
        "crypto": 0.0,
        "levels": levels,
        "trade_history": [],
        "last_price": current_price
    }
    save_state(state)
    return state

def save_state(state):
    # Atomic save to prevent corruption
    with open(STATE_FILE + ".tmp", "w") as f:
        json.dump(state, f, indent=4)
    os.rename(STATE_FILE + ".tmp", STATE_FILE)

def log_trade(state, side, exec_price, amount_base, amount_quote, fee_quote):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] 🟢 {side} {amount_base:.5f} BTC @ ${exec_price:.2f} | Val: ${amount_quote:.2f} | Fee: ${fee_quote:.4f}")
    
    state["trade_history"].append({
        "time": ts,
        "side": side,
        "price": exec_price,
        "base": amount_base,
        "quote": amount_quote,
        "fee_quote": fee_quote
    })

def check_grid(state, current_price):
    # 1. RANGE BREAKOUT RISK MANAGEMENT
    if current_price < LOWER_BOUND or current_price > UPPER_BOUND:
        if state["status"] == "RUNNING":
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ WARNING: Price {current_price} out of bounds ({LOWER_BOUND}-{UPPER_BOUND}). Halting new buys.")
            state["status"] = "OUT_OF_BOUNDS"
    else:
        if state["status"] == "OUT_OF_BOUNDS":
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Price back in bounds. Resuming Grid.")
            state["status"] = "RUNNING"
            
    last_price = state.get("last_price", current_price)
    levels = state["levels"]
    alloc_per_level = TOTAL_CAPITAL / len(levels)
    
    # 2. CHECK SELLS (Price crossed a grid level upwards)
    for i in range(len(levels) - 1):
        lower_lvl = levels[i]
        upper_lvl = levels[i+1]
        
        if lower_lvl["has_inventory"]:
            # If price moved from below upper_lvl to above it
            if last_price < upper_lvl["price"] <= current_price:
                # Execute SELL at upper_lvl
                base_to_sell = lower_lvl["base_amount"]
                exec_price = upper_lvl["price"]
                quote_value = base_to_sell * exec_price
                fee = quote_value * FEE_RATE
                net_quote = quote_value - fee
                
                state["crypto"] -= base_to_sell
                state["fiat"] += net_quote
                
                lower_lvl["has_inventory"] = False
                lower_lvl["base_amount"] = 0.0
                lower_lvl["cost_basis"] = 0.0
                
                log_trade(state, "SELL", exec_price, base_to_sell, quote_value, fee)
                save_state(state)

    # 3. CHECK BUYS (Price crossed a grid level downwards)
    if state["status"] == "RUNNING":
        for i in range(len(levels)):
            lvl = levels[i]
            if not lvl["has_inventory"]:
                # If price moved from above lvl to below it
                if last_price > lvl["price"] >= current_price:
                    # Execute BUY at lvl
                    exec_price = lvl["price"]
                    quote_to_spend = alloc_per_level
                    
                    if state["fiat"] >= quote_to_spend:
                        base_bought = quote_to_spend / exec_price
                        fee_base = base_bought * FEE_RATE
                        net_base = base_bought - fee_base
                        
                        state["fiat"] -= quote_to_spend
                        state["crypto"] += net_base
                        
                        lvl["has_inventory"] = True
                        lvl["base_amount"] = net_base
                        lvl["cost_basis"] = exec_price
                        
                        # Calculate fee in quote terms for logging
                        fee_quote = fee_base * exec_price
                        
                        log_trade(state, "BUY", exec_price, net_base, quote_to_spend, fee_quote)
                        save_state(state)

    state["last_price"] = current_price
    save_state(state)

def main():
    print("====================================")
    print("🤖 BTC/USDT GRID BOT (PAPER MODE) 🤖")
    print("====================================")
    
    state = init_state()
    print(f"Bounds: ${LOWER_BOUND} - ${UPPER_BOUND}")
    print(f"Grid Spacing: {GRID_SPACING_PERCENT}%")
    print(f"Total Levels: {len(state['levels'])}")
    print(f"Capital: ${TOTAL_CAPITAL}")
    print(f"Initial Price: ${state['last_price']}")
    print("Polling live price every 10 seconds...")
    print("------------------------------------")
    
    while True:
        try:
            curr = float(get_price(SYMBOL))
            check_grid(state, curr)
            sys.stdout.write(f"\rCurrent Price: ${curr:.2f} | Fiat: ${state['fiat']:.2f} | BTC: {state['crypto']:.5f}      ")
            sys.stdout.flush()
        except Exception as e:
            print(f"\nAPI Error: {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
