#!/usr/bin/python3

import json     
import requests
import re
from urllib.parse import unquote
import time

import difflib

URL = "https://coppermind.net/w/api.php"

def highlight_diffs(original:str, edit:str) -> str:
    differ = difflib.Differ()
    diff = list(differ.compare(original, edit))
    highlighted_output = ""
    for item in diff:
        if item.startswith('- '):
            highlighted_output += f'\033[91m{item[2:]}\033[0m'  # Red color for missing bits
        elif item.startswith('+ '):
            highlighted_output += f'\033[92m{item[2:]}\033[0m'  # Green color for additions
        else:
            highlighted_output += item[2:]
    return highlighted_output

# Global variable to control the maximum number of images retrieved
MAX_IMAGES = -1 # Default value is -1 (get everything)

SESSION = requests.Session()

def get_all_images():
    all_images = []

    PARAMS = {
        "action": "query",
        "format": "json",
        "list": "allimages",
        "ailimit": MAX_IMAGES if MAX_IMAGES > 0 else "max"  # Set maximum limit to retrieve all images or MAX_IMAGES
    }
    
    running = True

    while running:
        R = SESSION.get(url=URL, params=PARAMS)
        DATA = R.json()

        if ("error" in DATA):
            print(f"get_all_images.ERROR: {DATA["error"]}")
        else:
            newImages = DATA["query"]["allimages"]
            type(newImages)

            all_images.extend(newImages)

            # Continue fetching if there are more images and MAX_IMAGES is not set
            if ('continue' in DATA and MAX_IMAGES < 0):  
                PARAMS.update(DATA['continue'])
            else:
                running = False

    return all_images

def get_page_info(page_titles:str):
    
    PARAMS = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "titles": page_titles,
        "exintro": True,
        "explaintext": True
    }

    response = SESSION.get(url=URL, params=PARAMS)
    DATA = response.json()

    # Extract page content from the response
    page_info = next(iter(DATA["query"]["pages"].values()), None)
    if page_info:
        return page_info.get("extract")

    return None

from bs4 import BeautifulSoup

# Global counter variable
no_artist_found_count = 0

import requests
import re

knownInvalidTitles = []

def get_page_wikitext(page_titles) -> list[(str, str)]:
    assert type(page_titles) == list, f"page_titles == {page_titles}"

    # Split the page titles into chunks of 50 or fewer 
    # this is due to API limits
    chunk_size = 50
    chunks = []
    for i in range(0, len(page_titles), chunk_size):
        chunk = page_titles[i:i + chunk_size]
        chunks.append(chunk)

    output = []

    invalidCounter = 0
    invalidTitles = []

    for chunk in chunks:
        pages = '|'.join(chunk)

        PARAMS = {
            "action": "query",
            "format": "json",
            "prop": "revisions",
            "titles": pages,
            "rvprop": "content",
            "rvslots": "main",
            "formatversion": "2"
        }

        R = SESSION.get(url=URL, params=PARAMS)
        DATA = R.json()

        
        #print(json.dumps(DATA, indent=4))
        pages = DATA["query"]["pages"]
        #print(json.dumps(pages, indent=4))
        

        # Extract raw Wikitext from the response
        for page in pages:
            if ("invalid" in page and page["invalid"] == True):
                invalidCounter += 1
                invalidTitles.append((page["title"], page["invalidreason"]))

            else:
                page_content = page["revisions"][0]["slots"]["main"]["content"]
                title = page["title"]
                output.append((page_content, title))

    if (invalidCounter > 0):
        for badTitle in invalidTitles:
            if badTitle[0] not in knownInvalidTitles:
                print(f"New Invalid: \n\t`{badTitle[0]}`\n\t{badTitle[1]}")
            else:
                knownInvalidTitles.remove(badTitle)
        
        if (len(knownInvalidTitles) > 0):
            print("The following titles are no longer invalid!")
            print(f"\t{knownInvalidTitles}")
        
        print()

    return output

def parseArtist(input_text:str):

    if input_text:
        # Define patterns for when link comes first
        linkArtist_patterns = [
            r'\[(https?://.*?)\s(.*?)\]',           # Pattern for '[ artistLink artist]'
            r'^https?://(.*?)\s+(.*?)$',            # Pattern for 'artistLink artist'
        ]

        # Define patterns for when artist name comes first
        artistLink_patterns = [
            r'\[\[User:\s(.*?)\]\]',                  # Pattern for '[[User: artist]]'
            r'\[\[(.*)\]\]',                          # Pattern for '[[artist]]'
            r'(.*)'                                   # Pattern for 'artist'
        ]

        # Try matching patterns where link comes first
        for pattern in linkArtist_patterns:
            match = re.search(pattern, input_text)
            if match:
                artistLink = match.group(1)
                artist = match.group(2) if len(match.groups()) > 1 else ""

                if (artist == '' and artistLink == ''):
                    pass
                return artist, artistLink

        # Try matching patterns where artist name comes first
        for pattern in artistLink_patterns:
            match = re.search(pattern, input_text)
            if match:
                artist = match.group(1)
                artistLink = match.group(2) if len(match.groups()) > 1 else ""
                if (artist == '' and artistLink == ''):
                    pass
                return artist, artistLink
        

    # If no pattern matches, return empty strings
    return "", ""

def parseWebAddress(text:str):
    if(text):

        # Define the regular expression pattern for matching URLs
        url_pattern = r'(https?://\S+)'

        # Find the first match of the URL pattern in the text
        match = re.search(url_pattern, text)

        # Return the matched URL (or None if no match was found)
        return match.group(1) if match else None
    return None

def addArtInfo(wikitexts:list) -> tuple[dict[str, tuple[str, str]], bool]:

    #print(json.dumps(description_urls, indent=4))
    #print(json.dumps(wikitexts, indent=4))

    output = {}

    for i in range(len(wikitexts)): 

        wikitext = wikitexts[i][0]
        
        
        artist_match = re.search(r"artist=(.*?)\n", wikitext)
        source_match = re.search(r"source=(.*?)\n", wikitext)

        rawArtist = artist_match.group(1).strip() if artist_match else None
        (artist, artistLink) = parseArtist(rawArtist)
        rawSource = source_match.group(1).strip() if source_match else None
        source = parseWebAddress(rawSource)

        #print(f"type(wikitexts[{i}][1]) == {type(wikitexts[i][1])}, wikitexts[{i}][1] == {wikitexts[i][1]}")


        output[wikitexts[i][1]] = (artist, artistLink, source)

    

    return output

# creates a list of summaries based on the wikitext
summeryExempt = [
    "File:Zane by Ydunn Lopez.jpg",
    "File:Zane_by_Ydunn_Lopez.jpg",
    "File:AU Hope of Elantris.jpeg",
    "File:AU_Hope_of_Elantris.jpeg",
    "File:AU Allomancer Jak.jpeg",
    "File:AU Secret History.jpeg",
    "File:AU Sixth of the Dusk.jpeg",
    "File:Adhesion Surge-glyph.svg",
    "File:Abrasion Surge-glyph.svg",
    "File:Abrasion Void-glyph.svg",
    "File:Adhesion Void-glyph.svg",
    "File:Alcatraz Versus the Evil Librarians.jpeg",
    "File:Alcatraz Versus the Shattered Lens.jpg",
    "File:Alcatraz Versus the Knights of Crystallia.jpg",
    "File:Alcatraz Versus the Scrivener's Bones.jpg",
    "File:Allomantic Iron.png",
    "File:Allomantic Steel.png",
    "File:Allomantic Tin.png",
    "File:Allomantic Pewter.png",
    "File:Altered Perceptions.jpg",
    "File:AoL Polish Cover.jpg",
    "File:Arcanum Unbounded.jpg",
    "File:Ati.jpg"

]
blockedPages = [
    "File:Zinc.svg",
    "File:Aluminum.svg"
]
def checkForSummery(wikitexts:list[tuple[str, str]]) -> list[tuple[str, str]]:
    
    
    output = []

    for text in wikitexts:

        if text[1] not in summeryExempt and text[1] not in blockedPages:

            if "== Summary ==" not in text[0]:
                output.append(text)
        
    
    return output


def compileImages(): 
    all_images = get_all_images()

    print(len(all_images))
    #print(json.dumps(all_images, indent=4))

    

    descriptions = []
    for image in all_images:
        description_url = image.get("descriptionurl")
        description_url = unquote(description_url)
        descriptions.append(description_url)

    for i in range(len(descriptions)):
        descriptions[i] = descriptions[i].split('/')[-1]

    wikitexts = get_page_wikitext(descriptions)
    
    infoList = addArtInfo(wikitexts)
    
    #print(json.dumps(infoList, indent=4))
    
    results =[]

    for i in range(len(all_images)):

        title = all_images[i].get('title')

        artist = "None Found"
        artistLink = "None Found"
        src = "None Found"
        
        if (title in infoList):

            (artist, artistLink, src) = infoList[title]

        output = ''
        output += (f"Image:  `{title}`\n")
        output += (f"Artist: `{artist}`\n")
        output += (f"Artist Link: `{artistLink}`\n")
        output += (f"Source: `{src}`\n")
        output += ("\n")

        results.append(output)
    
    return results



def main():
    print("How long to get all images?")
    startTime = time.time()
    results = compileImages()

    # for i in range(len(results)-10, len(results)):
    #     print(results[i])
    
    endTime = time.time()

    delta = endTime - startTime
    print(f"Time Elapsed: {delta}s")

def test_highlight_diffs():
    original = "Hello"
    print(f"original == {original}\n")

    print(highlight_diffs(original, original+"World"))
    print()
    print(highlight_diffs(original, original+"\nWorld"))
    print()
    print(highlight_diffs(original, "World"+original))
    print()
    print(highlight_diffs(original, "World\n"+original))
    print()
    print(highlight_diffs(original, "World\n"+original + " Jim!"))
    print()
    print(highlight_diffs(original, "World\n"+original + "\nGoodbye"))
    print()
    print(highlight_diffs(original, original[0]))
    print()
    print(highlight_diffs(original, original[3]))

pass
#print(get_page_wikitext(["File:Adolin's_Shardblade.png", "File:AdolinKholin.png"]))

if (__name__ == "__main__"):
    main()