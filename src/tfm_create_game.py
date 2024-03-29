"""reate a connection to Board Game Arena and interact with it."""
import json
import logging
from logging.handlers import RotatingFileHandler
import random
import re
import shlex

import aiohttp
from creds_iface import get_discord_id
from discord_utils import send_table_embed
from utils import is_url
from utils import send_help

logging.getLogger("aiohttp").setLevel(logging.WARN)

LOG_FILENAME = "errs"
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(LOG_FILENAME, maxBytes=10000000, backupCount=0)
formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


{
    "randomMA": "Full random",
}


AVAILABLE_TFM_OPTIONS = [
    "customCorporationsList",
    "customColoniesList",
    "cardsBlackList",
    "color",
    "seed",
    "board",
    "players",
    "corporateEra",
    "communityCardsOption",
    "prelude",
    "venusNext",
    "includeVenusMA",
    "colonies",
    "turmoil",
    "promoCardsOption",
    "fastModeOption",
    "undoOption",
    "randomMA",  # Options are "Full random", "Limited synergy", or "No randomization"
    "removeNegativeGlobalEventsOption",
    "draftVariant",
    "showOtherPlayersVP",
    "solarPhaseOption",
    "soloTR",
    "initialDraft",
    "shuffleMapOption",
    "startingCorporations",
    "beginnerOption",
    "handicap",
    "randomFirstPlayer",
    "aresExtension",
    "moonExpansion",
    "showTimers",
    "requiresVenusTrackCompletion",
    "requiresMoonTrackCompletion",
    "moonStandardProjectVariant",
    "altVenusBoard",
]


class TFMPlayer:
    def __init__(self, player_name, colors, options):
        self.name = player_name
        self.colors = [c.lower() for c in colors]
        # options is a string of chars that are each an opt
        self.options = options.lower()


class TFMGame:
    """Account user/pass and methods to login/create games with it."""

    def __init__(self, server):
        self.session = aiohttp.ClientSession()
        self.base_url = server
        self.table_id = 0
        self.created_player_list = []

    async def put_data(self, url, params):
        """Put data."""
        params_str = json.dumps(params)
        logger.info(f"\nTFM PUT:{url}, with params:" + params_str)
        async with self.session.put(url, data=params_str) as response:
            resp_text = await response.text()
            return resp_text

    async def generate_shared_params(self, global_opts, players):
        """Generate the shared options where global opts override and
        options that are shared between all players are added."""
        logger.debug("Starting param generation")

        def choose_option(gl, pl, letter):
            """If it's in global_opts, override player opts. If it's in all player opts, then choose it."""
            return letter in gl or all([letter in p.options for p in pl])

        special_params = {
            "customCorporationsList": [],
            "customColoniesList": [],
            "cardsBlackList": [],
            "seed": random.random(),
        }
        boards = {"r": "random official", "h": "hellas", "e": "elysium", "t": "tharsis"}
        if "b" in global_opts:
            b_pos = global_opts.index("b")
            board_letter = global_opts[b_pos + 1]
            special_params["board"] = boards[board_letter]
        elif "b" in all(["b" in p.options for p in players]):
            # Use player 0 arbitrarily because they are all the same
            b_pos = players[0].index("b")
            board_letter = players[0].options[b_pos + 1]
            special_params["board"] = boards[board_letter]
        else:
            special_params["board"] = "random"

        params = {
            "players": [],
            # Expansions
            "corporateEra": choose_option(global_opts, players, "e"),
            "communityCardsOption": choose_option(global_opts, players, "g"),
            "prelude": choose_option(global_opts, players, "p"),
            "venusNext": choose_option(global_opts, players, "v"),
            "includeVenusMA": choose_option(global_opts, players, "v"),
            "colonies": choose_option(global_opts, players, "c"),
            "turmoil": choose_option(global_opts, players, "t"),
            "promoCardsOption": choose_option(global_opts, players, "o"),
            # Options
            "fastModeOption": choose_option(global_opts, players, "f"),
            "undoOption": choose_option(global_opts, players, "u"),
            "randomMA": choose_option(global_opts, players, "r"),
            "removeNegativeGlobalEventsOption": choose_option(
                global_opts,
                players,
                "n",
            ),  # Will only work if turmoil is also selected
            "draftVariant": choose_option(global_opts, players, "d"),
            "showOtherPlayersVP": choose_option(global_opts, players, "s"),
            "solarPhaseOption": choose_option(global_opts, players, "w"),
            "soloTR": choose_option(global_opts, players, "l"),
            "initialDraft": choose_option(global_opts, players, "i"),
            "shuffleMapOption": choose_option(global_opts, players, "m"),
            # "randomFirstPlayer",
            # "aresExtension",
            # "moonExpansion",
            # "showTimers",
            # "requiresVenusTrackCompletion",
            # "requiresMoonTrackCompletion",
            # "moonStandardProjectVariant",
            # "altVenusBoard"
        }

        # default to 2 corporations
        special_params["startingCorporations"] = "2"
        if "a" in global_opts:  # num_corps should be >=1, <=6
            a_pos = global_opts.index("a")
            num_corps = global_opts[a_pos + 1]
            if num_corps.isdigit():
                special_params["startingCorporations"] = num_corps
        elif "a" in all(["a" in p.options for p in players]):
            a_pos = players[0].index("a")
            num_corps = players[0][a_pos + 1]
            if num_corps.isdigit():
                special_params["startingCorporations"] = num_corps

        params.update(special_params)
        used_colors = []
        color_mapping = {
            "r": "red",
            "y": "yellow",
            "g": "green",
            "b": "blue",
            "p": "purple",
            "k": "black",
        }
        avail_colors = ["red", "yellow", "green", "blue", "purple", "black"]
        for i in range(len(players)):
            player = players[i]
            player_color = ""
            for color_letter in player.colors:
                color = color_mapping[color_letter]
                if color in avail_colors:
                    player_color = color
                    avail_colors.remove(color)
                    used_colors.append(color)
                    break
            if player_color == "":
                player_color = avail_colors[0]
                avail_colors.remove(player_color)
                used_colors.append(player_color)
            new_player = {
                "index": i + 1,  # their player array is 1-indexed
                "name": player.name,
                "color": player_color,
                "beginner": False,
                "handicap": 0,
                "first": i == 0,
            }
            params["players"].append(new_player)
        logger.debug("Param generation completed:" + str(params))
        return params

    async def create_table(self, params):
        """Create a table and return its url."""
        # /new-game is for the gui, but /game is for game creation and an API endpoint
        url = self.base_url + "/game"
        resp = await self.put_data(url, params)
        logger.debug("Received response:" + str(resp))
        resp_json = json.loads(resp)
        self.table_id = resp_json["id"]
        # To create the player links that are sent to everyone, Use /player?id=<ID>
        self.created_player_list = [
            {
                "name": player["name"],
                "color": player["color"],
                "player_id": player["id"],
                "player_link": self.base_url + "/player?id=" + player["id"],
            }
            for player in resp_json["players"]
        ]
        return self.created_player_list

    async def create_table_url(self, table_id):
        """Given the table id, make the table url."""
        return self.base_url + "/game?id=" + str(table_id)

    async def close_connection(self):
        """Close the connection. aiohttp complains otherwise."""
        await self.session.close()


async def init_tfm_game(message):
    """Format of message is !tfm +cpv player1;bgy;urd.
    See the help message for more info."""
    args = shlex.split(message.content)
    global_opts = ""
    server = "https://mars.ross.gg"  # default but can be changed by adding a url to the command
    players = []
    if len(args) == 1:
        await message.author.send("No command entered! Showing the help for !tfm.")
        await send_help(message, "tfm_help")
        return
    for arg in args[1:]:
        if arg[0] == "+":
            global_opts = arg[1:]
            continue
        if is_url(arg):
            server = arg
            continue
        logger.debug(f"Parsing arg `{arg}`")
        all_args = arg.split(";")
        if len(all_args) == 2:
            name, colors = all_args
            opts = ""
        elif len(all_args) == 3:
            name, colors, opts = all_args
        else:
            await message.author.send(f"Too many semicolons in player string {arg} (expected 2-3)!")
            return
        if not re.match("[rygbpk]+", colors):
            await message.author.send(f"Color in {colors} for player {name} is not valid.")
            return
        if not re.match("[23456abcdefghilmnoprstuvw]*", opts):
            await message.author.send(f"Opt in {opts} for player {name} is not valid.")
            return
        new_player = TFMPlayer(name, colors, opts)
        players.append(new_player)
    game = TFMGame(server)
    options = await game.generate_shared_params(global_opts, players)
    data = await game.create_table(options)
    player_lines = []
    i = 1
    for player in data:
        color_circle = f":{player['color']}_circle:"
        player_str = player["name"]
        discord_id = get_discord_id(player_str, message)
        if discord_id != -1:
            player_str = f"<@!{discord_id}>"
        player_line = f"**{i} {color_circle}** {player_str}\t [Link to Game]({player['player_link']})"
        player_lines.append(player_line)
        i += 1
    author_line = ""  # It's not as important to have a game creator - the bot is the game creator
    player_list_str = "\n".join(player_lines)
    options_str = ""
    option_names = list(options.keys())
    option_names.sort()
    # The following is a kludge to create a table inside an embed with ~ tabs
    # Use discord number to create a number like :three:
    numbers = {"2": "two", "3": "three", "4": "four", "5": "five", "6": "six"}
    number = numbers[str(options["startingCorporations"])]
    truncated_opts_str = "*Complete options sent to game creator*\n\n　:{}: `{:<20}`".format(number, "Corporations")
    expansions = [
        "colonies",
        "communityCardsOption",
        "corporateEra",
        "prelude",
        "promoCardsOption",
        "turmoil",
        "venusNext",
    ]
    ith = 1
    for expn in expansions:
        short_expn = expn.replace("CardsOption", "")
        if options[expn]:
            truncated_opts_str += "　:white_check_mark:`{:<20}`".format(short_expn)
        else:
            truncated_opts_str += "　:x:`{:<20}`".format(short_expn)
        ith += 1
        if ith % 2 == 0:
            truncated_opts_str += "\n"  # should be a 2row 3col table
    for key in option_names:
        if key != "players":
            options_str += f"{key}   =   {options[key]}\n"
    await send_table_embed(
        message,
        "Terraforming Mars",
        f"Running on server {server}",
        author_line,
        player_list_str,
        "Options",
        truncated_opts_str,
    )
    await message.author.send(f"**Created game with these options**\n\n```{options_str}```")
    await game.close_connection()
