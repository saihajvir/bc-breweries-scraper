import requests
from bs4 import BeautifulSoup
import json
import time
import random
import pandas as pd

def extract_menu_url(detail_url):
    """
    Extracts only the menu URL from a brewery's detail page.
    """
    menu_url = "N/A"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(detail_url, headers=headers)
        
        if response.status_code != 200:
            print(f"Failed to retrieve detail page. Status code: {response.status_code}")
            return menu_url
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        section_header_links = soup.select('.section-header a')
        
        menu_element = None

        for link in section_header_links:
            if link.text and "View All Beers" in link.text:
                menu_element = link
                break
        if menu_element:
            menu_url = menu_element["href"]
            print(f"Found menu URL: {menu_url}")
        else:
            print("No menu URL found")

    except Exception as e:
        print(f"Error extracting menu URL: {str(e)}")
    
    return menu_url

def update_breweries_with_menu_urls():
    """
    Updates the existing brewery data with menu URLs only, matching by brewery name.
    """
    # Load existing data
    try:
        with open('bc_breweries_complete.json', 'r', encoding='utf-8') as f:
            breweries = json.load(f)
        print(f"Loaded {len(breweries)} breweries from existing file")
        
        # Create a dictionary with brewery names as keys for easy lookup
        brewery_dict = {brewery.get('name', ''): brewery for brewery in breweries}
        print(f"Created lookup dictionary with {len(brewery_dict)} breweries")
        
    except Exception as e:
        print(f"Error loading existing data: {str(e)}")
        return
    
    # Count how many breweries need updating
    to_update = [b for b in breweries if "menu_url" not in b]
    print(f"Need to update {len(to_update)} breweries with menu URLs")
    
    # Process each brewery to add menu_url
    updated_count = 0
    for i, brewery in enumerate(to_update):
        brewery_name = brewery.get('name', '')
        if not brewery_name:
            print(f"Warning: Brewery at index {i} has no name, skipping...")
            continue
            
        # Verify the brewery exists in our dictionary
        if brewery_name not in brewery_dict:
            print(f"Warning: Brewery '{brewery_name}' not found in dictionary, skipping...")
            continue
            
        # Get the brewery from the dictionary to ensure we're updating the right one
        target_brewery = brewery_dict[brewery_name]
        
        if "url" in target_brewery and target_brewery["url"] != "N/A":
            print(f"\nProcessing brewery {i+1}/{len(to_update)}: {brewery_name}")
            
            # Get detail page and extract menu URL
            print(f"Fetching menu URL from {target_brewery['url']}")
            menu_url = extract_menu_url(target_brewery["url"])
            
            # Add menu_url to brewery data
            target_brewery["menu_url"] = menu_url
            updated_count += 1
            
            # Add a delay to avoid overloading the server
            if i < len(to_update) - 1:  # No need to delay after the last brewery
                delay = random.uniform(1.0, 2.0)
                print(f"Waiting {delay:.2f} seconds before next request...")
                time.sleep(delay)
    
    print(f"\nUpdated {updated_count} breweries with menu URLs")
    
    # Save updated data
    try:
        filename = 'bc_breweries_complete_with_menus.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(breweries, f, ensure_ascii=False, indent=4)
        print(f"Data successfully saved to {filename}")
        
        # Also save as CSV
        df = pd.DataFrame(breweries)
        df.to_csv('bc_breweries_complete_with_menus.csv', index=False, encoding="utf-8")
        print(f"Data also saved to bc_breweries_complete_with_menus.csv")
    except Exception as e:
        print(f"Error saving updated data: {str(e)}")

if __name__ == "__main__":
    print("Starting menu URL update for BC breweries...")
    update_breweries_with_menu_urls()
    print("Update completed")