# made by: rxzyx (rzx)
# provide credit when using!
# feel free to improve this by submitting a pull request!

from json import loads, dumps, JSONDecodeError
from asyncio import run, sleep as asleep, create_task, gather, CancelledError
from enum import Enum
from random import random, randint, choice
from inspect import isfunction
from requests import get, post, RequestException
from threading import Timer, Thread
from time import time
from websockets import connect
from typing import List, Dict, TypedDict, Union, Any, Optional

try:
    from aioconsole import ainput
except ImportError:
    print("aioconsole not installed! Using input.")
    ainput = input

HEADERS: dict = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/" + \
                  "537.36 (KHTML, like Gecko) Chrome/91.0 Safari/537.36",
    "Content-Type": "application/json"
}

API: str = "https://api.drawbattle.io/"
WSS_URI: str = "wss://ws.drawbattle.io/ws/?gameId={0}&userId={1}&userName={2}"

LOWERCASE_ALPHABET: str = "0123456789abcdefghijklmnopqrstuvwxyz"
INCLUDE_VALUES: list = ["all", "guesses"]
NAME_IDENTIFIER_ON: bool = True
CNAME_IDENTIFIER: str = "{create}:" # create name identifier
CURRENT_GAME: Optional[str] = None
using_console: bool = True
underscore_ping: bool = False
my_team: List[str] = []
spam_info: dict = {
    "active": False,
    "name": "",
    "length": 0
}
showdown_info: dict = {
    "index": 0,
    "team": 0,
    "active": False,
    "wordlist": []
}
current_info: dict = {
    "index": 0,
    "team": 0,
    "word": ""
}
game_info: dict = {}
template_funcs: Optional[list] = None
HELP_PAGE: str = '''
*Commands*

send_guess('guesshere') -> Sends a guess as the current user.
                           Params are guess, round_index, showdown
                                      (str)     (int)      (bool)
                           None need to be specified, guess is automatically
                           made to the correct answer.

force_start()           -> Forcibly starts the game.
                           
'''

def ord_suffix(n: int) -> str:
    if not isinstance(n, int):
        raise TypeError("Value `n` has to be an integer.")
    
    if n < 1:
        raise ValueError("Value `n` must be an integer above 0.")
    
    if 11 <= n % 100 <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd'][
            n % 10 if n % 10 in {1, 2, 3} else 0]
    
    return f"{n}{suffix}"


def random_str(length: int = 20) -> str:
    return ''.join(choice(LOWERCASE_ALPHABET) for _ in range(length))


def generate_userid() -> str:
    def base36_encode(num: Union[int, float]) -> str:
        if num == 0:
            return LOWERCASE_ALPHABET[0]
        base36 = []
        while num:
            num, remainder = divmod(num, 36)
            base36.append(LOWERCASE_ALPHABET[remainder])
        return ''.join(reversed(base36))
    
    random_int = int(random() * 1e18)
    random_base36 = base36_encode(random_int).ljust(12, '0')
    return random_base36

# eq to Math.random().toString(36).slice(2).padEnd(12, "0")
user_id: str = generate_userid()

class Team(TypedDict):
    name: str
    userIds: List[str]

class Settings(TypedDict):
    numRounds: int
    roundLengthSec: int
    hideWordLength: bool
    streamerMode: bool
    wordListId: int

class GameEvent(Enum):
    SessionStart = 1
    JoinGame = 2
    UserGuess = 3
    UpdateTeams = 4
    StartRound = 5
    UpdateUser = 6
    ReadyUp = 7
    WordChosen = 8
    UserLobbyDisconnect = 10
    UserDisconnect = 11
    UserReconnect = 12
    UpdateSettings = 14
    StartFinalRound = 15
    FinalRoundNextWord = 16
    CancelStartGame = 17
    CanvasOperation = 18
    UpdateFishbowlWords = 19

class SendEvent(Enum):
    UserGuess = 101
    StartGame = 102
    CancelStartGame = 103
    JoinTeam = 104
    UpdateUserName = 105
    UpdateSettings = 106
    ChooseWord = 107
    ReadyUp = 108
    CanvasOperation = 109
    SubmitFishbowlWords = 110
    ForceStartNextRound = 111

# Obsolete. Didn't realize this was SENT TO the user.
'''
def send_guess_template(guess: str = None,
                        round_index: Union[int, list] = None,
                        team: int = None, uid: str = None,
                        showdown: bool = None, ts: int = None):
    if not ts:
        ts = int(time() * 1000)

    if not uid:
        uid = user_id

    print(showdown_info)

    if showdown is None:
        showdown = showdown_info["active"]

    if not team:
        team = showdown_info["team"] if showdown else current_info["team"]

    if not round_index:
        round_index = showdown_info[
            "index"] if showdown else current_info["index"]

    if showdown and isinstance(round_index, int):
        round_index = [round_index]

    if not guess:
        guess = showdown_info['wordlist'][
            showdown_info['index']] if showdown else current_info["word"]

    return [
        GameEvent.UserGuess.value,
        round_index,
        team,
        {
            "userId": uid,
            "guess": guess,
            "timestamp": ts
        }
    ]
'''

def send_guess_template(guess: str = None,
                        round_index: Union[int, list] = None,
                        showdown: bool = None) -> dict:
    if showdown is None:
        showdown = showdown_info["active"]

    if not round_index:
        round_index = showdown_info[
            "index"] if showdown else current_info["index"]

    if showdown and isinstance(round_index, int):
        round_index = [round_index]

    if not guess:
        guess = showdown_info['wordlist'][
            showdown_info['index']] if showdown else current_info["word"]

    return [
        SendEvent.UserGuess.value,
        round_index,
        guess
    ]


def force_start_template(round_index: Union[int, list] = None,
                         showdown: bool = None) -> dict:

    if showdown is None:
        showdown = showdown_info["active"]

    if not round_index:
        round_index = showdown_info[
            "index"] if showdown else current_info["index"]

    if showdown and isinstance(round_index, int):
        round_index = [round_index]

    return [
        SendEvent.ForceStartNextRound.value,
        round_index
    ]


def create_game(wordListId: Optional[int] = None,
                streamerMode: Optional[str] = None) -> Dict[str, str]:
    global CURRENT_GAME

    data = {}
    if wordListId:
        wordListId = int(wordListId)
        data["wordListId"] = wordListId
    
    if streamerMode:
        streamerMode = str(streamerMode)
        data["streamerMode"] = streamerMode

    response = post(API + "games", json=data, headers=HEADERS)
    response.raise_for_status()
    
    game_data = response.json()
    
    if not game_data.get("gameId"):
        raise ValueError("`gameId` is missing from the response.")
    
    CURRENT_GAME = game_data["gameId"]
    
    return game_data
    

def fetch_game(gameid: str = CURRENT_GAME,
               include: str = "all") -> Dict[str, Union[str, List[Team],
                                                 Dict[str, Any], List[Any],
                                                 Settings]]:
    if not gameid:
        gameid = CURRENT_GAME or input("Enter the Game ID: ")
    
    if include not in INCLUDE_VALUES:
        raise ValueError(
            f"`{include}` is not a valid value for include. Instead," + \
            f" use the following: {' or '.join(INCLUDE_VALUES)}")

    response = get(API + "games/" + gameid, headers=HEADERS,
                      params={"include": include})
    response.raise_for_status()
    return response.json()


def get_template_functions():
    functions = []
    for name, obj in globals().items():
        if isfunction(obj) and name.endswith('_template'):
            functions.append(name.replace('_template', ''))
    return functions


async def get_input(w):
    global template_funcs

    while True:
        try:
            user_input = await ainput("cmd: ") # Enter to see messages
            parsed_input = user_input.replace("'", '"')
            matched_func = False

            if user_input.lower() == "help":
                print(HELP_PAGE)
            elif user_input.lower() == "quit":
                raise SystemExit

            for func in template_funcs:
                if func in parsed_input:
                    matched_func = True
                    parsed_input = parsed_input.replace(
                        func, func + "_template")
                    cmd_result = eval(parsed_input)
                    print(cmd_result)
                    await w.send(dumps(cmd_result))
                    # await w.recv()

            if not matched_func and parsed_input:
                parsed_input = eval(parsed_input)
        except Exception as e:
            print("An error occured evaluating your input:", e)


async def send_message(w):
    while True:
        try:
            await asleep(15)
            await w.send("_")
            # print("Message sent: _")
        except Exception as e:
            print(f"Error sending ping message: {e}")
            break


if __name__ == "__main__":
    template_funcs = get_template_functions()
    print("You are currently using @rxzyx's DrawBattle hack.")

    spam_info['active'] = input(
        "Spam mode? (yes/no): ").strip().lower() == 'yes'

    print(f"{'Spam' if spam_info['active'] else 'Normal'} mode is enabled.")

    using_console = input(
        "Enable console? (yes/no): ").strip().lower() != 'no'

    if spam_info['active'] and using_console:
        using_console = False
        print("Console disabled due to spam mode being enabled.")
    print(f"The console is {'enabled' if using_console else 'disabled'}.")

    CURRENT_GAME = input(
        "Enter the Game ID (enter to create): ") or create_game()['gameId']
    print("The game ID is", CURRENT_GAME)

    data = fetch_game(CURRENT_GAME)
    
    for team in data["teams"]:
        print(f"\n{team['name']}:")
        for uid in team["userIds"]:
            print(f"  {data['users'][uid]['name']} (User ID: {uid})")

    # For extreme naming cases, just do {create}:namehere to create a new one
    name = input("\nEnter your name to get your user ID (or a new name): ")
    uid = user_id
    if name and (not NAME_IDENTIFIER_ON or not name.startswith(
        CNAME_IDENTIFIER)):
        '''
        uid = next((data['users'][user_id]['id'] for team in data[
            "teams"] for user_id in team["userIds"] if data['users'][user_id][
                'name'
            ].lower() == name.lower()), None)'''
        matching_users = [
            data['users'][user_id] 
            for team in data["teams"] 
            for user_id in team["userIds"] 
            if data['users'][user_id]['name'].lower() == name.lower()
        ]

        if len(matching_users) > 1:
            exact_matches = [
                user for user in matching_users if user['name'] == name]

            if len(exact_matches) > 1:
                print(f"Multiple users found with the name '{name}':")
                for user in exact_matches:
                    print(f"ID: {user['id']} - Name: {user['name']}")

                user_choice = input("Please choose a user by ID: ").strip()

                chosen_user = next((
                    user for user in exact_matches if str(
                        user['id']) == user_choice), None)
                
                if chosen_user:
                    uid = chosen_user['id']
                else:
                    print("Invalid ID selected. No user selected.")
                    uid = None
            else:
                uid = exact_matches[0]['id']
        else:
            uid = matching_users[0]['id'] if matching_users else None
    elif NAME_IDENTIFIER_ON and name.startswith(CNAME_IDENTIFIER):
        name = name[len(CNAME_IDENTIFIER):]

    if not uid:
        uid = user_id
    user_id = uid
        
    print(f"User ID for {name}: {uid}" if uid else "User not found.")

    SPECTATE = input("Spectate? (yes/no): ").strip().lower() == 'yes'
    uri = WSS_URI.format(CURRENT_GAME, uid, name)
    if SPECTATE:
        uri += "&spectate=true"
    
    async def gamethread():
        global showdown_info, my_team, game_info, current_word, uri, uid, name

        if spam_info["active"]:
            if spam_info["name"]:
                name = f"{spam_info['name']}{randint(10**5, 10**6 - 1)}"
            else:
                name = random_str(spam_info["length"])
            uid = generate_userid()
            uri = WSS_URI.format(CURRENT_GAME, uid, name)

        async with connect(uri=uri, ping_interval=15, ping_timeout=60,
                           extra_headers=[("Cache-Control", "no-cache"),
                                          ("Pragma", "no-cache"),
                                          ("Accept-Encoding",
                                           "gzip, deflate, br, zstd"),
                                          ("Upgrade", "websocket"),
                                          ("User-Agent", HEADERS[
                                              "User-Agent"
                                          ])]) as w:
            # roomInfo = loads(await w.recv())[1]
            # print(roomInfo)

            if using_console:
                create_task(get_input(w))
            if underscore_ping:
                create_task(send_message(w)) # Not really needed...
                                             # We have a ping interval, but
                                             # it doesn't send an underscore.

            while True:
                try:
                    data = loads(await w.recv())
                    match data[0]:
                        case GameEvent.SessionStart.value:
                            if len(data) == 3:
                                game_info = data[1]
                                showdown_info['team'] = next((
                                    i for i, team in enumerate(
                                        game_info['teams']
                                    ) if uid in team['userIds']), -1)
                                my_team = game_info['teams'][showdown_info[
                                    'team']]['userIds']
                                if game_info.get('finalRound'):
                                    showdown_info = {
                                        'index': len(game_info[
                                            'finalRound'
                                        ]['teamStates'][showdown_info['team']]) - 1,
                                        'team': showdown_info['team'],
                                        'wordlist': game_info[
                                            'finalRound']['words'],
                                        'active': True
                                    }
                                elif game_info.get('currentRound'):
                                    if game_info['currentRound'].get('word'):
                                        current_info['word'] = game_info[
                                            'currentRound']['word']
                                    else:
                                        current_info['word'] = game_info[
                                            'currentRound']['wordChoices'][0]
                        case GameEvent.UserGuess.value:
                            if len(data) == 4:
                                if isinstance(data[1], list):
                                    if data[3]['userId'] in my_team:
                                        showdown_info['index'] = data[1][0]
                                        showdown_info['team'] = data[2]

                                        showdown_info['active'] = True
                                else:
                                    current_info['team'] = data[2]
                                    current_info["index"] = data[1]
                        case GameEvent.ReadyUp.value:
                            if len(data) == 3:
                                current_info["index"] = data[1]
                        case GameEvent.WordChosen.value:
                            if len(data) == 4:
                                pos_suffix = ord_suffix(data[1] + 1)
                                print(f"The {pos_suffix} value is {data[2]}")
                                current_info["word"] = data[2]
                        case GameEvent.StartRound.value:
                            if "wordChoices" in data[2]:
                                print("The word choices are", ' and '.join(
                                    data[2]["wordChoices"]))
                                current_info["word"] = data[2][
                                    "wordChoices"][0]
                        case GameEvent.StartFinalRound.value:
                            if len(data) == 2:
                                showdown_info['active'] = True
                                showdown_info['wordlist'] = data[1]['words']
                                print(f"The wordlist is: {data[1]['words']}")
                        case GameEvent.FinalRoundNextWord.value:
                            showdown_info['active'] = True
                            if len(data) == 4 and data[3][
                                'drawerId'
                            ] in my_team:
                                showdown_info['index'] = data[1]
                                showdown_info['team'] = data[2]
                                if data[3]['drawerId'] != uid:
                                    w_suffix = ord_suffix(data[1] + 1)
                                    current_shword = showdown_info[
                                        'wordlist'][showdown_info['index']]
                                    print(f"The word for the {w_suffix} " + \
                                          f"showdown is {current_shword}")

                except JSONDecodeError:
                    continue
        print("WebSocket closed")

    async def spam_users(num_bots: Optional[int] = None,
                         bot_name: Optional[str] = None,
                         bot_length: Optional[int] = None):
        global using_console, spam_info
        
        if using_console: # Might add a functionality that lets you interact
                          # with a specific bot, if you can then please do.
            using_console = False
            print("Defaulted `using_console` to False.")
            
        if not num_bots:
            try:
                num_bots = int(input(
                    "How many bots (as a number) would you like to put? "))
            except ValueError:
                num_bots = 20
                print("`num_bots` has to be in numeral form. Defaulted to 20.")

        if not bot_name:
            print("You can leave the bot name as blank to make it random.")
            print("By the way, the length of it is unrestricted :)")
            bot_name = input("What should the name of the bots be? ") # or None

            if not bot_name:
                try:
                    bot_length = int(input(
                        "What should the name length be? "))
                except ValueError:
                    bot_length = 20
                    print("`bot_length` has to be a number. Defaulted to 10.")
        spam_info["name"] = bot_name
        spam_info["length"] = bot_length

        tasks = []

        for i in range(1, num_bots + 1):
            task = create_task(
                gamethread()
            )
            tasks.append(task)
        try:
            await gather(*tasks)
        except CancelledError:
            print("One of the tasks was cancelled.")
        except Exception as e:
            print(f"An error occurred: {e}")
        

    def newthread():
        run(gamethread())

    if spam_info["active"]:
        run(spam_users())
        '''
        try:
            num_bots = int(input(
                "How many bots (as a number) would you like to put? "))
        except ValueError:
            num_bots = 20
            print("`num_bots` has to be in numeral form. Defaulted to 20.")
        
        for i in range(1, num_bots + 1):
            Thread(target=newthread).start()'''
    else:
        newthread()
