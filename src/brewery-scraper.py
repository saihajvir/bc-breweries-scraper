import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import json

def scrape_all_breweries(limit=None):
    """
    Scrapes data for breweries from the BC Ale Trail website.
    
    Parameters:
    - limit (int, optional): Limit the number of breweries to scrape. If None, scrape all.
    
    Returns a pandas DataFrame with the extracted information.
    """
    # Base URL for the breweries page
    url = "https://bcaletrail.ca/breweries/"
    
    # Send a request to the website
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    print(f"Fetching breweries list from {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")
        return None
    
    # Parse the HTML content
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Find all brewery elements
    brewery_cards = soup.select(".listing-item")
    
    if not brewery_cards:
        print("No brewery cards found. The website structure may have changed.")
        return None
    
    # Limit the number of breweries to scrape if specified
    if limit and isinstance(limit, int) and limit > 0:
        brewery_cards = brewery_cards[:limit]
        print(f"Limiting scrape to {len(brewery_cards)} breweries")
    else:
        print(f"Found {len(brewery_cards)} breweries to scrape")
    
    # List to store all brewery data
    all_breweries = []
    
    # Process each brewery
    for i, brewery_card in enumerate(brewery_cards):
        try:
            brewery = {}
            
            # Extract brewery name
            name_element = brewery_card.select_one(".listing-title")
            brewery["name"] = name_element.text.strip() if name_element else "N/A"

            # Extract brewery city
            city_element = brewery_card.select_one(".location")
            brewery["city"] = city_element.text.strip() if city_element else "N/A"

            # Extract brewery type
            brewery_type_element = brewery_card.select_one(".features")
            if brewery_type_element:
                # Split features by the pipe character and strip each feature
                features_text = brewery_type_element.text.strip()
                features_list = [feature.strip() for feature in features_text.split("|")]
                brewery["brewery_type"] = filter_features(features_list)  # Apply filtering here
            else:
                brewery["brewery_type"] = []

            # Extract brewery URL
            link_element = brewery_card.select_one("a")
            brewery["url"] = link_element["href"] if link_element and "href" in link_element.attrs else "N/A"
            
            # Progress indicator
            print(f"\nProcessing brewery {i+1}/{len(brewery_cards)}: {brewery['name']}")
            
            # Additional data from brewery detail page
            if brewery["url"] != "N/A":
                print(f"Fetching detailed information from {brewery['url']}")
                detail_data = scrape_brewery_detail(brewery["url"])
                brewery.update(detail_data)
                
                # Add a delay to avoid overloading the server
                if i < len(brewery_cards) - 1:  # No need to delay after the last brewery
                    delay = random.uniform(1.0, 3.0)
                    print(f"Waiting {delay:.2f} seconds before next request...")
                    time.sleep(delay)
            
            all_breweries.append(brewery)
            
        except Exception as e:
            print(f"Error processing brewery: {str(e)}")
            continue  # Skip to the next brewery if there's an error
    
    if not all_breweries:
        print("No breweries were successfully scraped.")
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(all_breweries)
    
    print(f"\nSuccessfully scraped {len(all_breweries)} breweries")
    return df

def scrape_brewery_detail(url):
    """
    Scrapes detailed information from a brewery's specific page.
    """
    detail_info = {
        "address": "N/A",
        "postal_code": "N/A",
        "state_province": "N/A",
        "phone": "N/A",
        "website_url": "N/A",
        "social_media": "N/A"
    }
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Failed to retrieve detail page. Status code: {response.status_code}")
            return detail_info
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Extract address
        address_element = soup.select_one(".address a")
        if address_element:
            full_address = address_element.text.strip()
            address_parts = parse_address(full_address)
            detail_info.update(address_parts)
        
        # Extract phone
        phone_element = soup.select_one(".tel a")
        if phone_element:
            raw_phone = phone_element.text.strip()
            detail_info["phone"] = clean_phone_number(raw_phone)
        
        # Extract website
        website_element = soup.select_one(".listing-links a")
        if website_element and "href" in website_element.attrs:
            detail_info["website_url"] = website_element["href"]  # Fixed typo in field name
        
        # # Extract description
        # description_element = soup.select_one(".brewery-description")
        # if description_element:
        #     detail_info["description"] = description_element.text.strip()
        
        # Extract social media links
        social_media_elements = soup.select(".list-social-item a")
        if social_media_elements:
            social_links = [link["href"] for link in social_media_elements if "href" in link.attrs]
            detail_info["social_media"] = social_links
        
    except Exception as e:
        print(f"Error scraping detail page: {str(e)}")
    
    return detail_info

def parse_address(full_address):
    """
    Parse the full address string into components:
    - address (complete street address including unit/suite number)
    - postal_code (Canadian postal code)
    - province (BC)
    """
    address_components = {
        "address": "N/A",
        "postal_code": "N/A",
        "state_province": "N/A",
        "country": "N/A"
    }
    
    # Default province to BC since these are BC breweries
    address_components["state_province"] = "BC"
    address_components["country"] = "Canada"
    
    # Split the address by commas and clean each part
    parts = [part.strip() for part in full_address.split(",")]
    
    # If there's at least one part, it's the main address
    if parts:
        address_components["address"] = parts[0].strip()
    
    # Look for postal code in the last part (city, province postal_code)
    if len(parts) > 1:
        last_part = parts[-1]
        
        # Canadian postal codes are in format A1A 1A1
        import re
        postal_match = re.search(r'[A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d', last_part)
        if postal_match:
            address_components["postal_code"] = postal_match.group(0).strip()
    
    return address_components

def filter_features(features):
    """
    Filters the brewery type list to only include features that are in the allowed list.
    The allowed features are loaded from the 'features_to_keep.json' file.
    """
    # Load the list of allowed features from features_to_keep.json
    try:
        with open('features_to_keep.json', 'r', encoding='utf-8') as f:
            allowed_features = json.load(f)
    except Exception as e:
        print(f"Error loading features list: {e}")
        return []
    
    # Filter the features by checking if they are in the allowed list
    return [feature for feature in features if feature in allowed_features]

def clean_phone_number(phone):
    """
    Clean phone number by removing parentheses, dashes, spaces, and other non-numeric characters.
    """
    import re
    # Keep only digits
    return re.sub(r'[^0-9]', '', phone)

def save_data(df, file_type="csv"):
    """
    Saves the DataFrame to a file.
    Supported file types: csv, excel, json
    """
    if df is None or df.empty:
        print("No data to save")
        return
    
    filename = f"bc_breweries_complete.{file_type}"
    
    if file_type.lower() == "csv":
        df.to_csv(filename, index=False, encoding="utf-8")
    elif file_type.lower() == "excel":
        df.to_excel(filename, index=False)
    elif file_type.lower() == "json":
        # Use json module directly instead of pandas' to_json to avoid escape slashes
        import json
        
        # Convert DataFrame to a list of dictionaries
        records = df.to_dict(orient='records')
        
        # Write to file with ensure_ascii=False to properly handle non-ASCII characters
        # and without escaping forward slashes
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=4)
    else:
        print(f"Unsupported file type: {file_type}")
        return
    
    print(f"Data successfully saved to {filename}")

if __name__ == "__main__":
    print("Starting BC Ale Trail brewery scraper (test mode)...")
    
    # Scrape just 5 breweries as a test
    breweries_df = scrape_all_breweries(limit=None)
    
    if breweries_df is not None:
        # Display summary
        print("\nScraping summary:")
        print(f"Total breweries scraped: {len(breweries_df)}")
        print(f"Columns in dataset: {', '.join(breweries_df.columns)}")
        
        # Save data to files
        save_data(breweries_df, "json")
        save_data(breweries_df, "csv")
    
    print("Scraping completed")