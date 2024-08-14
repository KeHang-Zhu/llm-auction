import matplotlib.pyplot as plt
import seaborn as sb
import numpy as np
import pandas as pd
import statsmodels.api as statsmodels
import matplotlib.patheffects as path_effects

plot_type = 'FPSB' # Change to SPSB if you want SPSB plots.

# Load the data
binary_results = pd.read_csv('binary_results.csv')

# Filter for FPSB vs SPSB auction data.
if plot_type == 'FPSB':
  fpsb_df = binary_results[binary_results['First'] == 1]
else:
  fpsb_df = binary_results[binary_results['First'] == 0]

# Setting up the subplots
fig, axs = plt.subplots(1, 3, figsize=(24, 8), dpi=120)
plt.subplots_adjust(wspace=0.3)

# Color palette
color_palette = sb.color_palette("Paired")

# Function to create scatter plot
def create_scatter(ax, df, x_col, y_col, color_col, title):
    # Create scatter plot
    scatter = sb.scatterplot(ax=ax, x=df[x_col], y=df[y_col], hue=df[color_col],
                             palette="coolwarm", legend=False, alpha=0.7, marker='^', s=40)
    
    # Add NE line (y = 2/3 * x) in red
    x_vals = np.linspace(df[x_col].min(), df[x_col].max(), 100)
    NE_line = 2/3 * x_vals
    ax.plot(x_vals, NE_line, color='red', linewidth=3)
    
    # Add 45° line
    ax.plot(x_vals, x_vals, '-.', color='black', linewidth=1)
    ax.text(42, 60, '45° line', fontsize=10)
    
    # Add predicted bid text
    ax.text(x_vals[-15], NE_line[-30], 'Predicted bid', verticalalignment='bottom',
            horizontalalignment='left', color='red', fontweight='normal', fontsize=10)
    ax.text(x_vals[-15], NE_line[-30] - 7, 'given v ~ U[0, 99]', verticalalignment='bottom',
            horizontalalignment='left', color='red', fontweight='normal', fontsize=10)
    ax.text(x_vals[-15], NE_line[-30] - 14, '& 3 bidders', verticalalignment='bottom',
            horizontalalignment='left', color='red', fontweight='normal', fontsize=10)
    
    # Add LOWESS smoothed line
    lowess = statsmodels.nonparametric.lowess(df[y_col], df[x_col], frac=0.6)
    ax.plot(lowess[:, 0], lowess[:, 1], '--', color='black', linewidth=3)
    ax.text(127, 85, 'Smoothed Data', verticalalignment='top', horizontalalignment='right',
            color='black', fontweight='normal', fontsize=11)
    
    # Add arrows
    arrow_props = dict(head_width=2, head_length=1, fc='blue', ec='black', length_includes_head=True)
    ax.arrow(60, 40, 0, 7, **arrow_props)
    ax.arrow(90, 60, 0, 7, **arrow_props)
    ax.arrow(75, 50, 0, 7, **arrow_props)
    
    # Set labels and title
    ax.set_xlabel("LLM agent's assigned value for the good", size=13)
    ax.set_ylabel("LLM agent's bid", size=14)
    ax.set_title(title, size=16)
    ax.set_xlim(0, 127)
    ax.set_ylim(0, 127)
    
    # Add colorbar
    sm = plt.cm.ScalarMappable(cmap="coolwarm", norm=plt.Normalize(vmin=0, vmax=1))
    cbar = plt.colorbar(sm, ax=ax)
    cbar.set_label(color_col, size=10)
    
    return scatter

# Create scatter plots
if plot_type == 'FPSB':
  create_scatter(axs[0], fpsb_df, 'Value', 'Bid', 'risk2', 'First Price Sealed Bid (IPV)\nRisk2 Coloring')
  create_scatter(axs[1], fpsb_df, 'Value', 'Bid', 'strategy2', 'First Price Sealed Bid (IPV)\nStrategy2 Coloring')
  create_scatter(axs[2], fpsb_df, 'Value', 'Bid', 'understand2', 'First Price Sealed Bid (IPV)\nUnderstand2 Coloring')
else:
  create_scatter(axs[0], fpsb_df, 'Value', 'Bid', 'risk2', 'Second Price Sealed Bid (IPV)\nRisk2 Coloring')
  create_scatter(axs[1], fpsb_df, 'Value', 'Bid', 'strategy2', 'Second Price Sealed Bid (IPV)\nStrategy2 Coloring')
  create_scatter(axs[2], fpsb_df, 'Value', 'Bid', 'understand2', 'Second Price Sealed Bid (IPV)\nUnderstand2 Coloring')  

plt.tight_layout()
plt.show()
