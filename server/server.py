from random import random

from flask import Flask, request, Response
from enum import Enum
import json
import uuid
import logging
from pymongo import MongoClient
import datetime

logger = logging.getLogger('root')
FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger.setLevel(logging.DEBUG)

db = MongoClient('mongodb://localhost:27017/').Game
Players = db.Player


class GameException(Exception):
    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return f"In Game Exception: {self.reason}"


class IllegalChoice(GameException):
    pass


class FormException(GameException):
    def __init__(self, reason, question):
        self.reason = reason
        self.question = question

    pass


class DoubleInput(FormException):
    pass


class MissingInput(FormException):
    pass


class IllegalInput(FormException):
    pass


class PlayerNotFound(GameException):
    pass


class EnumNotFound(GameException):
    pass


class IncorrectPassword(GameException):
    pass


class UsernameIsTaken(GameException):
    pass


class Skills(dict):
    def __init__(self):
        self['study_level'] = 0
        self['music_level'] = 0
        self['sports_level'] = 0
        self['cooking_level'] = 0
        self['social_level'] = 0
        self['went_to_school'] = 0
        self['went_to_sleep'] = 0


class Player(dict):
    def __init__(self, player_data, isNew):
        self.data = player_data
        if isNew:
            self.data['_id'] = str(uuid.uuid4())
            self.data['time_of_the_day'] = 8
            self.data['skills'] = Skills()
            self.data['creation_time'] = datetime.datetime.utcnow()
            self.data['last_update_time'] = datetime.datetime.utcnow()

    def get(self, attribute):
        return self.data[attribute]

    def set(self, attribute, value):
        self.data[attribute] = value
        self.updateInDB({attribute: value})

    def getSkill(self, skill):
        return self.data['skills'][skill]

    def raiseSkill(self, skill, by):
        skills = self.data['skills']
        raisedSkill = skills[skill] + by
        skills[skill] = raisedSkill
        self.updateInDB({"skills": skills})

    def spendTime(self, by):
        timeAfterSpending = self.data['time_of_the_day'] + by
        self.data['time_of_the_day'] = timeAfterSpending
        self.updateInDB({'time_of_the_day': timeAfterSpending})

    def raiseAge(self, by):
        ageAfterRaising = self.data['age'] + by
        self.data['age'] = ageAfterRaising
        self.updateInDB({'age': ageAfterRaising})

    def updateInDB(self, delta):
        delta['last_update_time'] = datetime.datetime.utcnow()
        query = {"_id": self.data["_id"]}
        newvalues = {"$set": delta}
        Players.update_one(query, newvalues)


class InputType(Enum):
    NAME = 1
    POSITIVE_INT = 2
    DOUBLE = 3
    USERNAME = 4
    PASSWORD = 5

    def getByLiteral(self, literal):
        return self[literal]


class QuestionsForNewPlayer(Enum):
    username = {
        "question": "Choose username:",
        "type": InputType.USERNAME
    }
    password = {
        "question": "Choose password:",
        "type": InputType.PASSWORD
    }
    name = {
        "question": "What's your name?",
        "type": InputType.NAME
    }
    age = {
        "question": "What's your age?",
        "type": InputType.POSITIVE_INT
    }
    height = {
        "question": "What's your height (cm)?",
        "type": InputType.POSITIVE_INT
    }
    city = {
        "question": "Where do you live?",
        "type": InputType.NAME
    }
    job = {
        "question": "What is your profession?",
        "type": InputType.NAME
    }

    @staticmethod
    def getAllLiterals():
        return list(map(lambda q: q.name, QuestionsForNewPlayer))

    @staticmethod
    def getAllValues():
        questions = list(map(lambda q: q.value, QuestionsForNewPlayer))
        questionNames = list(map(lambda q: q.name, QuestionsForNewPlayer))

        # adding the literal names to the dictionaries:
        for i in range(len(questions)):
            questions[i]["name"] = questionNames[i]
        return questions

    def getByLiteral(self, literal):
        wantedEnum = self[literal]
        if wantedEnum is None:
            raise EnumNotFound(f"NO SUCH ENUM: {literal}")
        return wantedEnum


class ChoiceOptions(Enum):
    SLEEP = {
        "string": "Sleep",
        "skill": "went_to_sleep",
        "timeSpent": 1
    }
    GO_TO_SCHOOL = {
        "string": "Go to school",
        "skill": "went_to_school",
        "timeSpent": 8,
    }
    LEARN_COOKING = {
        "string": "Learn cooking",
        "skill": "cooking_level",
        "timeSpent": 2
    }
    LEARN_GUITAR = {
        "string": "Learn guitar",
        "skill": "music_level",
        "timeSpent": 2
    }
    PLAY_FOOTBALL = {
        "string": "Play football",
        "skill": "sports_level",
        "timeSpent": 2
    }
    MEET_FRIENDS = {
        "string": "Meet friends",
        "skill": "social_level",
        "timeSpent": 3
    }
    READ_A_BOOK = {
        "string": "Read a book",
        "skill": "study_level",
        "timeSpent": 4
    }

    def getByLiteral(self, literal):
        wantedEnum = self[literal]
        if wantedEnum is None:
            raise EnumNotFound(f"NO SUCH ENUM: {literal}")
        return wantedEnum


class Game:
    def __init__(self):
        self.players = self._loadPlayersFromDB()

    def _loadPlayersFromDB(self):
        players = []
        playersData = Players.find()
        for playerData in playersData:
            players.append(Player(playerData, False))

        return players

    def _fixDictValues(self, dictToFix):
        for key in dictToFix:
            if (type(key) is dict or
                    type(key) is list):
                self._fixDictValues(key)
            elif (type(dictToFix[key]) is dict or
                  type(dictToFix[key]) is list):
                dictToFix[key] = self._fixDictValues(dictToFix[key])
            elif isinstance(dictToFix[key], Enum):
                # Replacing enums with their literal
                dictToFix[key] = dictToFix[key].name

        return dictToFix

    def _reformatJson(self, dictToFix):
        dictToFix = self._fixDictValues(dictToFix)

        return json.dumps(dictToFix, sort_keys=False, default=str)

    def _getPlayerById(self, id):
        for player in self.players:
            if player.data['_id'] == id:
                return player
        raise PlayerNotFound(f"NO PLAYER WITH ID: {id}")

    def _getPlayerByLoginData(self, loginData):
        for player in self.players:
            if player.data["username"] == loginData["username"]:
                if player.data["password"] == hash(loginData["password"]):
                    return player
                raise IncorrectPassword("Incorrect password!")

        raise PlayerNotFound(f"No Player With username {loginData['username']}")

    def _validateInput(self, input, inputType):
        if inputType == InputType.NAME:
            return self._validateName(input)
        elif inputType == InputType.POSITIVE_INT:
            return self._validatePositiveInt(input)
        elif inputType == InputType.USERNAME:
            return self._validateUsername(input)
        elif inputType == InputType.PASSWORD:
            return self._validatePassword(input)

    def _validateUsername(self, username):
        if not username.isalnum():
            raise IllegalInput("Given input isn't alphanumeric.")
        for player in self.players:
            if player.data["username"] == username:
                raise UsernameIsTaken(f"Username {username} is already taken")

        return username

    def _validatePassword(self, password):
        if len(password) < 7:
            raise IllegalInput("Password must contain at least 7 characters")

        return password

    def _validatePositiveInt(self, number):
        try:
            num = int(number)
            if num > 0:
                return num
            else:
                raise IllegalInput("Given input isn't positive.")

        except ValueError:
            raise IllegalInput("Given input isn't an integer.")

    def _validateName(self, name):
        if name.isalpha():
            return name
        else:
            raise IllegalInput("Given input isn't a name.")

    def _validatePlayer(self, answers):
        answeredQuestions = []
        for answer in answers:
            question = QuestionsForNewPlayer[answer]
            if question.name in answeredQuestions:
                raise DoubleInput(f"QUESTION: {question.name} HAS TWO ANSWERS", question)
            answeredQuestions.append(question.name)
            givenInput = answers[answer]
            inputType = InputType[question.value["type"]]
            isValid = self._validateInput(givenInput, inputType)
            if not isValid:
                raise IllegalInput(f"ILLEGAL INPUT: {givenInput} FOR QUESTION: {question.name}", question)

        allQuestions = QuestionsForNewPlayer.getAllLiterals()
        for question in allQuestions:
            if question not in answeredQuestions:
                raise MissingInput(f"MISSING ANSWER FOR QUESTION: {question.name}", question)

    def getFormForNewPlayer(self):
        response = QuestionsForNewPlayer.getAllValues()
        return self._reformatJson(response)

    def validateSingleInput(self, data):
        givenInput = data["givenInput"]
        inputType = InputType[data["type"]]
        isValid = self._validateInput(givenInput, inputType)

        if not isValid:
            if inputType == InputType.PASSWORD:
                message = "Invalid password"
            else:
                message = f"Invalid input: {givenInput} for type: {inputType}"
            response = {
                "status": "FAILURE", "message": message
            }
            return self._reformatJson(response)

        return self._reformatJson({"status": "SUCCESS"})

    def getPlayerById(self, data):
        player = self._getPlayerById(data['_id'])
        return self._reformatJson(player.data)

    def getPlayerByLoginData(self, loginData):
        player = self._getPlayerByLoginData(loginData)
        return self._reformatJson(player.data)

    def login(self, loginData):
        try:
            self._getPlayerByLoginData(loginData)
            return self._reformatJson({"status": "SUCCESS"})
        except PlayerNotFound:
            return self._reformatJson({"status": "FAILURE", "message": "NO SUCH PLAYER"})
        except IncorrectPassword:
            return self._reformatJson({"status": "FAILURE", "message": "INCORRECT PASSWORD"})

    def _reformatTime(self, hour):
        return str(hour).zfill(2) + ":00"

    def createNewPlayer(self, playerData):
        self._validatePlayer(answers=playerData)
        playerData["password"] = hash(playerData["password"])
        player = Player(playerData, True)
        print(f"NEW PLAYER CREATED: {player.data['_id']}")
        self.players.append(player)
        Players.insert_one(player.data)
        return self._reformatJson({
            "status": "SUCCESS",
            "playerId": player.data["_id"],
            "name": player.data["name"],
            "time": self._reformatTime(player.data["time_of_the_day"])
        })

    def getBasicDetailsForLogin(self, body):
        try:
            player = self._getPlayerById(body["playerId"])
            return self._reformatJson({
                "status": "SUCCESS",
                "playerId": player.data["_id"],
                "name": player.data["name"],
                "time": self._reformatTime(player.data["time_of_the_day"])
            })
        except PlayerNotFound:
            return self._reformatJson({
                "status": "FAILURE",
                "message": f"NO PLAYER WITH ID: f{body['playerId']}"
            })

    def getRelevantMenu(self, loginData):
        currentPlayer = self._getPlayerByLoginData(loginData)
        ADULT_OPTIONS = [ChoiceOptions.LEARN_COOKING, ChoiceOptions.LEARN_GUITAR, ChoiceOptions.PLAY_FOOTBALL,
                         ChoiceOptions.MEET_FRIENDS, ChoiceOptions.READ_A_BOOK]

        if (currentPlayer.get('time_of_the_day') > 20 or
                int(currentPlayer.get('age')) < 5):
            options = [ChoiceOptions.SLEEP]
        elif int(currentPlayer.get('age')) < 18:
            options = [ChoiceOptions.GO_TO_SCHOOL]
        else:
            options = ADULT_OPTIONS

        optionsForResponse = []
        for option in options:
            optionsForResponse.append({
                "literal": option.name,
                "string": option.value["string"]
            })

        response = {
            "status": "SUCCESS",
            "name": currentPlayer.get("name"),
            "time": self._reformatTime(currentPlayer.get("time_of_the_day")),
            "options": optionsForResponse
        }
        return self._reformatJson(response)

    def getPlayerData(self, body):
        currentPlayer = self._getPlayerById(body['playerId'])
        return self._reformatJson(currentPlayer.data)

    def _handleAgeEvents(self, player, choice):
        if ((choice == ChoiceOptions.SLEEP and
             player.getSkill(choice.value['skill']) % 10 == 0) or
                (choice == ChoiceOptions.GO_TO_SCHOOL and
                 player.getSkill(choice['skill']) % 10 == 0)):
            player.raiseAge(1)

    def _handleDailyBonus(self, player, choice):
        skills = player.data["skills"]
        if (choice == ChoiceOptions.SLEEP and
                player.getSkill(choice.value['skill']) % 7 == 0 and
                player.get('time_of_the_day') == 8):
            skillToRaise = random.choice(list(skills))
            player.raiseSkill(skillToRaise, 1)

    def handleChoice(self, body):
        currentPlayer = self._getPlayerByLoginData(body['loginData'])
        choice = ChoiceOptions[body['choice']]
        currentPlayer.raiseSkill(choice.value['skill'], 1)
        if choice == ChoiceOptions.SLEEP:
            currentPlayer.set("time_of_the_day", 8)
        else:
            currentPlayer.spendTime(choice.value['timeSpent'])

        # now handling linked events:
        self._handleAgeEvents(currentPlayer, choice)
        self._handleDailyBonus(currentPlayer, choice)

        return self._reformatJson({"status": "SUCCESS", "playerData": currentPlayer.data})


game = Game()
app = Flask(__name__)


@app.route('/invokeAction/<action>', methods=['GET', 'POST'])
def invoke_action(action):
    if request.method == 'POST' and request.json is None:
        body = json.dumps({"status": "FAILURE", "message": "INVALID FORMAT"}, sort_keys=False)
        return Response(body, mimetype='text/json')
    if not hasattr(game, action):
        body = json.dumps({"status": "FAILURE", "message": f"NO SUCH FUNCTION: {action}"}, sort_keys=False)
        return Response(body, mimetype='text/json')
    if not isPermitted(action):
        body = json.dumps({"status": "FAILURE", "message": f"NOT PERMITTED FOR ACTION: {action}"}, sort_keys=False)
        return Response(body, mimetype='text/json')

    content = request.json
    function = getattr(game, action)

    if request.method == 'POST':
        body = function(content)
    else:  # GET
        body = function()
    return Response(body, mimetype='text/json')
    # except Exception as e:
    #     body = json.dumps({"Status": "FAILURE", "Message": "AN INTERNAL ERROR HAS OCCURRED"}, sort_keys=False)
    #     logger.error(e)
    #     return Response(body, mimetype='text/json')


def isPermitted(action):
    # action that start with '_' are internal and aren't meant to be directly invoked.
    return not action.startswith('_')


if __name__ == '__main__':
    app.run(host='localhost', port='8081', debug=True)
