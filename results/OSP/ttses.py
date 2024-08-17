import pandas as pd
import numpy as np
from scipy import stats

# Load the data
df = pd.read_csv('OPS_all.csv')

# Calculate absolute difference between bid and value
df['abs_diff'] = abs(df['bid'] - df['value'])

# Prepare the three groups
group1 = df[(df['AC'] == True) & (df['Blind'] == False) & (df['winner'] == False)]['abs_diff']
group2 = df[(df['AC'] == True) & (df['Blind'] == True) & (df['winner'] == False)]['abs_diff']
group3 = df[(df['AC'] == False) & (df['Blind'] == True)]['abs_diff']

# Perform t-tests
t_stat1, p_value1 = stats.ttest_ind(group1, group2)
t_stat2, p_value2 = stats.ttest_ind(group1, group3)
t_stat3, p_value3 = stats.ttest_ind(group2, group3)

# Print results
print("T-test results:")
print("\n1. (Clock==True, Blind==False) vs (Clock==True, Blind==True)")
print(f"t-statistic: {t_stat1}")
print(f"p-value: {p_value1}")

print("\n2. (Clock==True, Blind==False) vs (Clock==False, Blind==True)")
print(f"t-statistic: {t_stat2}")
print(f"p-value: {p_value2}")

print("\n3. (Clock==True, Blind==True) vs (Clock==False, Blind==True)")
print(f"t-statistic: {t_stat3}")
print(f"p-value: {p_value3}")

# Calculate and print mean absolute differences for each group
print("\nMean absolute differences:")
print(f"(Clock==True, Blind==False): {group1.mean()}")
print(f"(Clock==True, Blind==True): {group2.mean()}")
print(f"(Clock==False, Blind==True): {group3.mean()}")