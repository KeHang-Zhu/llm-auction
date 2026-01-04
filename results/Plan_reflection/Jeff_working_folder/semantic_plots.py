import matplotlib.pyplot as plt
import seaborn as sb
import numpy as np
import pandas as pd
import statsmodels.api as statsmodels

# Ensure plots display correctly in Colab
%matplotlib inline

def create_scatter(ax, df, x_col, y_col, color_col, title, show_y_axis=True):
    colors = ['#FF9999', '#66B2FF']
    scatter_0 = ax.scatter(df[df[color_col] == 0][x_col], df[df[color_col] == 0][y_col], 
                           c=colors[0], marker='^', s=60, alpha=0.4)
    scatter_1 = ax.scatter(df[df[color_col] == 1][x_col], df[df[color_col] == 1][y_col], 
                           c=colors[1], marker='o', s=40, alpha=0.4)
    
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
    
    # Add separate LOWESS smoothed lines for color_col == 0 and color_col == 1
    lowess_0 = statsmodels.nonparametric.lowess(df[df[color_col] == 0][y_col], df[df[color_col] == 0][x_col], frac=0.2)
    lowess_1 = statsmodels.nonparametric.lowess(df[df[color_col] == 1][y_col], df[df[color_col] == 1][x_col], frac=0.2)
    print(colors[0],"zero color")
    print(colors[1],"one color")
    
    # Plot LOWESS line for color_col == 0 (in the same color as the scatter points)
    ax.plot(lowess_0[:, 0], lowess_0[:, 1], '--', color=colors[0], linewidth=3, label=f'Smoothed Data (0)')
    
    # Plot LOWESS line for color_col == 1 (in the same color as the scatter points)
    ax.plot(lowess_1[:, 0], lowess_1[:, 1], '--', color=colors[1], linewidth=3, label=f'Smoothed Data (1)')
  
    if show_y_axis:
        ax.set_ylabel("LLM agent's bid", size=14)
    else:
        ax.set_ylabel("")
    
    ax.set_title(title, size=16)
    ax.set_xlim(0, 127)
    ax.set_ylim(0, 127)
    
    # Add color legend at the bottom
    if color_col == 'risk2':
        legend_text_left = '0: Conservative'
        legend_text_right = '1: Aggressive'
    elif color_col == 'strategy2':
        legend_text_left = '0: Interactive strategy'
        legend_text_right = '1: Isolated strategy'
    elif color_col == 'understand2':
        legend_text_left = '0: Weak understanding'
        legend_text_right = '1: Strong understanding'
    
    triangle_size = 40
    square_size  = 12
    y_positions = [-0.22, -0.17]
    
    ax.scatter([0.25], [y_positions[0]], c=[colors[0]], marker='^', s=triangle_size, 
               transform=ax.transAxes)
    ax.text(0.28, y_positions[0], legend_text_left, transform=ax.transAxes, 
            ha='left', va='center', fontsize=10)
    ax.scatter([0.25], [y_positions[1]], c=[colors[1]], marker='*', s=triangle_size, 
               transform=ax.transAxes)
    ax.text(0.28, y_positions[1], legend_text_right, transform=ax.transAxes, 
            ha='left', va='center', fontsize=10)
    
    return scatter_0, scatter_1

plot_type = 'FPSB'

binary_results = pd.read_csv('/content/llm-auction/results/Plan_reflection/Jeff_working_folder/binary_risk2_results_new2.csv')

fpsb_df = binary_results[binary_results['First'] == 1] if plot_type == 'FPSB' else binary_results[binary_results['First'] == 0]

fig, axs = plt.subplots(1, 3, figsize=(12, 6), dpi=120)
plt.subplots_adjust(wspace=0.3, bottom=0.25)

main_title = 'First-Price Sealed-Bid (IPV)' if plot_type == 'FPSB' else 'Second-Price Sealed-Bid (IPV)'
fig.suptitle(main_title, fontsize=20, fontweight='bold')

create_scatter(axs[0], fpsb_df, 'Value', 'Bid', 'understand2', 'Understanding', show_y_axis=True)
create_scatter(axs[1], fpsb_df, 'Value', 'Bid', 'risk2', 'Conservative/Aggressive', show_y_axis=False)
create_scatter(axs[2], fpsb_df, 'Value', 'Bid', 'strategy2', 'Strategy Dependency', show_y_axis=False)

plt.tight_layout(rect=[0, 0.01, 1, 0.99])

# Ensure the plot is displayed
plt.show()
