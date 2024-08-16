import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sb
import numpy as np
import statsmodels.api as sm

def create_scatter(ax, df, x_col, y_col, color_col, title, show_y_axis=True):
    # Create scatter plot
    colors = ['#FF9999', '#66B2FF']  # Light red for 0, Light blue for 1
    scatter_0 = ax.scatter(df[df[color_col] == 0][x_col], df[df[color_col] == 0][y_col], 
                           c=colors[0], marker='^', s=60, alpha=0.4)
    scatter_1 = ax.scatter(df[df[color_col] == 1][x_col], df[df[color_col] == 1][y_col], 
                           c=colors[1], marker='o', s=40, alpha=0.4)
    
    # Add NE line (y = 2/3 * x) in red
    x_vals = np.linspace(df[x_col].min(), df[x_col].max(), 100)
    NE_line = x_vals
    ax.plot(x_vals, NE_line, color='red', linewidth=3)
    
    # Add 45° line
    ax.plot(x_vals, x_vals, '-.', color='black', linewidth=1)
    ax.text(102, 100, '45° line', fontsize=10)
    
    # Add predicted bid text
    ax.text(x_vals[-15], NE_line[-30], 'Predicted bid', verticalalignment='bottom',
            horizontalalignment='left', color='red', fontweight='normal', fontsize=10)
    
    # Add LOWESS smoothed line
    lowess = sm.nonparametric.lowess(df[y_col], df[x_col], frac=0.2)
    ax.plot(lowess[:, 0], lowess[:, 1], '--', color='black', linewidth=3)
    ax.text(127, 85, 'Smoothed\nData', verticalalignment='top', horizontalalignment='right',
            color='black', fontweight='normal', fontsize=11)
    
    # Set labels and title
    ax.set_xlabel("Assigned value for the good", size=13)
    if show_y_axis:
        ax.set_ylabel("LLM agent's bid", size=14)
    else:
        ax.set_ylabel("")
    ax.set_title(title, size=16)
    ax.set_xlim(0, 47)
    ax.set_ylim(0, 47)

# Load the data
df = pd.read_csv('OPS_all.csv')

# Create the figure with three subplots
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 6))

# Plot for AC=True, Blind=False
df_ac_true_blind_false = df[(df['AC'] == True) & (df['Blind'] == False)]
create_scatter(ax1, df_ac_true_blind_false, 'value', 'bid', 'winner', 'AC=True, Blind=False')

# Plot for AC=True, Blind=True
df_ac_true_blind_true = df[(df['AC'] == True) & (df['Blind'] == True)]
create_scatter(ax2, df_ac_true_blind_true, 'value', 'bid', 'winner', 'AC=True, Blind=True', show_y_axis=False)

# Plot for AC=False, Blind=True
df_ac_false_blind_true = df[(df['AC'] == False) & (df['Blind'] == True)]
create_scatter(ax3, df_ac_false_blind_true, 'value', 'bid', 'winner', 'AC=False, Blind=True', show_y_axis=False)

# Adjust layout and save the figure
plt.tight_layout()
plt.savefig('auction_scatter_plots.png', dpi=300, bbox_inches='tight')
plt.show()