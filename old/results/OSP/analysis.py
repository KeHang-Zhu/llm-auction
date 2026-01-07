import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sb
import numpy as np
import statsmodels.api as sm

def create_scatter(ax, df, x_col, y_col, color_col, title, show_y_axis=True):
    # Create scatter plot
    colors = ['#FF9999', '#66B2FF']  # Light red for 0, Light blue for 1
    scatter_0 = ax.scatter(df[df[color_col] == 0][x_col], df[df[color_col] == 0][y_col], 
                           c=colors[0], marker='^', s=60, alpha=0.7)
    scatter_1 = ax.scatter(df[df[color_col] == 1][x_col], df[df[color_col] == 1][y_col], 
                           c=colors[1], marker='o', s=40, alpha=0.7)
    
    # Add NE line (y = 2/3 * x) in red
    x_vals = np.linspace(df[x_col].min(), df[x_col].max(), 100)
    NE_line = x_vals
    ax.plot(x_vals, NE_line, '-.', color='black', linewidth=3)
    
    # Add 45° line
    # ax.plot(x_vals, x_vals, '-.', color='black', linewidth=1)
    # ax.text(102, 100, '45° line', fontsize=10)
    
    # Add predicted bid text
    ax.text(x_vals[-1], NE_line[-10], 'Dominant\nStrategy', verticalalignment='bottom',
            horizontalalignment='left', color='red', fontweight='normal', fontsize=13,alpha=0.7)
    
    # Add LOWESS smoothed line
    # lowess = sm.nonparametric.lowess(df[y_col], df[x_col], frac=0.2)
    # ax.plot(lowess[:, 0], lowess[:, 1], '--', color='black', linewidth=3)
    # ax.text(127, 85, 'Smoothed\nData', verticalalignment='top', horizontalalignment='right',
    #         color='black', fontweight='normal', fontsize=11)
    
    # Set labels and title
    ax.set_xlabel("Assigned value for the good", size=13)
    if show_y_axis:
        ax.set_ylabel("LLM agent's bid", size=14)
    else:
        ax.set_ylabel("")
    ax.set_title(title, size=16)
    ax.set_xlim(10, 49)
    ax.set_ylim(10, 40)
    
    
    # Legend
    y_positions = [0.95, 0.9]
    triangle_size = 100
    square_size = 12
    legend_text_left = 'Non-winner'
    legend_text_right = 'Winner'
    
    # First row (left item)
    ax.scatter([0.25], [y_positions[0]], c=[colors[0]], marker='^', s=triangle_size, 
               transform=ax.transAxes)
    ax.text(0.28, y_positions[0], legend_text_left, transform=ax.transAxes, 
            ha='left', va='center', fontsize=10)
    # ax.text(0.23, y_positions[0], '▲', color=colors[0], transform=ax.transAxes, 
    #         ha='right', va='center', fontsize=square_size)
    
    # Second row (right item)
    ax.scatter([0.25], [y_positions[1]], c=[colors[1]], marker='o', s=triangle_size, 
               transform=ax.transAxes)
    ax.text(0.28, y_positions[1], legend_text_right, transform=ax.transAxes, 
            ha='left', va='center', fontsize=10)
    # ax.text(0.23, y_positions[1], '●', color=colors[1], transform=ax.transAxes, 
    #         ha='right', va='center', fontsize=square_size-1.5)

# Load the data
df = pd.read_csv('OPS_all.csv')

# Create the figure with three subplots
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5))

# Plot for AC=True, Blind=False
df_ac_true_blind_false = df[(df['AC'] == True) & (df['Blind'] == False)]
create_scatter(ax1, df_ac_true_blind_false, 'value', 'bid', 'winner', 'AC')

# Plot for AC=True, Blind=True
df_ac_true_blind_true = df[(df['AC'] == True) & (df['Blind'] == True)]
create_scatter(ax2, df_ac_true_blind_true, 'value', 'bid', 'winner', 'AC-B', show_y_axis=False)

# Plot for AC=False, Blind=True
df_ac_false_blind_true = df[(df['AC'] == False) & (df['Blind'] == True)]
create_scatter(ax3, df_ac_false_blind_true, 'value', 'bid', 'winner', 'SPSB', show_y_axis=False)

# Adjust layout and save the figure
plt.tight_layout()
plt.savefig('auction_scatter_plots.png', dpi=300, bbox_inches='tight')
plt.show()