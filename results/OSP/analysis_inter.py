import pandas as pd
import numpy as np
from scipy.stats import fisher_exact
from tabulate import tabulate

# Read the CSV file
df = pd.read_csv('ACB_intervention.csv')

# Define a function to check if bidding is truthful
def is_truthful(row, treatment):
    if row['Early']:
        return row[treatment] == 'No'
    else:
        return row[treatment] == 'Yes'

# Create a function to calculate p-value
def calculate_p_value(control, treatment):
    control_truthful = control.sum()
    control_not_truthful = len(control) - control_truthful
    
    treatment_truthful = treatment.sum()
    treatment_not_truthful = len(treatment) - treatment_truthful
    
    contingency_table = [
        [control_truthful, control_not_truthful],
        [treatment_truthful, treatment_not_truthful]
    ]
    
    _, p_value = fisher_exact(contingency_table)
    return p_value

# Calculate truthful bidding percentages and p-values for each group
control_group = df
control_truthful_percentage = (control_group['Early'] == False).mean() * 100


treatments = ['second', 'risk', 'info']
results = []

results.append(['Control', 'None', f"{control_truthful_percentage:.2f}%", 'N/A'])

for treatment in treatments:
    df[f'{treatment}_truthful'] = df.apply(lambda row: is_truthful(row, treatment), axis=1)
    treated_group = df
    treated_truthful_percentage = treated_group[f'{treatment}_truthful'].mean() * 100
    p_value = calculate_p_value(control_group['Early'] == False, df[f'{treatment}_truthful'])
    results.append(['Treatment', treatment.capitalize(), f"{treated_truthful_percentage:.2f}%", f"{p_value:.4f}"])

# Create and print the table
headers = ['Group', 'Treatment', 'Truthful Bidding %', 'p-value']
table = tabulate(results, headers=headers, tablefmt='pipe')

print(table)

print("\n*Note: p-values are calculated comparing each treatment group to the control group using Fisher's exact test.")
print("For the control group, truthful bidding is defined as 'second' == 'Yes' when Early == False.")
print("For treatment groups, truthful bidding is defined as treatment == 'Yes' when Early == False, and treatment == 'No' when Early == True.*")
print("- A p-value < 0.05 is typically considered statistically significant.")

# Print additional information
print("\nAdditional Information:")
print(f"Total number of observations: {len(df)}")
print(f"Number of control group observations (Early == False): {len(control_group)}")
for treatment in treatments:
    treated_group = df
    print(f"Number of {treatment.capitalize()} treatment observations: {len(treated_group)}")
    
    
    
    
import pandas as pd
import numpy as np
from scipy import stats

df = pd.read_csv("/Users/wonderland/Desktop/auction/llm-auction/results/OSP/2P_intervention.csv")

def calculate_truthful_ratio(col):
    return (df['value'] == df[col]).mean()

truthful_ratios = {
    'answer': calculate_truthful_ratio('answer'),
    'risk': calculate_truthful_ratio('risk'),
    'counter': calculate_truthful_ratio('counter'),
    'second': calculate_truthful_ratio('second')
}

print("Truthful ratios:")
for col, ratio in truthful_ratios.items():
    print(f"{col}: {ratio:.4f}")

#
df['bid_dev'] = df['value'] - df['answer']
df['risk_dev'] = df['value'] - df['risk']
df['counter_dev'] = df['value'] - df['counter']
df['second_dev'] = df['value'] - df['second']

avg_bid_dev = df['bid_dev'].mean()
avg_risk_dev = df['risk_dev'].mean()
avg_counter_dev = df['counter_dev'].mean()
avg_second_dev = df['second_dev'].mean()

print(f"Average bid deviation: {avg_bid_dev}")
print(f"Average risk deviation: {avg_risk_dev}")
print(f"Average counter deviation: {avg_counter_dev}")
print(f"Average second deviation: {avg_second_dev}")

def calculate_p_value(col):
    _, p_value = stats.ttest_rel(df['answer'], df[col])
    return p_value

p_values = {
    'risk': calculate_p_value('risk'),
    'counter': calculate_p_value('counter'),
    'second': calculate_p_value('second')
}

print("\np-values:")
for col, p_value in p_values.items():
    print(f"bid vs {col}: {p_value:.4f}")