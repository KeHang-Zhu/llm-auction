import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error
import scipy.stats as stats

# Read the CSV file
df = pd.read_csv('binary_results.csv')

# Filter out rows where Value or Bid is 0
df = df[(df['Value'] != 0) & (df['Bid'] != 0)]

# Calculate percent deviation
df['percent_deviation'] = (df['Bid'] - df['Value']) / df['Value']

# Handle NaN values in strategy2
print(f"Number of NaN values in strategy2: {df['strategy2'].isna().sum()}")
df['strategy2'] = df['strategy2'].fillna(df['strategy2'].mean())  # Fill NaN with mean


# Function to perform regression and generate statistics
def perform_regression(X, y):
    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)
    
    # Calculate statistics
    n = len(y)
    k = X.shape[1]  # number of predictors
    r_squared = r2_score(y, y_pred)
    adj_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - k - 1)
    mse = mean_squared_error(y, y_pred)
    rmse = np.sqrt(mse)
    
    # Calculate standard errors and t-statistics
    residuals = y - y_pred
    degrees_of_freedom = n - k - 1
    s_squared = np.sum(residuals**2) / degrees_of_freedom
    var_covar_matrix = s_squared * np.linalg.inv(np.dot(X.T, X))
    se = np.sqrt(np.diagonal(var_covar_matrix))
    t_stats = model.coef_ / se
    
    # Calculate p-values
    p_values = [2 * (1 - stats.t.cdf(np.abs(t), degrees_of_freedom)) for t in t_stats]
    
    return {
        'coefficients': model.coef_,
        'intercept': model.intercept_,
        'r_squared': r_squared,
        'adj_r_squared': adj_r_squared,
        'mse': mse,
        'rmse': rmse,
        'standard_errors': se,
        't_statistics': t_stats,
        'p_values': p_values,
        'degrees_of_freedom': degrees_of_freedom
    }

# Perform regression for First == True
df_true = df[df['First'] == True]
X_true = df_true[['risk2']]
y_true = df_true['percent_deviation']
results_true = perform_regression(X_true, y_true)

# Perform regression for First == False
df_false = df[df['First'] == False]
X_false = df_false[['risk2']]
y_false = df_false['percent_deviation']
results_false = perform_regression(X_false, y_false)

# Print results
def print_results(results, condition):
    print(f"\nRegression Results for First == {condition}:")
    print(f"Intercept: {results['intercept']:.4f}")
    print(f"Coefficient (risk2): {results['coefficients'][0]:.4f}")
    print(f"R-squared: {results['r_squared']:.4f}")
    print(f"Adjusted R-squared: {results['adj_r_squared']:.4f}")
    print(f"Mean Squared Error: {results['mse']:.4f}")
    print(f"Root Mean Squared Error: {results['rmse']:.4f}")
    print(f"Standard Error (risk2): {results['standard_errors'][0]:.4f}")
    print(f"t-statistic (risk2): {results['t_statistics'][0]:.4f}")
    print(f"p-value (risk2): {results['p_values'][0]:.4f}")
    print(f"Degrees of Freedom: {results['degrees_of_freedom']}")

print_results(results_true, "True")
print_results(results_false, "False")

# Calculate percentages for risk2, separated by First
def calculate_percentages(column, first_value):
    subset = df[df['First'] == first_value]
    total = len(subset[column])
    zeros = (subset[column] == 0).sum()
    ones = (subset[column] == 1).sum()
    return {
        '0': (zeros / total) * 100,
        '1': (ones / total) * 100
    }

print("\nPercentages for risk2:")
print("First == True:")
risk2_true = calculate_percentages('risk2', True)
print(f"0 - {risk2_true['0']:.2f}%, 1 - {risk2_true['1']:.2f}%")
print("First == False:")
risk2_false = calculate_percentages('risk2', False)
print(f"0 - {risk2_false['0']:.2f}%, 1 - {risk2_false['1']:.2f}%")


