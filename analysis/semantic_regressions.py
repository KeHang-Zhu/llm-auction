import pandas as pd
import numpy as np
import statsmodels.api as sm

# Load the data
binary_results = pd.read_csv('binary_results.csv')
print(f"Original DataFrame shape: {binary_results.shape}")

# Filter for First Price Sealed Bid auction data and create a copy
fpsb_df = binary_results[binary_results['First'] == 1].copy()
print(f"Shape after filtering for First Price Sealed Bid: {fpsb_df.shape}")

# Check for any zero or negative values in 'Value' column
zero_or_negative_values = fpsb_df[fpsb_df['Value'] <= 0]
if not zero_or_negative_values.empty:
    print("\nWarning: Zero or negative values found in 'Value' column:")
    print(zero_or_negative_values)
    fpsb_df = fpsb_df[fpsb_df['Value'] > 0]
    print(f"Shape after removing zero/negative values: {fpsb_df.shape}")

# Calculate percent bid deviation
fpsb_df['percent_bid_deviation'] = (fpsb_df['Bid'] - fpsb_df['Value']) / fpsb_df['Value']

# Check for infinite or NaN values
infinite_or_nan = fpsb_df[np.isinf(fpsb_df['percent_bid_deviation']) | np.isnan(fpsb_df['percent_bid_deviation'])]
if not infinite_or_nan.empty:
    print("\nWarning: Infinite or NaN values found in percent_bid_deviation:")
    print(infinite_or_nan)
    fpsb_df = fpsb_df[~np.isinf(fpsb_df['percent_bid_deviation']) & ~np.isnan(fpsb_df['percent_bid_deviation'])]
    print(f"Shape after removing inf/nan values: {fpsb_df.shape}")

print("\nFinal DataFrame shape:", fpsb_df.shape)
print("\nColumns in the final DataFrame:", fpsb_df.columns.tolist())

# Print data info
print("\nData Info:")
print(fpsb_df.info())
print("\nDescriptive Statistics:")
print(fpsb_df.describe())

# Prepare the data for regression
X = sm.add_constant(fpsb_df['risk2'])
y = fpsb_df['percent_bid_deviation']

# Fit the regression model
model = sm.OLS(y, X).fit()

# Print the regression results
print("\nRegression Results:")
print(model.summary())
