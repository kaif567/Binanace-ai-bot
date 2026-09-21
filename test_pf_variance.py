import numpy as np

def run_simulation():
    # Parameters
    target_pf = 1.15
    tp = 5.0
    sl = 2.0
    # Equation: PF = (WR * TP) / ((1 - WR) * SL)
    # target_pf * SL - target_pf * SL * WR = WR * TP
    # WR = (target_pf * SL) / (TP + target_pf * SL)
    true_wr = (target_pf * sl) / (tp + target_pf * sl)
    
    print(f"Target True PF: {target_pf:.2f}")
    print(f"Implied True Win Rate (for TP 5%, SL 2%): {true_wr*100:.2f}%\n")
    
    trade_counts = [30, 50, 70]
    iterations = 100_000
    
    for n_trades in trade_counts:
        # Simulate 'iterations' number of batches, each with 'n_trades' trades
        wins = np.random.binomial(n_trades, true_wr, size=iterations)
        losses = n_trades - wins
        
        gross_profits = wins * tp
        gross_losses = losses * sl
        
        # Avoid division by zero
        gross_losses = np.where(gross_losses == 0, 0.0001, gross_losses)
        observed_pfs = gross_profits / gross_losses
        
        # Calculate Percentiles
        p05 = np.percentile(observed_pfs, 5)
        p25 = np.percentile(observed_pfs, 25)
        p50 = np.percentile(observed_pfs, 50)
        p75 = np.percentile(observed_pfs, 75)
        p95 = np.percentile(observed_pfs, 95)
        
        # Calculate how often it "Fails" (PF < 1.0) purely due to noise
        fail_rate = np.mean(observed_pfs < 1.0) * 100
        
        print(f"--- For Sample Size: {n_trades} Trades ---")
        print(f"Expected Average PF: {np.mean(observed_pfs):.2f}")
        print(f"90% Confidence Interval: [{p05:.2f} to {p95:.2f}]")
        print(f"Probability of 'Failing' (PF < 1.0) due to noise: {fail_rate:.1f}%")
        print(f"Distribution: 25th% = {p25:.2f}, Median = {p50:.2f}, 75th% = {p75:.2f}\n")

if __name__ == "__main__":
    run_simulation()
