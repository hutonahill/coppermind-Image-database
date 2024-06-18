from getImages import checkForSummery, get_all_images, get_page_wikitext, URL, SESSION, highlight_diffs
from urllib.parse import unquote
import re
import requests
import random
import json

SAVE_FILE = "saveEdit.json"

CONFIRMED_KEY = "confirmed"
TODO_KEY = "todo"
REJECTED_KEY = "rejected"

# looking to repurpose this script? this is the function to edit.
def editDescriptions() -> list[tuple[str, str, str]]:
    all_images = get_all_images()

    print(f"Fetched {len(all_images)} images.")
    #print(json.dumps(all_images, indent=4))

    
    # get the description URLs out of all the image data
    descriptions = []

    for image in all_images:
        description_url = image.get("descriptionurl")
        description_url = unquote(description_url)

        end_description_url = description_url.split('/')[-1]
        descriptions.append(end_description_url)

    wikitexts = get_page_wikitext(descriptions)

    # index 0: wikitext, index 1: page title
    noSum = checkForSummery(wikitexts)

    print(f"found {len(noSum)} page(s) with no summery header")

    editList = []

    for page in noSum:
        tablePattern = r'\{\{([^{}]+)\}\}'

        # create a copy of the page wiki text that we can manipulate it and keep a record of what it used to be.
        assessmentCopy = page[0]

        matches = re.findall(tablePattern, assessmentCopy)

        # make sure the pages we edit meet our requirements.
        if (len(matches) == 1):
            assessmentCopy.replace(matches[0], "")

            if(len(assessmentCopy) >= 5):
                newText = "== Summary ==\n" + page[0]

                # [0]: page title, [1]: the new page, [2]: the old page
                editList.append((page[1], newText, page[0]))
    
    return editList

        

def editAPI(Token:str, pageTitle:str, newText:str, summery: str) -> bool:
    
    params = {
        "action": "edit",
        "title": pageTitle, # Title of the page to edit.
        "nocreate":"true", # If the page doesn't exist, throw an error
        "section": "0",  # Section number (0 for the whole page)
        "text": newText,  # The new content to be added to the page
        "token": Token,  # Edit token required for editing. (get the from logIn method)
        "format": "json",
        "bot": "true", # Edit is marked as a bot (wont show up in the timeline. I think.)
        "minor": "true", # Marks the edit as minor
        "summary": summery # Summery of the edit
    }

    response = requests.post(URL, data=params)
    
    if(response["result"] == "Success"):
        return
    else:
        print(f"editAPI.ERROR: {response["error"]}")

def logIn() -> tuple[bool, str]:

    # Retrieve login token first
    PARAMS_0 = {
        'action':"query",
        'meta':"tokens",
        'type':"login",
        'format':"json"
    }

    response = SESSION.get(url=URL, params=PARAMS_0)
    DATA = response.json()

    LOGIN_TOKEN = DATA['query']['tokens']['logintoken']


    # then actually log in with a bot account.
    print("BOT ACCOUNTS ONLY!")
    username = input("username: ")
    password = input("password: ")

    PARAMS_1 = {
        "action": "login",
        "lgname": username,
        "lgpassword": password,
        "lgtoken": LOGIN_TOKEN,
        "format": "json"
    }

    # overwrite the memory of the users credentials
    for i in range(5):
        username = str(random.random() * random.randint(1,10000000))
        password = str(random.random() * random.randint(1,10000000))

    response = SESSION.post(URL, data=PARAMS_1)
    DATA = response.json()

    result = DATA["login"]["result"]

    # if logging in worked, get our CSRF_TOKEN and inform the user.
    if(result == "Success"):

        # Step 3: GET request to fetch CSRF token
        PARAMS_2 = {
            "action":"query",
            "meta":"tokens",
            "format":"json"
        }

        response = SESSION.get(url=URL, params=PARAMS_2)
        DATA = response.json()

        CSRF_TOKEN = DATA['query']['tokens']['csrftoken']

        return True, CSRF_TOKEN
    else:
        print(json.dumps(DATA, indent=4))
        return False, ""

def logout(Token:str) -> bool:
    PARAMS_3 = {
        "action": "logout",
        "token": Token,
        "format": "json"
    }

    R = SESSION.post(URL, data=PARAMS_3)
    DATA = R.json()

    if (not DATA):
        return True
    else:
        print(json.dumps())

def print_bold(text: str) -> None:
    print(f"\033[1m{text}\033[0m")

    
def writeFile(filename: str, data: dict) -> None:
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4, sort_keys=True)

def readFile(filename: str) -> dict:
    with open(filename, 'r') as file:
        return json.load(file)

if (__name__ == "__main__"):
    
    print('\nStarting...')

    

    confirmedEdits = []

    rejectedEdits = []

    editsToCheck = []

    # Ask wether to use the save.
    command = input("Do you want to use a save?(y/n) ").lower()

    if(command == "y" or command == "yes" or command == "use"):
        output = readFile(SAVE_FILE)
        confirmedEdits = output[CONFIRMED_KEY]
        editsToCheck = output[TODO_KEY]
        rejectedEdits = output[REJECTED_KEY]

    else:
        # [[0]: page title, [1]: the new page, [2]: the old page]
        editsToCheck = editDescriptions()

        save = {
            CONFIRMED_KEY:confirmedEdits,
            TODO_KEY:editsToCheck,
            REJECTED_KEY:rejectedEdits
        }

        writeFile(SAVE_FILE, save)

        

    # loop though all the proposed edits
    while (len(editsToCheck) > 0):
        target = editsToCheck[-1]

        highlighted = highlight_diffs(target[2], target[1])

        print_bold(f"#{len(editsToCheck)}: {target[0]}")
        print(highlighted)

        command = input("> ")

        command = command.replace(" ", "").lower()

        # if the edit is good, go back
        if (command == "" or command == "yes" or command == "y"):
            confirmedEdits.append(editsToCheck.pop(-1))
            print("Edit Saved")
        
        # un confirm an edit
        elif (command == "back" or command == "b"):
            editsToCheck.append(confirmedEdits.pop(-1))
            print("Undone confirmation")
        
        # command to print confirmed edits
        elif (command == "save"):
            print(f"good edits:  {len(confirmedEdits)} \n" +
                  f"bad edits:   {len(rejectedEdits)} \n" +
                  f"edits to go: {len(editsToCheck)} ")

            save = {
                CONFIRMED_KEY:confirmedEdits,
                TODO_KEY:editsToCheck,
                REJECTED_KEY:rejectedEdits
            }

            writeFile(SAVE_FILE, save)
        
        # re-que all edits that were marked as rejected.
        elif (command == "dump" or command == "review"):
            editsToCheck = editsToCheck + rejectedEdits
            print("Added canceled edits to edits to do")
        
        # re-ques the most recent rejected edit.
        elif (command == "dumpone" or command == "dump1" or 
              command == "reviewone" or command == "review1"):
            editsToCheck.append(rejectedEdits.pop(-1))
            print("Returned one canceled edit to the todo stack.")
        
        # All good programs with commands have a help command.
        elif(command == "help" or command == "h"):
            print("Command List:" + 
                  "\thelp: prints this page \n" + 
                  "\t'': just hit enter and the current edit will be marked as confirmed. \n" + 
                  "\tback: takes the last confirmed edit and puts it back in the todo que \n" + 
                  "\tsave: saves the current progress to a file. \n" + 
                  "\tdump: dumps all edits that are marked as rejected back into the todo que \n" + 
                  "\tdumpOne: dumps the most recent rejected edit back into the todo que\n")

        # default is to assume the edits are bad.
        else:
            print("Bad Edit")
            rejectedEdits.append(editsToCheck.pop(-1))

        print()
    
    print(f"good edits: {len(confirmedEdits)} \nbad edits: {len(rejectedEdits)}")

    print()
    save = {
        CONFIRMED_KEY:confirmedEdits,
        TODO_KEY:editsToCheck,
        REJECTED_KEY:rejectedEdits
    }

    writeFile(SAVE_FILE, save)
    
