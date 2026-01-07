# average overbid/ underbid, 

# First/ Second

# first 5 round/ mid 5 round /last 5 rounds. 
# 'Overbid_deviation': If overbid==True, deviation= bid - value
# 'underbid_deviation':If underbid==True, deviation= bid - value
# 'group_count': if overbid==True, overbid ++1, if underbid==True, underbid ++1
# 'Type': ['First-Price', 'First-Price', 'First-Price', 'Second-Price', 'Second-Price','Second-Price']
# 'round_number':[0, 5, 10, 0, 5, 10]

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Read the CSV file
df = pd.read_csv('/Users/wonderland/Desktop/auction/llm-auction/results/Plan_reflection/fp_sp_auction_data.csv')

# Process the data
def process_data(group):
    overbid_count = group['Overbid'].sum()
    underbid_count = group['Underbid'].sum()
    total_count = len(group)
    
    overbid_deviation = group[group['Overbid']]['Bid'] - group[group['Overbid']]['Value']
    underbid_deviation = group[group['Underbid']]['Bid'] - group[group['Underbid']]['Value']
    
    return pd.Series({
        'Overbid_count': overbid_count,
        'Underbid_count': underbid_count,
        'Total_count': total_count,
        'Overbid_deviation_mean': overbid_deviation.mean(),
        'Underbid_deviation_mean': underbid_deviation.mean()
        # Remove 'First' from here as it's already in the groupby keys
    })

# Group by Round and apply processing
df['Round_group'] = df['Round'] // 5
processed_data = df.groupby(['Round_group', 'Player Name', 'First']).apply(process_data).reset_index()

# Separate First-Price and Second-Price data
first_price_data = processed_data[processed_data['First']]
second_price_data = processed_data[~processed_data['First']]

print(df['First'].value_counts())
print(processed_data.groupby(['Round_group', 'First']).size().unstack(fill_value=0))


import pandas as pd
import matplotlib.pyplot as plt

# Assuming processed_data is already created as in the previous code

# Further aggregate the data
def aggregate_data(group):
    return pd.Series({
        'Overbid_count': group['Overbid_count'].sum(),
        'Underbid_count': group['Underbid_count'].sum(),
        'Overbid_deviation_mean': (group['Overbid_deviation_mean'] * group['Overbid_count']).sum() / group['Overbid_count'].sum(),
        'Underbid_deviation_mean': (group['Underbid_deviation_mean'] * group['Underbid_count']).sum() / group['Underbid_count'].sum()
    })

aggregated_data = processed_data.groupby(['Round_group', 'First']).apply(aggregate_data).reset_index()

# Separate First-Price and Second-Price data
first_price_data = aggregated_data[aggregated_data['First']]
second_price_data = aggregated_data[~aggregated_data['First']]

plt.figure(figsize=(12, 8))
plt.grid(True, linestyle='--', alpha=0.7)

# Plot First-Price data
for _, row in first_price_data.iterrows():
    plt.scatter(row['Round_group'], row['Overbid_deviation_mean'], 
                s=row['Overbid_count']*20, color='blue', alpha=0.7)
    plt.scatter(row['Round_group'], row['Underbid_deviation_mean'], 
                s=row['Underbid_count']*20, color='orange', alpha=0.7)
    plt.plot([row['Round_group'], row['Round_group']], 
             [row['Overbid_deviation_mean'], row['Underbid_deviation_mean']], 
             color='grey', linewidth=1, alpha=0.5)

# Plot Second-Price data
for _, row in second_price_data.iterrows():
    plt.scatter(row['Round_group'] + 0.1, row['Overbid_deviation_mean'], 
                s=row['Overbid_count']*20, color='green', alpha=0.7)
    plt.scatter(row['Round_group'] + 0.1, row['Underbid_deviation_mean'], 
                s=row['Underbid_count']*20, color='red', alpha=0.7)
    plt.plot([row['Round_group'] + 0.1, row['Round_group'] + 0.1], 
             [row['Overbid_deviation_mean'], row['Underbid_deviation_mean']], 
             color='grey', linewidth=1, alpha=0.5)

# Customize the plot
plt.title('Bid Deviation vs Round Group', fontsize=16)
plt.xlabel('Round Group', fontsize=12)
plt.ylabel('Bid Deviation', fontsize=12)
plt.xticks([0, 1, 2], ['0-4', '5-9', '10-14'])
plt.xlim(-0.5, 2.5)

# Create custom legend
plt.scatter([], [], c='blue', s=100, label='First-Price Overbid')
plt.scatter([], [], c='orange', s=100, label='First-Price Underbid')
plt.scatter([], [], c='green', s=100, label='Second-Price Overbid')
plt.scatter([], [], c='red', s=100, label='Second-Price Underbid')
plt.scatter([], [], c='gray', s=60, label='Count: 3')
plt.scatter([], [], c='gray', s=100, label='Count: 5')
plt.scatter([], [], c='gray', s=140, label='Count: 7')

# Create custom legend
legend_elements = [
    plt.scatter([], [], c='blue', s=100, label='First-Price Overbid'),
    plt.scatter([], [], c='orange', s=100, label='First-Price Underbid'),
    plt.scatter([], [], c='green', s=100, label='Second-Price Overbid'),
    plt.scatter([], [], c='red', s=100, label='Second-Price Underbid'),
    plt.scatter([], [], c='gray', s=60, label='Count: 3'),
    plt.scatter([], [], c='gray', s=100, label='Count: 5'),
    plt.scatter([], [], c='gray', s=140, label='Count: 7')
]
plt.legend(handles=legend_elements, 
           title='Bid Type', 
           title_fontsize='12', 
           fontsize='10', 
           loc='center left', 
           bbox_to_anchor=(1, 0.5))

plt.tight_layout()
plt.show()