"""
Generate SMAD comparison figure across ALL auction types and environments.
Creates a horizontal bar chart ordered by auction type.

Auction Types:
- First-Price IPV (IPV)
- Second-Price IPV (IPV)
- Third-Price IPV (IPV)
- AC-B / Ascending Clock (APV) - Breitmoser/Li style
- SPSB APV (APV)
- First-Price Common Value (CV)
- Second-Price Common Value / English (CV)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / 'papers' / 'figures'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Experiment directories
ROBUSTNESS_DIR = PROJECT_ROOT / 'robustness_logs' / 'V10'
EXPERIMENT_DIR = PROJECT_ROOT / 'experiment_logs_with_explanation' / 'V10'
GPT4O_DIR = PROJECT_ROOT / 'experiment_logs_gpt_4o' / 'V12'
CLAUDE_DIR = PROJECT_ROOT / 'experiment_logs_claude' / 'V10'


# Auction configurations
# Format: (display_name, env_type, experiment_pattern, optimal_ratio, n_bidders)
AUCTION_CONFIGS = {
    # IPV auctions
    'fpsb_ipv': ('First-Price IPV', 'IPV', 'fpsb_ipv', lambda n: (n-1)/n, 3),
    'spsb_ipv': ('Second-Price IPV', 'IPV', 'spsb_ipv', lambda n: 1.0, 3),
    'third_price_ipv': ('Third-Price IPV', 'IPV', 'third_price_ipv', lambda n: (n-1)/(n-2), 3),

    # APV auctions (Li 2017 / Breitmoser style)
    'spsb_apv': ('SPSB (APV)', 'APV', 'spsb_apv', lambda n: 1.0, 4),
    'ascending_clock_apv': ('Ascending Clock (APV)', 'APV', 'ascending_clock_apv', lambda n: 1.0, 4),

    # CV auctions
    'common_value_first': ('First-Price CV', 'CV', 'common_value_first', None, 4),
    'common_value_second': ('Second-Price CV (English)', 'CV', 'common_value_second', None, 4),
}

# Model directories mapping
MODEL_DIRS = {
    'GPT-4o': GPT4O_DIR,
    'Claude Sonnet': CLAUDE_DIR,
    'GPT-5-mini': ROBUSTNESS_DIR,
    'Gemini': ROBUSTNESS_DIR,
    'Llama': ROBUSTNESS_DIR,
}


def load_experiment_data(base_dir: Path, pattern: str, model_suffix: str = '') -> Optional[pd.DataFrame]:
    """Load experiment data from directory matching pattern."""

    # Try different path patterns
    search_patterns = [
        base_dir / f"{pattern}{model_suffix}",
        base_dir / f"{pattern}_{model_suffix}" if model_suffix else None,
        base_dir / pattern,
    ]

    for search_dir in search_patterns:
        if search_dir is None:
            continue
        if not search_dir.exists():
            continue

        # Find all result CSVs
        csv_files = list(search_dir.rglob("*_results.csv"))
        if csv_files:
            dfs = []
            for f in csv_files:
                try:
                    df = pd.read_csv(f)
                    dfs.append(df)
                except Exception:
                    continue
            if dfs:
                return pd.concat(dfs, ignore_index=True)

    return None


def compute_smad(df: pd.DataFrame, optimal_ratio: float) -> Tuple[float, float, int]:
    """Compute SMAD and mean bid ratio from dataframe."""

    if df is None or len(df) == 0:
        return np.nan, np.nan, 0

    # Get values and bids
    values = pd.to_numeric(df['player_value'], errors='coerce').dropna()
    bids = pd.to_numeric(df['bid'], errors='coerce').dropna()

    if len(values) == 0 or len(bids) == 0:
        return np.nan, np.nan, 0

    # Align lengths
    min_len = min(len(values), len(bids))
    values = values.iloc[:min_len].values
    bids = bids.iloc[:min_len].values

    # Filter out zero values to avoid division issues
    valid_mask = values > 0.1
    values = values[valid_mask]
    bids = bids[valid_mask]

    if len(values) == 0:
        return np.nan, np.nan, 0

    # Compute bid ratio
    ratios = bids / values
    mean_ratio = np.mean(ratios)

    # Compute SMAD
    if optimal_ratio is not None:
        optimal_bids = values * optimal_ratio
        mean_optimal = np.mean(optimal_bids)
        if mean_optimal > 0:
            smad = 100 * np.mean(np.abs(bids - optimal_bids)) / mean_optimal
        else:
            smad = np.nan
    else:
        # For CV auctions, use different metric (just return ratio for now)
        smad = np.nan

    return smad, mean_ratio, len(values)


def collect_all_results() -> pd.DataFrame:
    """Collect SMAD results for all auction types and models."""

    results = []

    for auction_key, (display_name, env_type, pattern, opt_func, n_bidders) in AUCTION_CONFIGS.items():
        optimal_ratio = opt_func(n_bidders) if opt_func else None

        print(f"\nProcessing: {display_name} ({env_type})")

        # Try each model
        for model_name in ['GPT-4o', 'Claude Sonnet', 'GPT-5-mini', 'Gemini', 'Llama']:

            df = None

            # Model-specific loading logic
            if model_name == 'GPT-4o':
                # GPT-4o uses different naming convention in V12
                if 'ipv' in pattern:
                    # Map to V12 naming
                    if pattern == 'fpsb_ipv':
                        v12_pattern = 'axis1_contingent_baseline_first'
                    elif pattern == 'spsb_ipv':
                        v12_pattern = 'axis1_contingent_baseline'
                    elif pattern == 'third_price_ipv':
                        v12_pattern = 'axis1_contingent_baseline_third'
                    else:
                        v12_pattern = None

                    if v12_pattern:
                        df = load_experiment_data(GPT4O_DIR, v12_pattern)

            elif model_name in ['GPT-5-mini', 'Gemini', 'Llama', 'Claude Sonnet']:
                # Robustness logs use model suffix
                model_suffix_map = {
                    'GPT-5-mini': 'gpt5mini',
                    'Gemini': 'gemini',
                    'Llama': 'llama',
                    'Claude Sonnet': 'claude_sonnet',
                }
                suffix = model_suffix_map[model_name]

                # Try robustness logs first
                df = load_experiment_data(ROBUSTNESS_DIR, f"{pattern}_{suffix}")

                # If not found, try experiment logs with explanation (default model)
                if df is None and model_name == 'GPT-5-mini':
                    df = load_experiment_data(EXPERIMENT_DIR, pattern)

            if df is not None and len(df) > 0:
                smad, mean_ratio, n = compute_smad(df, optimal_ratio)
                print(f"  {model_name}: N={n}, Ratio={mean_ratio:.3f}, SMAD={smad:.2f}%" if not np.isnan(smad) else f"  {model_name}: N={n}, Ratio={mean_ratio:.3f}")

                results.append({
                    'Auction': display_name,
                    'Environment': env_type,
                    'Model': model_name,
                    'N': n,
                    'Mean_Ratio': mean_ratio,
                    'Optimal_Ratio': optimal_ratio,
                    'SMAD': smad,
                })
            else:
                print(f"  {model_name}: No data found")

    return pd.DataFrame(results)


def plot_horizontal_bar_chart(df: pd.DataFrame):
    """Create horizontal bar chart of SMAD by auction type."""

    # Filter to valid SMAD values
    df = df[df['SMAD'].notna()].copy()

    if len(df) == 0:
        print("No valid SMAD data to plot!")
        return

    # Define auction order (by environment type)
    auction_order = [
        'First-Price IPV',
        'Second-Price IPV',
        'Third-Price IPV',
        'SPSB (APV)',
        'Ascending Clock (APV)',
        'First-Price CV',
        'Second-Price CV (English)',
    ]

    # Filter to auctions we have data for
    available_auctions = [a for a in auction_order if a in df['Auction'].values]

    # Get unique models
    models = df['Model'].unique()
    n_models = len(models)

    # Color palette for models
    model_colors = {
        'GPT-4o': '#e74c3c',
        'Claude Sonnet': '#9b59b6',
        'GPT-5-mini': '#3498db',
        'Gemini': '#2ecc71',
        'Llama': '#f39c12',
    }

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 10))

    # Bar settings
    bar_height = 0.15
    y_positions = np.arange(len(available_auctions))

    # Plot bars for each model
    for i, model in enumerate(models):
        model_data = df[df['Model'] == model]

        smad_values = []
        for auction in available_auctions:
            row = model_data[model_data['Auction'] == auction]
            if len(row) > 0:
                smad_values.append(row['SMAD'].values[0])
            else:
                smad_values.append(0)

        offset = (i - n_models/2 + 0.5) * bar_height
        color = model_colors.get(model, '#95a5a6')

        bars = ax.barh(y_positions + offset, smad_values, bar_height,
                       label=model, color=color, edgecolor='black', linewidth=0.5)

        # Add value labels
        for bar, val in zip(bars, smad_values):
            if val > 0:
                ax.text(val + 1, bar.get_y() + bar.get_height()/2,
                       f'{val:.1f}', va='center', fontsize=8)

    # Formatting
    ax.set_yticks(y_positions)
    ax.set_yticklabels(available_auctions, fontsize=11)
    ax.set_xlabel('SMAD (%) - Lower is Better', fontsize=12, fontweight='bold')
    ax.set_title('Scaled Mean Absolute Deviation (SMAD) Across All Auction Types\nBy Model and Environment',
                fontsize=14, fontweight='bold')

    # Add environment type annotations
    env_colors = {'IPV': '#e8f4f8', 'APV': '#f8f4e8', 'CV': '#f4e8f8'}

    # Draw background rectangles for environment types
    current_env = None
    env_start = 0
    for idx, auction in enumerate(available_auctions):
        env = df[df['Auction'] == auction]['Environment'].values[0]
        if env != current_env:
            if current_env is not None:
                ax.axhspan(env_start - 0.5, idx - 0.5, alpha=0.3,
                          color=env_colors.get(current_env, '#f0f0f0'), zorder=0)
            current_env = env
            env_start = idx
    # Final environment
    ax.axhspan(env_start - 0.5, len(available_auctions) - 0.5, alpha=0.3,
              color=env_colors.get(current_env, '#f0f0f0'), zorder=0)

    # Add environment labels on right side
    env_positions = {}
    for idx, auction in enumerate(available_auctions):
        env = df[df['Auction'] == auction]['Environment'].values[0]
        if env not in env_positions:
            env_positions[env] = []
        env_positions[env].append(idx)

    for env, positions in env_positions.items():
        mid_pos = np.mean(positions)
        ax.text(ax.get_xlim()[1] * 1.02, mid_pos, env,
               va='center', ha='left', fontsize=10, fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.3', facecolor=env_colors.get(env, 'white'),
                        edgecolor='gray', alpha=0.8))

    # Legend
    ax.legend(title='Model', loc='lower right', fontsize=10)

    # Grid
    ax.xaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    # Optimal line at 0
    ax.axvline(x=0, color='green', linestyle='--', linewidth=2, alpha=0.7)

    plt.tight_layout()

    # Save
    output_path = OUTPUT_DIR / 'smad_all_auctions_horizontal.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')
    print(f"\nSaved: {output_path}")
    print(f"Saved: {output_path.with_suffix('.pdf')}")

    plt.close()


def plot_simple_model_comparison(df: pd.DataFrame):
    """Create a simpler version focusing on available data."""

    # Filter to valid SMAD values
    df = df[df['SMAD'].notna() & (df['N'] > 0)].copy()

    if len(df) == 0:
        print("No valid SMAD data to plot!")
        return

    # Create pivot table
    pivot = df.pivot_table(index='Auction', columns='Model', values='SMAD', aggfunc='mean')

    # Order by environment
    env_order = df.drop_duplicates('Auction').set_index('Auction')['Environment']

    # Sort
    auction_order = []
    for env in ['IPV', 'APV', 'CV']:
        auctions = env_order[env_order == env].index.tolist()
        auction_order.extend(auctions)

    pivot = pivot.reindex([a for a in auction_order if a in pivot.index])

    # Plot
    fig, ax = plt.subplots(figsize=(12, 8))

    pivot.plot(kind='barh', ax=ax, width=0.8, edgecolor='black', linewidth=0.5)

    ax.set_xlabel('SMAD (%) - Lower is Better', fontsize=12, fontweight='bold')
    ax.set_title('SMAD Across All Auction Types and Models',
                fontsize=14, fontweight='bold')
    ax.legend(title='Model', loc='lower right')
    ax.xaxis.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save
    output_path = OUTPUT_DIR / 'smad_all_auctions_simple.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.with_suffix('.pdf'), bbox_inches='tight')
    print(f"\nSaved: {output_path}")

    plt.close()


def main():
    """Main execution."""
    print("="*70)
    print("SMAD ACROSS ALL AUCTION TYPES")
    print("="*70)

    # Collect results
    results_df = collect_all_results()

    # Print summary
    print("\n" + "="*70)
    print("SUMMARY TABLE")
    print("="*70)

    if len(results_df) > 0:
        pivot = results_df.pivot_table(
            index='Auction',
            columns='Model',
            values='SMAD',
            aggfunc='mean'
        )
        print("\nSMAD (%) by Auction and Model:")
        print(pivot.to_string())

        # Save to CSV
        results_df.to_csv(OUTPUT_DIR / 'smad_all_auctions_data.csv', index=False)
        print(f"\nData saved to: {OUTPUT_DIR / 'smad_all_auctions_data.csv'}")

    # Generate plots
    print("\n" + "="*70)
    print("Generating plots...")
    print("="*70)

    plot_horizontal_bar_chart(results_df)
    plot_simple_model_comparison(results_df)

    print("\n" + "="*70)
    print("COMPLETE!")
    print("="*70)


if __name__ == '__main__':
    main()
