import os
import sys
import requests
import time
import re
import tkinter
from tkinter import filedialog
from PIL import Image, ImageOps
from io import BytesIO
from urllib.parse import quote_plus
import traceback  # <<< ADDED: To print detailed error information

# Base URL for APIs
SCRYFALL_API_BASE_URL = "https://api.scryfall.com"

# Delay between API requests in seconds to respect Scryfall's rate limit (100ms)
REQUEST_DELAY = 0.1

# --- Constants for Physical Dimensions ---
CARD_WIDTH_INCHES = 2.5
CARD_HEIGHT_INCHES = 3.5
BORDER_INCHES = 0.125

def sanitize_filename(name):
    """Removes characters that are invalid for file names."""
    name = name.replace('//', '-')
    return re.sub(r'[\\/*?:"<>|]', "", name)

def add_border(image, border_size, color_choice):
    """Adds a border to a given Pillow image object."""
    if color_choice == 'transparent':
        color = (0, 0, 0, 0)
    elif color_choice == 'white':
        color = (255, 255, 255)
    else:  # black
        color = (0, 0, 0)

    return ImageOps.expand(image, border=border_size, fill=color)

def get_card_data_from_url(card_url):
    """Extracts set code and card number from a Scryfall web URL and fetches card data."""
    match = re.search(r'scryfall.com/card/([^/]+)/([^/]+)', card_url)
    if not match:
        print("  Invalid Scryfall card URL format.")
        return None
    set_code, collector_number = match.groups()
    api_url = f"{SCRYFALL_API_BASE_URL}/cards/{set_code}/{collector_number}"
    try:
        print(f"Fetching card data from: {api_url}")
        time.sleep(REQUEST_DELAY)
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching card data: {e}")
        return None

def process_card(card_data, image_size, download_dir, add_border_flag, border_color):
    """Processes a single card's JSON data to download its image(s)."""
    if not card_data:
        return

    image_format = 'png' if image_size == 'png' or border_color == 'transparent' else 'jpg'
    
    layout = card_data.get('layout', 'normal')
    card_name = sanitize_filename(card_data.get('name', 'UnknownCard'))
    set_code = card_data.get('set', 'unknown')
    collector_number = card_data.get('collector_number', '0')
    flavor_name = sanitize_filename(card_data.get('flavor_name', ''))

    print(f"\nProcessing card: {card_name} ({set_code.upper()} #{collector_number})")

    def download_and_save(url, file_path, is_standard_size):
        """Nested helper to download, process, and save an image."""
        try:
            response = requests.get(url)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))

            if add_border_flag:
                if is_standard_size:
                    pixel_width, _ = img.size
                    effective_dpi = pixel_width / CARD_WIDTH_INCHES
                    border_pixels = round(effective_dpi * BORDER_INCHES)
                    img = add_border(img, border_pixels, border_color)
                    print(f"    Applied {border_pixels}px border based on calculated DPI.")

            if image_format == 'jpg' and img.mode == 'RGBA':
                img = img.convert('RGB')
            
            img.save(file_path)
            print(f"  Successfully downloaded and saved: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"  An error occurred processing {card_name}: {e}")

    standard_sizes = ['small', 'normal', 'large', 'png', 'art_crop', 'border_crop']
    is_standard_size = image_size in standard_sizes

    single_image_layouts = [
        'normal', 'split', 'flip', 'leveler', 'class', 'case', 'saga',
        'adventure', 'mutate', 'prototype', 'planar', 'scheme', 'vanguard',
        'token', 'emblem', 'augment', 'host'
    ]
    double_image_layouts = [
        'transform', 'modal_dfc', 'double_faced_token', 'art_series', 'reversible_card'
    ]

    if layout in single_image_layouts:
        if 'image_uris' in card_data and image_size in card_data['image_uris']:
            image_url = card_data['image_uris'][image_size]
            base_name = f"{set_code}-{collector_number}-{flavor_name}-{card_name}" if flavor_name else f"{set_code}-{collector_number}-{card_name}"
            file_name = f"{base_name}.{image_format}"
            file_path = os.path.join(download_dir, file_name)
            download_and_save(image_url, file_path, is_standard_size)
        else:
            print(f"  Could not find image URI for size '{image_size}' for {card_name}.")

    elif layout in double_image_layouts:
        if 'card_faces' in card_data:
            for i, face in enumerate(card_data['card_faces']):
                if 'image_uris' in face and image_size in face['image_uris']:
                    face_name = sanitize_filename(face.get('name', f"face{i+1}"))
                    image_url = face['image_uris'][image_size]
                    file_name = f"{set_code}-{collector_number}-{face_name}.{image_format}"
                    file_path = os.path.join(download_dir, file_name)
                    download_and_save(image_url, file_path, is_standard_size)
                else:
                    print(f"  Could not find image URI for size '{image_size}' for face {i+1} of {card_name}.")
        else:
            print(f"  Layout is '{layout}' but no 'card_faces' data found for {card_name}.")

    elif layout == 'meld':
        if 'all_parts' in card_data:
            print(f"  Processing meld card. It has {len(card_data['all_parts'])} parts.")
            for part in card_data['all_parts']:
                component_type = part.get('component')
                part_name = sanitize_filename(part.get('name', 'UnknownPart'))
                if component_type in ['meld_part', 'meld_result']:
                    part_data = None
                    try:
                        api_uri = part['uri']
                        time.sleep(REQUEST_DELAY)
                        response = requests.get(api_uri)
                        response.raise_for_status()
                        part_data = response.json()
                    except requests.exceptions.RequestException as e:
                        print(f"    Error fetching meld part data for {part_name}: {e}")
                        continue

                    if not part_data:
                        print(f"    Could not get data for meld part: {part_name}")
                        continue

                    part_set = part_data.get('set', 'unknown')
                    part_number = part_data.get('collector_number', '0')

                    if 'image_uris' in part_data and image_size in part_data['image_uris']:
                        image_url = part_data['image_uris'][image_size]

                        if component_type == 'meld_result':
                            print(f"    Downloading and splitting meld result: {part_name}")
                            try:
                                response = requests.get(image_url)
                                response.raise_for_status()
                                img = Image.open(BytesIO(response.content))
                                
                                width, height = img.size
                                top_half = img.crop((0, 0, width, height // 2))
                                bottom_half = img.crop((0, height // 2, width, height))

                                top_half = top_half.transpose(Image.Transpose.ROTATE_90)
                                bottom_half = bottom_half.transpose(Image.Transpose.ROTATE_90)
                                
                                if add_border_flag:
                                    pixel_width, _ = top_half.size
                                    effective_dpi = pixel_width / CARD_HEIGHT_INCHES
                                    border_pixels = round(effective_dpi * BORDER_INCHES)
                                    print(f"    Applying {border_pixels}px border to meld parts.")
                                    
                                    top_half = add_border(top_half, border_pixels, border_color)
                                    bottom_half = add_border(bottom_half, border_pixels, border_color)
                                
                                if image_format == 'jpg':
                                    if top_half.mode == 'RGBA':
                                        top_half = top_half.convert('RGB')
                                    if bottom_half.mode == 'RGBA':
                                        bottom_half = bottom_half.convert('RGB')

                                top_filename = f"{part_set}-{part_number}-{part_name}-top.{image_format}"
                                bottom_filename = f"{part_set}-{part_number}-{part_name}-bottom.{image_format}"

                                top_half.save(os.path.join(download_dir, top_filename))
                                bottom_half.save(os.path.join(download_dir, bottom_filename))
                                print(f"      Saved: {top_filename} and {bottom_filename}")

                            except Exception as e:
                                print(f"    Error processing meld result image for {part_name}: {e}")
                        else:
                            file_name = f"{part_set}-{part_number}-{part_name}.{image_format}"
                            file_path = os.path.join(download_dir, file_name)
                            download_and_save(image_url, file_path, True)
                    else:
                        print(f"    Could not find image URI for size '{image_size}' for meld part: {part_name}")
        else:
            print(f"  Layout is 'meld' but no 'all_parts' data found for {card_name}.")
    else:
        print(f"  Unhandled card layout: '{layout}' for card {card_name}. Skipping.")

def main():
    """Main function to run the script."""
    print("=========================================")
    print(" Scryfall Magic: The Gathering Downloader")
    print("=========================================")

    if getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))

    download_mode = ''
    print("\nSelect download mode:")
    print("[1] Download a full Set")
    print("[2] Download a single card by URL")
    print("[3] Download from Pasted Decklist")
    while True:
        choice = input("Enter your choice (1, 2, or 3): ").strip()
        if choice in ['1', '2', '3']:
            download_mode = choice
            break
        print("Invalid choice. Please enter 1, 2, or 3.")

    image_sizes = ['small', 'normal', 'large', 'png', 'art_crop', 'border_crop']
    print("\nAvailable image sizes:")
    for i, size in enumerate(image_sizes):
        print(f"[{i+1}] {size}")
    
    image_size_choice = ''
    while True:
        try:
            choice = input(f"Enter desired image size (1-{len(image_sizes)}): ").strip()
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(image_sizes):
                image_size_choice = image_sizes[choice_index]
                break
            else:
                print("Invalid number. Please choose from the list.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    add_border_flag = False
    border_color = ''
    print("\nAdd a 1/8 inch border for print bleed?")
    print("[1] Yes")
    print("[2] No")
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice == '1':
            add_border_flag = True
            break
        elif choice == '2':
            add_border_flag = False
            break
        print("Invalid choice. Please enter 1 or 2.")

    if add_border_flag:
        print("\nEnter border color:")
        print("[1] Black")
        print("[2] White")
        print("[3] Transparent")
        color_map = {'1': 'black', '2': 'white', '3': 'transparent'}
        while True:
            choice = input("Enter your choice (1, 2, or 3): ").strip()
            if choice in color_map:
                border_color = color_map[choice]
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        print(f"A 1/8 inch ({border_color}) border will be added. Pixel size is calculated per-image.")

    cards_to_process = []
    folder_name = ""

    if download_mode == '1':
        set_code = input("\nEnter the set letter tag (e.g., BRO, DSK): ").strip().lower()
        folder_name = set_code
        search_url = f"{SCRYFALL_API_BASE_URL}/cards/search?q=set%3A{set_code}&unique=cards"
        print(f"\nFetching card list for set: {set_code.upper()}...")
        while search_url:
            try:
                time.sleep(REQUEST_DELAY)
                response = requests.get(search_url)
                response.raise_for_status()
                json_data = response.json()
                cards_to_process.extend(json_data.get('data', []))
                if json_data.get('has_more'):
                    search_url = json_data.get('next_page')
                    print("  Found more pages, fetching next...")
                else:
                    search_url = None
            except requests.exceptions.RequestException as e:
                print(f"Error fetching set data: {e}")
                print("Please check if the set code is correct.")
                search_url = None

    elif download_mode == '2':
        card_url = input("\nPaste the full Scryfall card URL: ").strip()
        folder_name = "singles"
        card_data = get_card_data_from_url(card_url)
        if card_data:
            cards_to_process.append(card_data)

    elif download_mode == '3':
        folder_name = sanitize_filename(input("\nEnter a name for the deck folder: ").strip())
        if not folder_name:
            folder_name = "pasted-deck"
        print("\nPaste your decklist below (view README for format). Enter a blank line to finish.")
        deck_lines = []
        while True:
            line = input()
            if not line:
                break
            deck_lines.append(line)
        line_regex = re.compile(r"^\s*(\d+)\s+(.+?)(?:\s+\((\w{3,5})\)\s+([\w\d-]+))?\s*$")
        processed_cards = set()
        print(f"\nParsing decklist and fetching from Scryfall...")
        for line in deck_lines:
            match = line_regex.match(line)
            if not match:
                print(f"Warning: Could not parse line '{line}'. Skipping.")
                continue
            _, name, set_code, number = match.groups()
            name = name.strip()
            card_identifier = f"{set_code.lower()}-{number}" if set_code and number else name
            if card_identifier in processed_cards:
                continue
            api_url = f"{SCRYFALL_API_BASE_URL}/cards/{set_code.lower()}/{number}" if set_code and number else f"{SCRYFALL_API_BASE_URL}/cards/named?exact={quote_plus(name)}"
            try:
                time.sleep(REQUEST_DELAY)
                response = requests.get(api_url)
                response.raise_for_status()
                cards_to_process.append(response.json())
                processed_cards.add(card_identifier)
                print(f"  Found: {name}")
            except requests.exceptions.RequestException as e:
                print(f"  Error finding '{name}': {e}")
    
    if not cards_to_process:
        print("\nNo cards to download. Exiting.")
        return

    print("\nA file dialog will now open. Please select where to save the output folder.")
    root = tkinter.Tk()
    root.attributes('-topmost', True) # Force the dialog to the front
    root.withdraw()  # Hide the root window
    base_dir = filedialog.askdirectory(
        parent=root,
        initialdir=script_dir,
        title="Please select a directory to save your card folder in"
    )
    root.destroy() # Clean up the root window after selection

    if not base_dir:
        print("\nNo directory selected. Exiting program.")
        return

    download_dir = os.path.join(base_dir, folder_name)

    if not os.path.exists(download_dir):
        print(f"\nCreating directory: {download_dir}")
        os.makedirs(download_dir)

    print(f"\nStarting download of {len(cards_to_process)} card(s) as '{image_size_choice}' images...")
    
    for card in cards_to_process:
        process_card(card, image_size_choice, download_dir, add_border_flag, border_color)
        time.sleep(REQUEST_DELAY)

    print("\n=========================================")
    print("Download process finished!")
    print("=========================================")

if __name__ == "__main__":
    while True:
        try:
            main()

        except Exception as e:
            print("\n\n--- AN UNEXPECTED ERROR OCCURRED ---")
            print("The program encountered a fatal error and had to stop.")
            print("----------------- ERROR REPORT -----------------")
            
            traceback.print_exc()
            
            print("----------------- END OF REPORT ----------------")
            input("\nPress ENTER to acknowledge and continue...")

        while True:
            restart_choice = input("\nWould you like to restart the program? (y/n): ").lower().strip()
            if restart_choice in ["y", "yes", "n", "no"]:
                break
            else:
                print("Invalid input. Please enter 'y' for yes or 'n' for no.")

        if restart_choice in ["n", "no"]:
            break
        
        print("\nRestarting program...")
        time.sleep(1)

    print("\nClosing program. Goodbye!")
    time.sleep(2)