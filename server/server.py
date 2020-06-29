from random import random

from flask import Flask, request, Response
from enum import Enum
import json
import uuid
import logging

logger = logging.getLogger('root')
FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger.setLevel(logging.DEBUG)


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
    def __init__(self, player_data):
        self.data = player_data
        self.data['id'] = str(uuid.uuid4())
        self.data['time_of_the_day'] = 8
        self.data['skills'] = Skills()

    def get(self, attribute):
        return self.data[attribute]

    def set(self, attribute, value):
        self.data[attribute] = value

    def getSkill(self, skill):
        return self.data['skills'][skill]

    def raiseSkill(self, skill, by):
        self.data['skills'][skill] += by

    def spendTime(self, by):
        self.data['time_of_the_day'] += by

    def raiseAge(self, by):
        self.data['age'] += by


class InputType(Enum):
    NAME = 1
    POSITIVE_INT = 2
    DOUBLE = 3

    def getByLiteral(self, literal):
        return self[literal]


class QuestionsForNewPlayer(Enum):
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
        self.players = []

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

        return json.dumps(dictToFix, sort_keys=False)

    def _getPlayerById(self, id):
        for player in self.players:
            if player.data['id'] == id:
                return player
        raise PlayerNotFound(f"NO PLAYER WITH ID: {id}")

    def _validateInput(self, input, inputType):
        if inputType == InputType.NAME:
            return self._validateName(input)
        elif inputType == InputType.POSITIVE_INT:
            return self._validatePositiveInt(input)

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
            response = {
                "status": "FAILURE", "message": f"INVALID INPUT: {givenInput} FOR TYPE: {inputType}"
            }
            return self._reformatJson(response)

        return self._reformatJson({"status": "SUCCESS"})

    def getPlayerById(self, data):
        player = self._getPlayerById(data['id'])
        return self._reformatJson(player.data)

    def _reformatTime(self, hour):
        return str(hour).zfill(2) + ":00"

    def createNewPlayer(self, playerData):
        self._validatePlayer(answers=playerData)
        player = Player(playerData)
        print(f"NEW PLAYER CREATED: {player.data['id']}")
        self.players.append(player)
        return self._reformatJson({
            "status": "SUCCESS",
            "playerId": player.data["id"],
            "name": player.data["name"],
            "time": self._reformatTime(player.data["time_of_the_day"])
        })

    def getRelevantMenu(self, body):
        currentPlayer = self._getPlayerById(body['playerId'])
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
        currentPlayer = self._getPlayerById(body['playerId'])
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
