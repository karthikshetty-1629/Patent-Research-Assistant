import xml.etree.ElementTree as ET
import boto3
import botocore
import io
import logging
import re

# Configure logging
logging.basicConfig(level=logging.ERROR, filename='error.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')

def clean_malformed_xml(xml_content):
    # Remove common problematic characters that can make XML not well-formed
    xml_content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', xml_content)
    return xml_content

def parse_uspto_xml(xml_content):
    try:
        # Preprocess XML content to remove any junk data before or after the root element
        xml_content = re.sub(r'^.*?<\?xml', '<?xml', xml_content, flags=re.DOTALL)  # Remove any content before the first <?xml
        xml_content = re.sub(r'(</.*?>)\s*<\?xml.*$', '\1', xml_content, flags=re.DOTALL)  # Remove any content after the last root closing tag
        
        # Clean malformed XML content
        xml_content = clean_malformed_xml(xml_content)
        
        # Load and parse the XML content
        tree = ET.ElementTree(ET.fromstring(xml_content))
        root = tree.getroot()
        
        # Extract essential fields for the patent
        patent_data = {}
        patent_data['patent_id'] = root.find('.//doc-number').text if root.find('.//doc-number') is not None else None
        patent_data['filing_date'] = root.find('.//date-produced').text if root.find('.//date-produced') is not None else None
        patent_data['publication_date'] = root.find('.//date-publ').text if root.find('.//date-publ') is not None else None
        patent_data['title'] = root.find('.//invention-title').text if root.find('.//invention-title') is not None else None
        
        # Extract classifications
        classifications = []
        for classification in root.findall('.//classification-ipcr'):
            classifications.append(classification.find('main-classification').text if classification.find('main-classification') is not None else "")
        patent_data['classifications'] = classifications
        
        # Extract applicant details
        applicants = []
        for applicant in root.findall('.//us-applicant'):
            applicant_name = applicant.find('.//last-name').text if applicant.find('.//last-name') is not None else ""
            applicants.append(applicant_name)
        patent_data['applicants'] = applicants
        
        return patent_data
    except ET.ParseError as e:
        line, column = getattr(e, 'position', ('Unknown', 'Unknown'))
        logging.error(f"Error parsing XML: {e}. Line: {line}, Column: {column}")
        return None
    except re.error as e:
        logging.error(f"Regex error during XML preprocessing: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error while parsing XML: {e}")
        return None

def get_s3_file_content(bucket_name, s3_key):
    s3 = boto3.client('s3')
    try:
        response = s3.get_object(Bucket=bucket_name, Key=s3_key)
        return response['Body'].read().decode('utf-8')
    except botocore.exceptions.ClientError as e:
        logging.error(f"Error getting file from S3: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error while getting file from S3: {e}")
        return None

# Example usage
if __name__ == "__main__":
    s3_bucket_name = 'patent-research-assistant-mv'
    s3_key = 'uspto/fulltext-unzipped/2023/ipg231226/ipg231226.xml'
    
    xml_content = get_s3_file_content(s3_bucket_name, s3_key)
    if xml_content:
        # Handle cases where XML content may be empty or missing crucial data
        if xml_content.strip():
            patent_data = parse_uspto_xml(xml_content)
            if patent_data:
                print("Parsed Patent Data:")
                print(patent_data)
            else:
                print("Failed to parse patent XML content.")
        else:
            logging.error("Retrieved XML content is empty.")
            print("Failed to retrieve valid patent XML content from S3.")
    else:
        print("Failed to retrieve patent XML content from S3.")
