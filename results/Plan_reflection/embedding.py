import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt

load_dotenv()

# Load data
df = pd.read_csv("/Users/wonderland/Desktop/auction/llm-auction/results/Plan_reflection/fp_sp_auction_data.csv")

# Initialize OpenAI client
client = OpenAI()

# Assuming your DataFrame has a column 'Plan' that you want to encode
texts = df['Plan'].tolist(0)

# Generate embeddings
embeddings = []
for text in texts:
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-large"
    )
    embeddings.append(response.data[0].embedding)

# Convert list of embeddings into a DataFrame
embedding_df = pd.DataFrame(embeddings)

# # Integrate embeddings back into your main DataFrame
# df['Embedding'] = embedding_df.values.tolist()

# Integrate embeddings back into your main DataFrame
df = pd.concat([df, embedding_df], axis=1)

# Save the DataFrame with embeddings to a CSV file
csv_output_path = "auction_data_with_embeddings.csv"
df.to_csv(csv_output_path, index=False)


# # Apply t-SNE
# tsne = TSNE(n_components=2, random_state=42)
# tsne_results = tsne.fit_transform(embedding_df)

# # Create a new DataFrame for plotting
# tsne_df = pd.DataFrame(tsne_results, columns=['TSNE1', 'TSNE2'])
# tsne_df['Overbid'] = df['Overbid']
# tsne_df['Underbid'] = df['Underbid']
# tsne_df['First'] = df['First']  # Assuming 'First' indicates if the prediction was true or not

# # Plotting
# plt.figure(figsize=(12,10))
# scatter = plt.scatter(tsne_df['TSNE1'], tsne_df['TSNE2'], c=tsne_df['First'], cmap='viridis')
# plt.legend(handles=scatter.legend_elements()[0], labels=['False', 'True'])
# plt.xlabel('TSNE1')
# plt.ylabel('TSNE2')
# plt.title('t-SNE of Auction Bids')
# plt.show()


