import os
import xml.etree.ElementTree as ET

output_dir = "/Users/nithinkeshav/Downloads/xml_split_output"

for file in os.listdir(output_dir):
    file_path = os.path.join(output_dir, file)
    try:
        # Parse and validate XML
        tree = ET.parse(file_path)
        root = tree.getroot()
        print(f"{file} is valid. Root tag: {root.tag}")
    except ET.ParseError as e:
        print(f"Error in {file}: {e}")
