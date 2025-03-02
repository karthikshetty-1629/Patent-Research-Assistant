import boto3
import xml.etree.ElementTree as ET
from io import BytesIO
import re

def parse_multiple_patents(bucket: str, key: str, max_patents: int = 5):
    """Parse multiple patents from a single XML file"""
    try:
        print(f"Accessing file from s3://{bucket}/{key}")
        
        # Get file from S3
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        
        # Split content into individual patent documents
        # Pattern matches from <?xml to </us-patent-grant>
        patent_pattern = r'(<\?xml[^>]+\?>.*?</us-patent-grant>)'
        patents = re.findall(patent_pattern, content, re.DOTALL)
        
        print(f"\nFound {len(patents)} patents in the file")
        print(f"Showing details for first {max_patents} patents:\n")
        
        # Process each patent
        for i, patent_xml in enumerate(patents[:max_patents], 1):
            print(f"\n=== Patent {i} ===")
            try:
                # Parse individual patent
                root = ET.fromstring(patent_xml)
                
                # Extract basic patent information
                doc_number = root.find('.//doc-number').text
                date = root.find('.//date').text
                kind = root.find('.//kind').text
                
                print(f"Document Number: {doc_number}")
                print(f"Date: {date}")
                print(f"Kind: {kind}")
                
                # Extract title if present
                title = root.find('.//invention-title')
                if title is not None:
                    print(f"Title: {title.text}")
                
                # Extract inventors if present
                inventors = root.findall('.//inventor')
                if inventors:
                    print("\nInventors:")
                    for inventor in inventors:
                        first_name = inventor.find('.//first-name')
                        last_name = inventor.find('.//last-name')
                        if first_name is not None and last_name is not None:
                            print(f"- {first_name.text} {last_name.text}")
                
                # Extract abstract if present
                abstract = root.find('.//abstract')
                if abstract is not None:
                    abstract_text = ' '.join(abstract.itertext()).strip()
                    print(f"\nAbstract: {abstract_text[:200]}...")
                
                print("\n" + "-"*50)
                
            except ET.ParseError as e:
                print(f"Error parsing patent {i}: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Error: {str(e)}")

# Usage
bucket = "patent-research-assistant-mv"
key = "uspto/fulltext-unzipped/2023/ipg231226/ipg231226.xml"
parse_multiple_patents(bucket, key)
