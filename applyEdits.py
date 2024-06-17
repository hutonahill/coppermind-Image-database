from editImages import editAPI, logIn, logout, readFile, SAVE_FILE, CONFIRMED_KEY

# This Script carries out the edit after its been conferred. Its likely to take a long time as 
# I don't know how to do edit calls in bulk.

# If your trying to repurpose this script, modify the 3rd parameter for editAPI to match what your doing

if (__name__ == "__main__"):
    didLoginPass, LoginKey = logIn()

    if (didLoginPass == True):
        confirmedEdits = []

        output = readFile(SAVE_FILE)
        confirmedEdits = output[CONFIRMED_KEY]

        for edit in confirmedEdits:
            title = edit[0]
            newPageText = edit[1]
            editAPI(LoginKey, title, newPageText, "Added Summery header.")
    else:
        print("Login Failed.")