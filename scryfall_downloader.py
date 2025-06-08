import os
import sys
import time
import json
import urllib.request
import urllib.error
import math
import re
from urllib.parse import quote, urlparse

def get_script_dir():
    if getattr(sys, 'frozen', False):  # Running as compiled executable
        return os.path.dirname(sys.executable)
    else:  # Running as standard Python script
        return os.path.dirname(os.path.abspath(__file__))
    
def sanitize_filename(name):
    # Convert to ASCII-safe filename with reasonable character limits
    clean = name.encode('ascii', 'ignore').decode('ascii')
    for c in ':/\\|?*"<>':
        clean = clean.replace(c, '_')
    clean = '_'.join(filter(None, clean.split('_')))
    return clean[:180]

def get_extension(url):
    # Extract file extension from URL
    return url.split('.')[-1].split('?')[0].lower()

def download_image(url, filepath, border_type=None):
    # Download an image with error handling
    # Optionally add different types of borders
    try:
        with urllib.request.urlopen(url) as response:
            if response.status == 200:
                img_data = response.read()
                
                # Save original image
                with open(filepath, 'wb') as f:
                    f.write(img_data)
                
                # Add border if requested
                if border_type and border_type != "none":
                    try:
                        from PIL import Image, ImageOps
                        import io
                        
                        # Open image from memory
                        img = Image.open(io.BytesIO(img_data))
                        width, height = img.size
                        
                        # Calculate DPI based on standard Magic card size (2.5 x 3.5 inches)
                        dpi_x = width / 2.5
                        dpi_y = height / 3.5
                        dpi = (dpi_x + dpi_y) / 2
                        
                        # Calculate border width in pixels (1/8 inch)
                        border_width = math.ceil(dpi / 8)
                        
                        # Handle different border types
                        if border_type == "colorless":
                            # Convert to RGBA if not already
                            if img.mode != 'RGBA':
                                img = img.convert('RGBA')
                            
                            # Create new transparent image with border space
                            new_width = width + 2 * border_width
                            new_height = height + 2 * border_width
                            new_img = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
                            
                            # Paste original in center
                            new_img.paste(img, (border_width, border_width))
                            
                            bordered_img = new_img
                            border_desc = "transparent"
                        elif border_type in ["black", "white"]:
                            # For black/white borders, replace any existing transparency with border color
                            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                                # Create new background with border color
                                border_color = (0, 0, 0) if border_type == "black" else (255, 255, 255)
                                background = Image.new('RGB', img.size, border_color)
                                
                                # Convert to RGBA if needed
                                if img.mode != 'RGBA':
                                    img = img.convert('RGBA')
                                
                                # Paste image onto background using alpha channel as mask
                                background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                                img = background
                            
                            # Add border expansion
                            border_color = (0, 0, 0) if border_type == "black" else (255, 255, 255)
                            bordered_img = ImageOps.expand(
                                img, 
                                border=border_width, 
                                fill=border_color
                            )
                            border_desc = f"solid {border_type}"
                        
                        # Preserve original format if possible
                        original_format = img.format
                        
                        # Save with border
                        bordered_img.save(filepath, format=original_format if original_format != 'GIF' else 'PNG')
                        print(f"  Added {border_width}px {border_desc} border")
                        return True
                    except ImportError:
                        print("  Pillow library not installed. Borders require Pillow.")
                        print("  Install with: pip install Pillow")
                        print("  Saving without border")
                        return True
                    except Exception as e:
                        print(f"  Error adding border: {e}")
                        print("  Saving without border")
                        return True
                return True
            else:
                print(f"  HTTP Error {response.status}: {url}")
                return False
    except urllib.error.URLError as e:
        print(f"  URL Error: {str(e)}")
    except Exception as e:
        print(f"  Error downloading {filepath}: {str(e)}")
    return False

def get_all_cards(set_code):
    # Retrieve all cards for a given set with pagination handling
    cards = []
    url = f"https://api.scryfall.com/cards/search?order=set&q=e%3A{quote(set_code)}&unique=prints"
    
    while url:
        try:
            with urllib.request.urlopen(url) as response:
                if response.status != 200:
                    print(f"API Error: HTTP {response.status}")
                    break
                    
                data = json.loads(response.read().decode('utf-8'))
                cards.extend(data['data'])
                
                if data['has_more']:
                    url = data['next_page']
                    time.sleep(0.1)
                else:
                    url = None
        except urllib.error.URLError as e:
            print(f"API Connection Error: {str(e)}")
            break
        except json.JSONDecodeError as e:
            print(f"JSON Parsing Error: {str(e)}")
            break
    
    return cards

def get_card_from_url(card_url):
    # Retrieve card data from a Scryfall URL
    try:
        # Extract card ID from URL
        parsed = urlparse(card_url)
        path_parts = parsed.path.split('/')
        
        # Pattern 1: /cards/:set/:number/:name
        # Pattern 2: /card/:set/:number/:id/:name
        if len(path_parts) >= 4 and path_parts[1] in ['card', 'cards']:
            set_code = path_parts[2]
            collector_number = path_parts[3]
            
            # Handle URLs with language codes
            if re.match(r'^[a-z]{2}$', collector_number) and len(path_parts) > 4:
                collector_number = path_parts[4]
            
            # Get card from Scryfall API
            api_url = f"https://api.scryfall.com/cards/{set_code}/{collector_number}"
            with urllib.request.urlopen(api_url) as response:
                if response.status == 200:
                    card_data = json.loads(response.read().decode('utf-8'))
                    return [card_data]
                else:
                    print(f"API Error: HTTP {response.status} for {api_url}")
        else:
            print("Invalid Scryfall URL format")
    except Exception as e:
        print(f"Error retrieving card from URL: {str(e)}")
    
    return None

def get_display_name(card_data, face_data=None):
    # Get the best display name for a card, prioritizing alternate art names
    if face_data:
        if 'flavor_name' in face_data and face_data['flavor_name']:
            return face_data['flavor_name']
        if 'printed_name' in face_data and face_data['printed_name']:
            return face_data['printed_name']
        if 'name' in face_data and face_data['name']:
            return face_data['name']
    
    if 'flavor_name' in card_data and card_data['flavor_name']:
        return card_data['flavor_name']
    if 'printed_name' in card_data and card_data['printed_name']:
        return card_data['printed_name']
    
    return card_data.get('name', 'Unnamed Card')

def main():
    # User inputs
    print("Download options:")
    print("1. Download an entire set")
    print("2. Download a single card from URL")
    choice = input("Select download option (1 or 2): ").strip()
    
    cards = []
    set_code = "singles"
    
    if choice == "1":
        # Set download mode
        set_code = input("Enter set code (e.g., 'FCA', 'FIC'): ").strip().lower()
        cards = get_all_cards(set_code)
        
    elif choice == "2":
        # Single card download mode
        card_url = input("Enter Scryfall card URL: ").strip()
        cards = get_card_from_url(card_url)
        if cards:
            set_code = cards[0].get('set', 'singles')
        else:
            print("Failed to retrieve card from URL")
            return
    else:
        print("Invalid choice")
        return
    
    if not cards:
        print("No cards found.")
        return
    
    print("\nAvailable image sizes:")
    sizes = ['small', 'normal', 'large', 'png', 'art_crop', 'border_crop']
    for i, size in enumerate(sizes, 1):
        print(f"{i}. {size}")
    
    try:
        size_choice = int(input("\nSelect image size (1-6): ").strip())
        if 1 <= size_choice <= 6:
            image_size = sizes[size_choice - 1]
        else:
            print("Invalid selection. Using 'normal'.")
            image_size = 'normal'
    except ValueError:
        print("Invalid input. Using 'normal'.")
        image_size = 'normal'
    
    # Border options
    print("\nBorder options:")
    print("1. No border")
    print("2. Solid black border")
    print("3. Solid white border")
    print("4. Colorless border (transparent)")
    
    border_choice = input("Select border option (1-4): ").strip()
    border_type = None
    
    if border_choice == "1":
        print("No border will be added")
    elif border_choice == "2":
        border_type = "black"
        print("Adding solid black bleed border")
    elif border_choice == "3":
        border_type = "white"
        print("Adding solid white bleed border")
    elif border_choice == "4":
        border_type = "colorless"
        print("Adding transparent colorless border")
    else:
        print("Invalid selection. No border will be added")
    
    # Create output directory relative to script location
    script_dir = get_script_dir()
    if choice == "1":
        output_dir = os.path.join(script_dir, f"scryfall_{set_code}")
    else:
        output_dir = os.path.join(script_dir, "scryfall_singles")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nFound {len(cards)} cards. Downloading images to:\n{output_dir}\n")
    
    # Download images
    total_downloaded = 0
    for i, card in enumerate(cards):
        collector_number = card.get('collector_number', '')
        card_id = card.get('id', '')[:8]
        
        primary_name = card.get('name', f"card_{i+1}")
        print(f"\nProcessing {i+1}/{len(cards)}: {primary_name}")
        
        # Handle double-faced cards
        if 'card_faces' in card:
            for face_index, face in enumerate(card['card_faces']):
                if 'image_uris' in face and image_size in face['image_uris']:
                    img_url = face['image_uris'][image_size]
                    ext = get_extension(img_url)
                    
                    display_name = get_display_name(card, face)
                    face_type = "front" if face_index == 0 else "back"
                    
                    base_name = f"{collector_number}_{sanitize_filename(display_name)}_{face_type}_{card_id}"
                    filename = f"{base_name}.{ext}"
                    filepath = os.path.join(output_dir, filename)
                    
                    if download_image(img_url, filepath, border_type):
                        print(f"  Downloaded: {filename}")
                        total_downloaded += 1
        # Handle single-faced cards
        elif 'image_uris' in card and image_size in card['image_uris']:
            img_url = card['image_uris'][image_size]
            ext = get_extension(img_url)
            
            display_name = get_display_name(card)
            
            base_name = f"{collector_number}_{sanitize_filename(display_name)}_{card_id}"
            filename = f"{base_name}.{ext}"
            filepath = os.path.join(output_dir, filename)
            
            if download_image(img_url, filepath, border_type):
                print(f"  Downloaded: {filename}")
                total_downloaded += 1
        
        # Respect API rate limits
        if i < len(cards) - 1:
            time.sleep(0.1)
    
    print(f"\nDownload complete! {total_downloaded} images saved to '{output_dir}'")

if __name__ == "__main__":
    main()