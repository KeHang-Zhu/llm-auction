import pandas as pd
from openai import OpenAI
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt


# Load data
df = pd.read_csv("/Users/wonderland/Desktop/auction/llm-auction/results/Plan_reflection/auction_data_with_embeddings.csv")

## read the column_name of 0 to 3071
# Extract embeddings into a DataFrame
embedding_columns = [str(i) for i in range(3072)]  # Adjust the range if different number of embeddings
embedding_df = df[embedding_columns]

# Apply t-SNE
tsne = TSNE(n_components=2, random_state=38)
tsne_results = tsne.fit_transform(embedding_df)

# Create a new DataFrame for plotting
tsne_df = pd.DataFrame(tsne_results, columns=['TSNE1', 'TSNE2'])
tsne_df['Overbid'] = df['Overbid']
tsne_df['Underbid'] = df['Underbid']
tsne_df['First'] = df['First']

# Define labels based on 'Overbid', 'Underbid', and 'First'
tsne_df['Label'] = tsne_df.apply(lambda row: 'Overbid + First' if row['Overbid'] and row['First'] else (
    'Overbid + Second' if row['Overbid'] and not row['First'] else (
    'Underbid + First' if row['Underbid'] and row['First'] else 'Underbid + Second')), axis=1)

# Plotting
plt.figure(figsize=(10, 8))
for label, group in tsne_df.groupby('Label'):
    plt.scatter(group['TSNE1'], group['TSNE2'], label=label)

plt.legend()
plt.xlabel('TSNE1')
plt.ylabel('TSNE2')
plt.title('t-SNE of Auction Data Embeddings')
plt.show()

cluster_data = tsne_df[(tsne_df['TSNE1'] < -20) & (tsne_df['TSNE2'] < -1)]


print("Cluster Data (first 5 columns):")
print(df.loc[cluster_data.index, df.columns[:5]]) 

# cluster_df = df.loc[cluster_data.index, df.columns[:5]]
# cluster_df.to_csv("anomaly.csv", index=False) 


# cluster_indices = cluster_data.index
# normal_data = df.drop(index=cluster_indices).iloc[:, :5]  
# normal_data.to_csv("normal.csv", index=False)
