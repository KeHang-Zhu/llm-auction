import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy import stats

# Read the CSV file
df = pd.read_csv('combined_results.csv')

# Create bins for the Value column
df['ValueBin'] = pd.cut(df['Value'], bins=10)

# Calculate mean bid and standard error for each auction format
def calculate_stats(group):
    return pd.Series({
        'MeanBid': group['Bid'].mean(),
        'StdError': group['Bid'].sem()
    })

first_price = df[df['First'] == True].groupby('ValueBin').apply(calculate_stats).reset_index()
second_price = df[df['First'] == False].groupby('ValueBin').apply(calculate_stats).reset_index()

# Set up the plot style
plt.figure(figsize=(12, 8))
sns.set_style("whitegrid")

# Plot the two lines with error bars
plt.errorbar(first_price['ValueBin'].apply(lambda x: x.mid), first_price['MeanBid'], 
             yerr=first_price['StdError'], fmt='-o', label='First-Price Auction')
plt.errorbar(second_price['ValueBin'].apply(lambda x: x.mid), second_price['MeanBid'], 
             yerr=second_price['StdError'], fmt='-o', label='Second-Price Auction')

# Set chart title and labels with increased font size
plt.title("Comparison of Auction Formats: LLM Agent's Bid vs Assigned Value", fontsize=20)
plt.xlabel("LLM Agent's Assigned Value for the Good", fontsize=16)
plt.ylabel("LLM Agent's Bid", fontsize=16)
plt.legend(fontsize=14)

# Increase font size for tick labels
plt.xticks(fontsize=12)
plt.yticks(fontsize=12)

# Adjust layout and display the plot
plt.tight_layout()
plt.savefig('cross-format.png')

# Perform t-test to compare the two auction formats
t_stat, p_value = stats.ttest_ind(df[df['First'] == True]['Bid'], 
                                  df[df['First'] == False]['Bid'])

print(f"T-statistic: {t_stat}")
print(f"P-value: {p_value}")