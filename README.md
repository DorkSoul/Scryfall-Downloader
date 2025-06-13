# Scryfall Magic: The Gathering Card Downloader

This is a Python script that allows you to download Magic: The Gathering card images from the Scryfall API.

## Features

### Multiple Download Modes:
* Download an entire Magic set by its three-letter code (e.g., MOM, LTR).
* Download a single card by pasting its Scryfall URL.
* Download an entire decklist by pasting it directly into the console.

### Print-Ready Borders:
* Optionally add a 1/8th inch bleed edge to any card. Print services like MakePlayingCards.com use this size.
* Choose your border color: Black, White, or Transparent.
* Border size is calculated based on each image's resolution.

### Scryfall Image Sizes:
* Choose from image sizes provided by Scryfall, such as `png`, `large`, `normal`, and `art_crop`.

### Layout Handling:
* Downloads front faces of single-faced cards.
* Downloads both faces of double-faced cards.
* Downloads all parts of meld cards.

## Requirements (for running from .py file)
* Python 3.x
* The `requests` and `Pillow` libraries. You can install them via pip:
    ```
    pip install requests Pillow
    ```

# How to Use

1.  Download `Scryfall Downloader.exe` from the releases tab (https://github.com/DorkSoul/Scryfall-Downloader/releases).
2.  Double-click to run.
3.  A console window will appear. Follow the on-screen menu prompts.

## Menu Options Walkthrough

- ### Input the number corresponding to your choice in each case preceded by a number and press enter ###

1.  **Select Download Mode:**
    * `[1] Download a full Set`: You will be asked for the set's letter code (e.g., WOE).
    * `[2] Download a single card by URL`: You will be asked to paste the full URL of a card from the Scryfall website.
    * `[3] Download from Pasted Decklist`: You will be asked for a folder name and then prompted to paste a decklist. See the format below.

    **1.1**  **Full Set:** Enter the letter code and press enter

    **1.2**  **Single Card:** Paste in the scryfall cards url (e.g., https://scryfall.com/card/cn2/78/queen-marchesa )

    **1.3**  **Decklist:** 
    
        * Enter a name for the folder that will be created and filled with the card images for the deck and press enter.

        * When pasting a decklist please ensure there are no empty lines as these will end the download at that point. 

        * If you want more from a sideboard for example run the program again and paste those in.

        * Two formats are accepted for decklists. 
        
        * The quantity of a card is required for formatting but its value does not matter since only one image will be downloaded.

        * Once the deck has been pasted in press enter on a black line to continue the program   
          (you may need to press enter a second time if the last line in the console is the last card in the deck and not a blank line)

    **With Set/Number information (Recommended for specific versions):**
    ```
    1 Sol Ring (LTC) 280
    4 Counterspell (2XM) 46
    10 Island (SLD) 102
    etc...
    ```

    **Without Set/Number information (Will get the default printing):**
    ```
    1 Sol Ring
    4 Counterspell
    10 Island
    etc...
    ```

2.  **Select Image Size:** Choose your desired image quality and crop.
    * `[1] small`: 146 × 204
    * `[2] normal`: 488 × 680
    * `[3] large`: 672 × 936
    * `[4] png`: 745 × 1040
    * `[5] art_crop`: Varies
    * `[6] border_crop`: 480 × 680
3.  **Print Border:** Choose if you want to add the 1/8th inch print bleed edge. If you select yes, you will then choose the border color from black, white or transparent.
4.  **Save Location:** File Explorer will pop up. Navigate to the directory where you want your new folder of cards to be created and click "Select Folder".

## Disclaimer

This tool is for personal use only and is made possible by the incredible work of the Scryfall team.  
Please use this tool responsibly and be respectful of the Scryfall API.  
The script includes a built-in delay to comply with their rate limits.  