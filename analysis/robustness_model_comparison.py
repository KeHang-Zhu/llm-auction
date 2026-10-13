"""
Model Comparison Plots for Robustness Testing

Compares FPSB and TPSB bidding behavior across different LLM models:
- GPT-5-mini
- Claude Sonnet
- Gemini
- Llama
- GPT-4o (temp 0.1, temp 1.0)

Creates bid vs value scatter plots comparing models.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


# Paths
ROBUSTNESS_DIR = Path("robustness_logs/V10")
OUTPUT_DIR = Path("results/v12_interventions/model_comparison")

# Model configurations
MODELS = {
    'gpt5mini': {'name': 'GPT-5-mini', 'color': '#1f77b4'},
    'claude_sonnet': {'name': 'Claude Sonnet', 'color': '#d62728'},
    'gemini': {'name': 'Gemini', 'color': '#2ca02c'},
    'llama': {'name': 'Llama', 'color': '#ff7f0e'},
    'gpt4o_temp01': {'name': 'GPT-4o (t=0.1)', 'color': '#9467bd'},
    'gpt4o_temp10': {'name': 'GPT-4o (t=1.0)', 'color': '#8c564b'},
}

# Auction types to compare
AUCTIONS = {
    'fpsb_ipv': {'name': 'First-Price IPV', 'optimal_ratio': 2/3},
    'third_price_ipv': {'name': 'Third-Price IPV', 'optimal_ratio': 2.0},
    'spsb_ipv': {'name': 'Second-Price IPV', 'optimal_ratio': 1.0},
}


def load_model_data(auction_type: str, model_key: str) -> pd.DataFrame:
    """Load experiment data for a specific auction and model."""
    exp_name = f"{auction_type}_{model_key}"
    exp_path = ROBUSTNESS_DIR / exp_name

    if not exp_path.exists():
        return pd.DataFrame()

    dfs = []
    for csv_file in exp_path.rglob("*_results.csv"):
        try:
            df = pd.read_csv(csv_file)
            dfs.append(df)
        except Exception:
            pass

    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        df['player_value'] = pd.to_numeric(df['player_value'], errors='coerce')
        df['bid'] = pd.to_numeric(df['bid'], errors='coerce')
        df = df.dropna(subset=['player_value', 'bid'])
        df = df[df['player_value'] > 0]
        return df
    return pd.DataFrame()


def compute_metrics(df: pd.DataFrame, optimal_ratio: float) -> dict:
    """Compute bidding metrics."""
    if df.empty:
        return {'n': 0, 'mean_ratio': np.nan, 'std_ratio': np.nan, 'smad': np.nan, 'dist_from_optimal': np.nan}

    values = df['player_value'].values
    bids = df['bid'].values

    # Bid/value ratio
    ratios = bids / values
    mean_ratio = np.mean(ratios)
    std_ratio = np.std(ratios)

    # SMAD (distance from optimal)
    optimal_bids = values * optimal_ratio
    smad = 100 * np.mean(np.abs(bids - optimal_bids)) / np.mean(optimal_bids)

    return {
        'n': len(df),
        'mean_ratio': mean_ratio,
        'std_ratio': std_ratio,
        'smad': smad,
        'dist_from_optimal': abs(mean_ratio - optimal_ratio)
    }


def plot_model_comparison_scatter(auction_type: str, output_dir: Path):
    """Create scatter plot comparing all models for one auction type."""
    auction_info = AUCTIONS[auction_type]

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    results = []

    for idx, (model_key, model_info) in enumerate(MODELS.items()):
        if idx >= len(axes):
            break

        ax = axes[idx]
        df = load_model_data(auction_type, model_key)

        if df.empty:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center',
                   transform=ax.transAxes, fontsize=12)
            ax.set_title(model_info['name'], fontsize=11, fontweight='bold')
            continue

        values = df['player_value'].values
        bids = df['bid'].values

        # Scatter plot
        ax.scatter(values, bids, alpha=0.3, s=15, c=model_info['color'], edgecolors='none')

        # Optimal line
        x_line = np.linspace(0, max(values.max(), 50), 100)
        y_optimal = x_line * auction_info['optimal_ratio']
        ax.plot(x_line, y_optimal, 'g--', linewidth=2, alpha=0.8,
               label=f"Optimal ({auction_info['optimal_ratio']:.2f}·v)")

        # Identity line (bid = value)
        ax.plot(x_line, x_line, 'k:', linewidth=1, alpha=0.5, label='bid = value')

        # Mean bid line
        mean_ratio = np.mean(bids / values)
        y_mean = x_line * mean_ratio
        ax.plot(x_line, y_mean, 'r-', linewidth=1.5, alpha=0.7,
               label=f'Mean ({mean_ratio:.2f}·v)')

        # Metrics
        metrics = compute_metrics(df, auction_info['optimal_ratio'])
        results.append({
            'Model': model_info['name'],
            'N': metrics['n'],
            'Mean_Ratio': metrics['mean_ratio'],
            'Std_Ratio': metrics['std_ratio'],
            'SMAD': metrics['smad'],
            'Dist_from_Optimal': metrics['dist_from_optimal']
        })

        # Labels
        ax.set_xlabel('Value', fontsize=9)
        ax.set_ylabel('Bid', fontsize=9)
        ax.set_title(model_info['name'], fontsize=11, fontweight='bold')

        # Limits
        max_val = max(values.max(), bids.max(), 50)
        ax.set_xlim(0, max_val * 1.05)
        if 'third' in auction_type:
            ax.set_ylim(0, max_val * 2.5)
        else:
            ax.set_ylim(0, max_val * 1.1)

        ax.grid(True, alpha=0.2)
        ax.legend(loc='upper left', fontsize=8)

        # Stats box
        stats_text = f'N={metrics["n"]}\nμ(b/v)={metrics["mean_ratio"]:.2f}\nSMAD={metrics["smad"]:.1f}%'
        ax.text(0.98, 0.02, stats_text, transform=ax.transAxes, fontsize=8,
               verticalalignment='bottom', horizontalalignment='right',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    # Hide unused axes
    for idx in range(len(MODELS), len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle(f"{auction_info['name']}: Model Comparison", fontsize=14, fontweight='bold')
    plt.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / f'{auction_type}_model_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()

    return pd.DataFrame(results)


def plot_fp_tp_comparison(output_dir: Path):
    """Create side-by-side FP vs TP comparison across models."""
    fig, axes = plt.subplots(len(MODELS), 2, figsize=(14, 4 * len(MODELS)))

    fp_info = AUCTIONS['fpsb_ipv']
    tp_info = AUCTIONS['third_price_ipv']

    all_results = []

    for idx, (model_key, model_info) in enumerate(MODELS.items()):
        # First-Price
        ax_fp = axes[idx, 0]
        df_fp = load_model_data('fpsb_ipv', model_key)

        if not df_fp.empty:
            values = df_fp['player_value'].values
            bids = df_fp['bid'].values
            ax_fp.scatter(values, bids, alpha=0.3, s=15, c='#1f77b4', edgecolors='none')

            x_line = np.linspace(0, max(values.max(), 50), 100)
            ax_fp.plot(x_line, x_line * fp_info['optimal_ratio'], 'g--', lw=2, label='Optimal (2/3·v)')
            ax_fp.plot(x_line, x_line, 'k:', lw=1, alpha=0.5, label='bid = value')

            mean_ratio = np.mean(bids / values)
            ax_fp.plot(x_line, x_line * mean_ratio, 'r-', lw=1.5, alpha=0.7, label=f'Mean ({mean_ratio:.2f}·v)')

            metrics_fp = compute_metrics(df_fp, fp_info['optimal_ratio'])
            ax_fp.set_xlim(0, 55)
            ax_fp.set_ylim(0, 55)

            stats_text = f'N={metrics_fp["n"]}, μ(b/v)={metrics_fp["mean_ratio"]:.2f}, SMAD={metrics_fp["smad"]:.1f}%'
            ax_fp.text(0.02, 0.98, stats_text, transform=ax_fp.transAxes, fontsize=8,
                      verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        else:
            ax_fp.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax_fp.transAxes)
            metrics_fp = {'mean_ratio': np.nan, 'smad': np.nan, 'n': 0}

        ax_fp.set_xlabel('Value')
        ax_fp.set_ylabel('Bid')
        ax_fp.set_title(f'{model_info["name"]} - First-Price', fontsize=10, fontweight='bold')
        ax_fp.grid(True, alpha=0.2)
        ax_fp.legend(loc='lower right', fontsize=7)

        # Third-Price
        ax_tp = axes[idx, 1]
        df_tp = load_model_data('third_price_ipv', model_key)

        if not df_tp.empty:
            values = df_tp['player_value'].values
            bids = df_tp['bid'].values
            ax_tp.scatter(values, bids, alpha=0.3, s=15, c='#d62728', edgecolors='none')

            x_line = np.linspace(0, max(values.max(), 50), 100)
            ax_tp.plot(x_line, x_line * tp_info['optimal_ratio'], 'g--', lw=2, label='Optimal (2·v)')
            ax_tp.plot(x_line, x_line, 'k:', lw=1, alpha=0.5, label='bid = value')

            mean_ratio = np.mean(bids / values)
            ax_tp.plot(x_line, x_line * mean_ratio, 'r-', lw=1.5, alpha=0.7, label=f'Mean ({mean_ratio:.2f}·v)')

            metrics_tp = compute_metrics(df_tp, tp_info['optimal_ratio'])
            ax_tp.set_xlim(0, 55)
            ax_tp.set_ylim(0, 120)

            stats_text = f'N={metrics_tp["n"]}, μ(b/v)={metrics_tp["mean_ratio"]:.2f}, SMAD={metrics_tp["smad"]:.1f}%'
            ax_tp.text(0.02, 0.98, stats_text, transform=ax_tp.transAxes, fontsize=8,
                      verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        else:
            ax_tp.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax_tp.transAxes)
            metrics_tp = {'mean_ratio': np.nan, 'smad': np.nan, 'n': 0}

        ax_tp.set_xlabel('Value')
        ax_tp.set_ylabel('Bid')
        ax_tp.set_title(f'{model_info["name"]} - Third-Price', fontsize=10, fontweight='bold')
        ax_tp.grid(True, alpha=0.2)
        ax_tp.legend(loc='lower right', fontsize=7)

        all_results.append({
            'Model': model_info['name'],
            'FP_N': metrics_fp.get('n', 0),
            'FP_Mean_Ratio': metrics_fp.get('mean_ratio', np.nan),
            'FP_SMAD': metrics_fp.get('smad', np.nan),
            'TP_N': metrics_tp.get('n', 0),
            'TP_Mean_Ratio': metrics_tp.get('mean_ratio', np.nan),
            'TP_SMAD': metrics_tp.get('smad', np.nan),
        })

    fig.suptitle('Model Comparison: First-Price vs Third-Price Auctions', fontsize=14, fontweight='bold')
    plt.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / 'fp_vs_tp_model_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()

    return pd.DataFrame(all_results)


def create_summary_table(output_dir: Path):
    """Create summary table of all models and auction types."""
    results = []

    for auction_key, auction_info in AUCTIONS.items():
        for model_key, model_info in MODELS.items():
            df = load_model_data(auction_key, model_key)
            metrics = compute_metrics(df, auction_info['optimal_ratio'])

            results.append({
                'Auction': auction_info['name'],
                'Model': model_info['name'],
                'N': metrics['n'],
                'Mean_Bid_Ratio': metrics['mean_ratio'],
                'Std_Bid_Ratio': metrics['std_ratio'],
                'Optimal_Ratio': auction_info['optimal_ratio'],
                'Distance_from_Optimal': metrics['dist_from_optimal'],
                'SMAD': metrics['smad']
            })

    results_df = pd.DataFrame(results)

    output_dir.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(output_dir / 'model_comparison_summary.csv', index=False)

    return results_df


if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Agg')

    print("="*70)
    print("MODEL COMPARISON ANALYSIS")
    print("="*70)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate comparison plots
    print("\nGenerating FP vs TP model comparison...")
    fp_tp_results = plot_fp_tp_comparison(OUTPUT_DIR)
    print(fp_tp_results.to_string())

    # Generate individual auction plots
    for auction in AUCTIONS.keys():
        print(f"\nGenerating {auction} comparison...")
        results = plot_model_comparison_scatter(auction, OUTPUT_DIR)
        if not results.empty:
            print(results.to_string())

    # Create summary table
    print("\nGenerating summary table...")
    summary = create_summary_table(OUTPUT_DIR)
    print("\nSummary:")
    print(summary.to_string())

    print(f"\nResults saved to {OUTPUT_DIR}")
    print("="*70)
