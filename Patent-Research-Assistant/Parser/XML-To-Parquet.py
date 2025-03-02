import os
import pandas as pd
import xmltodict
import logging
from pandas import json_normalize

# Configure logging
log_file = "/Users/nithinkeshav/Downloads/parquet_conversion.log"
logging.basicConfig(
    filename=log_file,
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Input and output directories
xml_directory = "/Users/nithinkeshav/Downloads/xml_split_output"
parquet_output_dir = "/Users/nithinkeshav/Downloads/xml_parquet_output"

# Create output directory if it doesn't exist
os.makedirs(parquet_output_dir, exist_ok=True)

# Function to parse XML into a flattened dictionary
def parse_xml_to_dict(xml_file):
    with open(xml_file, "r", encoding="utf-8") as file:
        try:
            xml_data = xmltodict.parse(file.read())
            return xml_data
        except Exception as e:
            logging.error(f"Error parsing {xml_file}: {e}")
            return None

# Function to normalize and save to Parquet
def save_to_parquet(data, output_file):
    try:
        # Flatten the dictionary into a DataFrame
        df = pd.json_normalize(data)
        df.to_parquet(output_file, engine="pyarrow", index=False)
        print(f"Saved: {output_file}")
    except Exception as e:
        logging.error(f"Error saving {output_file} to Parquet: {e}")

# Process all XML files in the directory
for file in os.listdir(xml_directory):
    if file.endswith(".xml"):
        file_path = os.path.join(xml_directory, file)
        parsed_data = parse_xml_to_dict(file_path)
        if parsed_data:
            # Save each XML file to a separate Parquet file
            parquet_file = os.path.join(parquet_output_dir, f"{os.path.splitext(file)[0]}.parquet")
            save_to_parquet(parsed_data, parquet_file)

print(f"Conversion completed. Check the log file for errors: {log_file}")
