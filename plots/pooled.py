import numpy as np

def run_pooled_smad_monte_carlo_normalized(n_sims=50000, n_mc_runs=100):
    """
    Monte Carlo simulation to estimate SMAD using the 'Range Normalization' method.
    
    Normalization Factor: E[b*_max - b*_min]
    This isolates strategic deviation relative to the spread of information, 
    rather than the total value of the item.
    """
    
    # Data from Levin et al. (1996) Table 2 (Inexperienced Bidders, N=4)
    # Format: (epsilon, n_periods, actual_profit_fp, theory_profit_fp, actual_profit_sp, theory_profit_sp)
    data_points = [
        {'eps': 6,  'n': 29, 'act_fp': -2.13, 'thy_fp': 2.76, 'act_sp': -0.58, 'thy_sp': 1.23},
        {'eps': 12, 'n': 41, 'act_fp': -1.32, 'thy_fp': 5.01, 'act_sp': -0.78, 'thy_sp': 2.25},
        {'eps': 24, 'n': 25, 'act_fp': 1.20,  'thy_fp': 9.83, 'act_sp': 0.11,  'thy_sp': 1.73}
    ]

    N_bidders = 4
    X_MIN, X_MAX = 50.0, 250.0  # Bounds for true value x0
    
    # Store weighted results
    total_periods = sum(d['n'] for d in data_points)
    weighted_smad_fp = []
    weighted_smad_sp = []
    
    for run_idx in range(n_mc_runs):
        
        run_smad_fp_accum = 0.0
        run_smad_sp_accum = 0.0
        
        for d in data_points:
            eps = d['eps']
            weight = d['n'] / total_periods
            
            # 1. Simulate DGP (Data Generating Process)
            # Reshape v to (n_sims, 1) for correct broadcasting
            v = np.random.uniform(X_MIN, X_MAX, n_sims).reshape(-1, 1)
            
            # Signals: Uniform[v - eps, v + eps] -> Shape (n_sims, N_bidders)
            signals = np.random.uniform(v - eps, v + eps, size=(n_sims, N_bidders))
            
            # 2. Theoretical Benchmarks (RNNE)
            # FP: b*(x) = x - eps (Approximate for Region 2)
            b_star_fp_all = signals - eps
            
            # SP (English): b*(x) = x
            b_star_sp_all = signals
            
            # 3. Calibration (Moment Matching to recover Human Bids)
            # Shift = Theory Profit - Actual Profit (Positive shift = Overbidding)
            shift_fp = d['thy_fp'] - d['act_fp']
            shift_sp = d['thy_sp'] - d['act_sp']
            
            b_human_fp_all = b_star_fp_all + shift_fp
            b_human_sp_all = b_star_sp_all + shift_sp
            
            # 4. Compute New Normalization Factor (Expected Range of Equilibrium Bids)
            # We calculate the range (Max - Min) for EACH auction simulation, then average them.
            
            # range for FP: shape (n_sims,)
            range_fp = np.max(b_star_fp_all, axis=1) - np.min(b_star_fp_all, axis=1)
            denom_fp = np.mean(range_fp)
            
            # range for SP: shape (n_sims,)
            range_sp = np.max(b_star_sp_all, axis=1) - np.min(b_star_sp_all, axis=1)
            denom_sp = np.mean(range_sp)
            
            # 5. Compute SMAD
            # Numerator: Mean Absolute Deviation
            # Denominator: Expected Range
            
            # FP SMAD
            mad_fp = np.mean(np.abs(b_human_fp_all - b_star_fp_all))
            smad_fp = 100.0 * mad_fp / denom_fp
            
            # SP SMAD
            mad_sp = np.mean(np.abs(b_human_sp_all - b_star_sp_all))
            smad_sp = 100.0 * mad_sp / denom_sp
            
            # Accumulate weighted average
            run_smad_fp_accum += smad_fp * weight
            run_smad_sp_accum += smad_sp * weight
            
        weighted_smad_fp.append(run_smad_fp_accum)
        weighted_smad_sp.append(run_smad_sp_accum)

    return {
        "FP_CV": (np.mean(weighted_smad_fp), np.std(weighted_smad_fp)),
        "English_Proxy": (np.mean(weighted_smad_sp), np.std(weighted_smad_sp))
    }

if __name__ == "__main__":
    results = run_pooled_smad_monte_carlo_normalized()
    print("=== Pooled Results (Inexperienced, N=4) with Range Normalization ===")
    print("Normalization Factor: E[b*_max - b*_min]")
    print("-" * 60)
    print(f"First-Price CV SMAD: {results['FP_CV'][0]:.2f}% (std: {results['FP_CV'][1]:.2f})")
    print(f"English (SP) SMAD:   {results['English_Proxy'][0]:.2f}% (std: {results['English_Proxy'][1]:.2f})")