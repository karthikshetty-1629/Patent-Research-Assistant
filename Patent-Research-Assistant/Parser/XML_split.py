import os

def split_concatenated_xml(concatenated_path, output_dir):
    """
    Split a concatenated XML file into multiple valid XML documents.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(concatenated_path, "r", encoding="utf-8") as file:
        content = file.read()

    # Split on XML declarations
    docs = content.split('<?xml version="1.0" encoding="UTF-8"?>')

    for i, doc in enumerate(docs):
        if doc.strip():  # Ignore empty splits
            doc_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + doc.strip()
            output_file = os.path.join(output_dir, f"document_{i + 1}.xml")
            with open(output_file, "w", encoding="utf-8") as out_file:
                out_file.write(doc_content)
            print(f"Saved: {output_file}")

# Paths
concatenated_path = "/Users/nithinkeshav/Downloads/ipg180102.xml"
output_dir = "/Users/nithinkeshav/Downloads/xml_split_output"

# Split the concatenated XML
split_concatenated_xml(concatenated_path, output_dir)
print("Splitting completed.")
