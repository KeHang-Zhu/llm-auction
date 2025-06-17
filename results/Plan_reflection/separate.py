import pandas as pd

# Load the original data
data = pd.read_csv('scaled_results.csv')

# Filter the data for Overbid==True
overbid_data = data[data['Overbid'] == True]

# Save the filtered data to a new CSV file
overbid_data.to_csv('overbid.csv', index=False)

print(f"Overbid data has been saved to 'overbid.csv'")
print(f"Number of rows in overbid.csv: {len(overbid_data)}")