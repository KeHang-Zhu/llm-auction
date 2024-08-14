import matplotlib.pyplot as plt
import seaborn as sb
import numpy as np
import pandas as pd
import statsmodels.api as statsmodels
import matplotlib.patheffects as path_effects

def create_scatter(ax, df, x_col, y_col, color_col, title, show_y_axis=True):
    # Create scatter plot
    scatter = sb.scatterplot(ax=ax, x=df[x_col], y=df[y_col], hue=df[color_col],
                             palette="coolwarm", legend=False, alpha=0.7, marker='^', s=60)
    
    # Add NE line (y = 2/3 * x) in red
    x_vals = np.linspace(df[x_col].min(), df[x_col].max(), 100)
    NE_line = 2/3 * x_vals
    ax.plot(x_vals, NE_line, color='red', linewidth=3)
    
    # Add 45° line
    ax.plot(x_vals, x_vals, '-.', color='black', linewidth=1)
    ax.text(102, 100, '45° line', fontsize=10)
    
    # Add predicted bid text
    ax.text(x_vals[-15], NE_line[-30], 'Predicted bid', verticalalignment='bottom',
            horizontalalignment='left', color='red', fontweight='normal', fontsize=10)
    
    # Add LOWESS smoothed line
    lowess = statsmodels.nonparametric.lowess(df[y_col], df[x_col], frac=0.2)
    ax.plot(lowess[:, 0], lowess[:, 1], '--', color='black', linewidth=3)
    ax.text(127, 85, 'Smoothed\nData', verticalalignment='top', horizontalalignment='right',
            color='black', fontweight='normal', fontsize=11)
    
    # Set labels and title
    ax.set_xlabel("Assigned value for the good", size=13)
    if show_y_axis:
        ax.set_ylabel("LLM agent's bid", size=14)
    else:
        ax.set_ylabel("")
        # ax.yaxis.set_ticks([])
    ax.set_title(title, size=16)
    ax.set_xlim(0, 127)
    ax.set_ylim(0, 127)
    
    # Add color legend at the bottom
    if color_col == 'risk2':
        legend_text_left = 'Risk-averse'
        legend_text_right = 'Non risk-averse'
    elif color_col == 'strategy2':
        legend_text_left = 'Strategically uncertain'
        legend_text_right = 'Strategically certain'
    elif color_col == 'understand2':
        legend_text_left = 'Weak understanding'
        legend_text_right = 'Strong understanding'
    
    # Use color_palette to get the correct colors
    colors = sb.color_palette("coolwarm", 2)
    
    # Add colored text for legend
    # ax.text(0.5, -0.15, legend_text, transform=ax.transAxes, ha='center', va='center', fontsize=10)

    
    # Add colored triangles and text for legend in two rows
    triangle_size = 60
    square_size  = 12
    y_positions = [-0.22, -0.17]  # Positions for two rows
    
    # First row (left item)
    ax.scatter([0.25], [y_positions[0]], c=[colors[0]], marker='^', s=triangle_size, 
               transform=ax.transAxes)
    ax.text(0.28, y_positions[0], legend_text_left, transform=ax.transAxes, 
            ha='left', va='center', fontsize=10)
    ax.text(0.23, y_positions[0], '▲', color=colors[0], transform=ax.transAxes, 
            ha='right', va='center', fontsize=square_size)
    
    # Second row (right item)
    ax.scatter([0.25], [y_positions[1]], c=[colors[1]], marker='^', s=triangle_size, 
               transform=ax.transAxes)
    ax.text(0.28, y_positions[1], legend_text_right, transform=ax.transAxes, 
            ha='left', va='center', fontsize=10)
    ax.text(0.23, y_positions[1], '▲', color=colors[1], transform=ax.transAxes, 
            ha='right', va='center', fontsize=square_size)

    return scatter

plot_type = 'SPSB' # Change to SPSB if you want SPSB plots.

# Load the data
binary_results = pd.read_csv('binary_results.csv')

# Filter for FPSB vs SPSB auction data.
if plot_type == 'FPSB':
  fpsb_df = binary_results[binary_results['First'] == 1]
else:
  fpsb_df = binary_results[binary_results['First'] == 0]


fig, axs = plt.subplots(1, 3, figsize=(12, 6), dpi=120)
plt.subplots_adjust(wspace=0.3, bottom=0.25)

# Set the main title
main_title = 'First-Price Sealed-Bid (IPV)' if plot_type == 'FPSB' else 'Second-Price Sealed-Bid (IPV)'
fig.suptitle(main_title, fontsize=20, fontweight='bold')

if plot_type == 'FPSB':
    create_scatter(axs[0], fpsb_df, 'Value', 'Bid', 'risk2', 'Risk Level', show_y_axis=True)
    create_scatter(axs[1], fpsb_df, 'Value', 'Bid', 'strategy2', 'Strategy Level', show_y_axis=False)
    create_scatter(axs[2], fpsb_df, 'Value', 'Bid', 'understand2', 'Familiarity Level', show_y_axis=False)
else:
    create_scatter(axs[0], fpsb_df, 'Value', 'Bid', 'risk2', 'Risk Level', show_y_axis=True)
    create_scatter(axs[1], fpsb_df, 'Value', 'Bid', 'strategy2', 'Strategy Level', show_y_axis=False)
    create_scatter(axs[2], fpsb_df, 'Value', 'Bid', 'understand2', 'Familiarity Level', show_y_axis=False)

plt.tight_layout(rect=[0, 0.01, 1, 0.99])  # Adjust layout to accommodate main title
plt.show()