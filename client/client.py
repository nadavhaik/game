#
# API 1st
# > Think about Edge cases
# > Make sure it's a PARAMETER
#

import json
import sys
import requests
import getpass

# Game Class + Game Exceptions --> world.py

# Player --> player.py

# client.py <-- Init Player, World, Run.

# GitLab <--

serverAddress = "http://127.0.0.1:8081"


class GameException(Exception):
    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return f"In Game Exception: {self.reason}"


class IllegalChoice(GameException):
    pass


class IllegalInput(GameException):
    pass


class NoSuchPlayer(GameException):
    pass


class LoginError(GameException):
    pass


class ServerError(GameException):
    pass


class Game:
    def sendPostRequestToServer(self, wantedAction, body):
        return requests.post(url=(serverAddress + "/invokeAction/" + wantedAction),
                             headers={'Accept': 'application/json'},
                             json=body).json()

    def sendGetRequestToServer(self, wantedAction):
        return requests.get(url=(serverAddress + "/invokeAction/" + wantedAction)).json()

    def __init__(self):
        pass

    def login(self, loginData):
        details = self.sendPostRequestToServer("login", loginData)

        if details["status"] == "FAILURE":
            raise LoginError(details["message"])

        return details

    def reformatTime(self, hour):
        return str(hour).zfill(2) + ":00"

    def getRelevantMenu(self, loginData):

        answer = self.sendPostRequestToServer("getRelevantMenu", loginData)
        menu = answer["options"]
        name = answer["name"]
        time = answer["time"]
        print(f"Hello {name}, it's {time} o'clock. what would you like to do?")
        for i in range(len(menu)):
            print(f"{str(i + 1)}. {menu[i]['string']}")
        print("To show player details enter *")

        choice = input()
        if self.isValidMenuChoice(choice, menu):
            if choice == '*':
                details = self.sendPostRequestToServer("getPlayerByLoginData", loginData)
                print(json.dumps(details, indent=4, sort_keys=False))
            else:
                response = self.sendPostRequestToServer("handleChoice", {
                    "loginData": loginData,
                    "choice": menu[int(choice) - 1]["literal"]
                })
                time = self.reformatTime(response["playerData"]["time_of_the_day"])
                return time
        else:
            raise IllegalChoice("Illegal choice")

    def isValidMenuChoice(self, choice, options):
        if (choice == '*') | (choice == '#'):
            return True
        elif choice.isnumeric() and int(choice) <= len(options):
            return True
        return False

    def validateInput(self, givenInput, inputType):
        answer = self.sendPostRequestToServer("validateSingleInput", {
            "givenInput": givenInput,
            "type": inputType,
        })

        if answer["status"] == "FAILURE":
            raise IllegalChoice(answer["message"])

        return givenInput

    def getQuestionsFromServer(self):
        return self.sendGetRequestToServer("getFormForNewPlayer")

    def createPlayer(self, playerData):
        response = self.sendPostRequestToServer("createNewPlayer", playerData)
        if response["status"] == "FAILURE":
            raise ServerError("An unknown error has occured")
        return playerData["username"], playerData["password"]

    def buildPlayer(self):
        # Initialize as None for checking
        player = {}
        questions = self.getQuestionsFromServer()

        while True:
            try:
                for question in questions:
                    key = question["name"]
                    questionText = question["question"]
                    inputType = question["type"]
                    try:
                        if player.get(key, None) is None:
                            if inputType == "PASSWORD":
                                while True:
                                    print(questionText)
                                    password = getpass.getpass()
                                    print("Re-enter password:")
                                    reEnterPassword = getpass.getpass()
                                    if password != reEnterPassword:
                                        print("Passwords don't match!")
                                    else:
                                        break
                                player[key] = self.validateInput(password, inputType)
                            else:
                                player[key] = self.validateInput(input(questionText + "\n"), inputType)
                    except IllegalChoice as e:
                        print(e.reason)
                break

            except IllegalInput:
                print("Illegal input.")

        return self.createPlayer(player)

    def getMenuForPlayer(self, loginData):
        while True:
            try:
                time = self.getRelevantMenu(loginData)
            except IllegalChoice:
                print("Illegal choice.")

    def run(self, loginData):
        while True:
            self.getMenuForPlayer(loginData)


def main():
    game = Game()
    print("Hello! What would you like to do?")
    print("1. Login")
    print("2. Register")
    while True:
        choice = input()
        if not ((choice.isnumeric()) and (0 < int(choice) < 3)):
            print("Illegal choice.")
        else:
            break

    if choice == "1":
        while True:
            print("Enter username:")
            username = input()
            print("Enter password:")
            password = getpass.getpass()
            try:
                game.login({"username": username, "password": password})
                break
            except LoginError as e:
                print(e.reason)
    else:
        username, password = game.buildPlayer()

    # i.e., Plaeyer
    game.run({"username": username, "password": password})  # for player in self._players ....


if __name__ == "__main__":
    sys.exit(main())
