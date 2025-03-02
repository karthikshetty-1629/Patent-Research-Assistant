import pandas as pd

# Path to your Parquet file
parquet_file = "/Users/nithinkeshav/Downloads/xml_parquet_output/document_2.parquet"

# Read the Parquet file into a Pandas DataFrame
df = pd.read_parquet(parquet_file)

# Display the DataFrame
print(df.head())  # View the first 5 rows

print(df.columns)
