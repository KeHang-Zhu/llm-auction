import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load data
data = pd.read_csv('scaled_results.csv')


categories_name = ['Risk level', 'Dynamical\nStrategy', 'Interdependency', 'Learning']
categories = ['risk', 'dynamic', 'depend', 'learn']
levels_dict = {
    'risk': [0, 1, 2, 3, 4],
    'dynamic': [0, 1, 2, 3, 4],
    'depend': [0, 1, 2, 3, 4],
    'learn': [0, 1, 2, 3, 4]
}

fig, axes = plt.subplots(len(categories), 1, figsize=(10, 8), sharex=True)
colors = plt.cm.viridis(np.linspace(0, 1, 5))  # Using viridis from 0 to 4

for ax, category, name in zip(axes, categories, categories_name):
    counts = data[category].value_counts(normalize=True)
    counts = counts.reindex(levels_dict[category]).fillna(0)  # Ensure all levels are present
    bottom = np.zeros(1)  # Starting at 0 for stacking

    for level, color in zip(levels_dict[category], colors):
        value = counts[level]
        ax.barh(name, value, left=bottom, color=color, label=f'Level {level} ({value*100:.1f}%)')
        bottom += value  # Move the bottom up for the next bar segment

    # ax.set_title(f'{category.capitalize()} Distribution')
    ax.set_xlabel('Percentage')
    ax.legend(title='Levels', bbox_to_anchor=(1.05, 1), loc='upper left')

plt.tight_layout()
# plt.show()


## Plot the difference between First and Second Price

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load data
data = pd.read_csv('scaled_results.csv')

categories_name = ['Risk level', 'Dynamical\nStrategy', 'Interdependency', 'Learning']
categories = ['risk', 'dynamic', 'depend', 'learn']
levels = [0, 1, 2, 3, 4]

fig, axes = plt.subplots(2, 2, figsize=(10, 8))
axes = axes.flatten()

for ax, category, name in zip(axes, categories, categories_name):
    first_true = data[(data['Overbid'] == True) & (data['First'] == True)][category].value_counts(normalize=True).reindex(levels).fillna(0)
    first_false = data[(data['Overbid'] == False) & (data['First'] == True)][category].value_counts(normalize=True).reindex(levels).fillna(0)
    
    x = np.arange(len(levels))
    width = 0.35
    
    ax.bar(x - width/2, first_true, width, label='Overbid', color='skyblue')
    ax.bar(x + width/2, first_false, width, label='Not Overbid', color='lightgreen')
    
    ax.set_xlabel('Levels')
    ax.set_ylabel('Percentage')
    ax.set_title(f'{name}')
    ax.set_xticks(x)
    ax.set_xticklabels(levels)
    ax.legend()
    
    # Add percentage labels on top of each bar
    for i, v in enumerate(first_true):
        ax.text(i - width/2, v, f'{v:.1%}', ha='center', va='bottom')
    for i, v in enumerate(first_false):
        ax.text(i + width/2, v, f'{v:.1%}', ha='center', va='bottom')

plt.tight_layout()
plt.show()



