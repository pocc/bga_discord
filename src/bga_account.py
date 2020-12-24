"""Create a connection to Board Game Arena and interact with it."""
import json
import logging
from logging.handlers import RotatingFileHandler
import re
import time
import urllib.parse

import aiohttp
from bga_game_list import get_game_list

logging.getLogger("aiohttp").setLevel(logging.WARN)

LOG_FILENAME = "errs"
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(LOG_FILENAME, maxBytes=10000000, backupCount=0)
formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


MODE_TYPES = {
    "normal": 0,
    "training": 1,
}
MODE_VALUES = list(MODE_TYPES.keys())
SPEED_TYPES = {
    "fast": 0,
    "normal": 1,
    "slow": 2,
    "24/day": 10,
    "12/day": 11,
    "8/day": 12,
    "4/day": 13,
    "3/day": 14,
    "2/day": 15,
    "1/day": 17,
    "1/2days": 19,
    "nolimit": 20,
}
SPEED_VALUES = list(SPEED_TYPES.keys())
KARMA_TYPES = {"0": 0, "50": 1, "65": 2, "75": 3, "85": 4}
KARMA_VALUES = list(KARMA_TYPES.keys())
LEVEL_VALUES = [
    "beginner",
    "apprentice",
    "average",
    "good",
    "strong",
    "expert",
    "master",
]


class BGAAccount:
    """Account user/pass and methods to login/create games with it."""

    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.base_url = "https://boardgamearena.com"

    async def fetch(self, url):
        """Generic get."""
        logger.debug("\nGET: " + url)
        async with self.session.get(url) as response:
            resp_text = await response.text()
            if resp_text[0] in ["{", "["]:  # If it's a json
                print(f"Fetched {url}. Resp: " + resp_text[:80])
            return resp_text

    async def post(self, url, params):
        """Generic post."""
        logger.debug("LOGIN: " + url + "\nEMAIL: " + params["email"])
        async with self.session.post(url, data=params) as response:
            resp_text = await response.text()
            print(f"Posted {url}. Resp: " + resp_text[:80])

    async def login(self, username, password):
        """Login to BGA provided the username/password. The session will
        now have cookies to use for privileged actions."""
        url = self.base_url + "/account/account/login.html"
        params = {
            "email": username,
            "password": password,
            "rememberme": "on",
            "redirect": "join",
            "form_id": "loginform",
            "dojo.preventCache": str(int(time.time())),
        }
        await self.post(url, params)
        return await self.verify_privileged()

    async def logout(self):
        """Logout of current session."""
        url = self.base_url + "/account/account/logout.html"
        params = {"dojo.preventCache": str(int(time.time()))}
        url += "?" + urllib.parse.urlencode(params)
        await self.fetch(url)

    async def quit_table(self):
        """ Quit the table if the player is currently at one"""
        url = self.base_url + "/player"
        resp = await self.fetch(url)
        # Some version of "You are playing" or "Playing now at:"
        matches = re.search(r"[Pp]laying[^<]*<a href=\"\/table\?table=(\d+)", resp)
        if matches is not None:
            table_id = matches[1]
            logger.debug("Quitting table" + str(table_id))
            quit_url = self.base_url + "/table/table/quitgame.html"
            params = {
                "table": table_id,
                "neutralized": "true",
                "s": "table_quitgame",
                "dojo.preventCache": str(int(time.time())),
            }
            quit_url += "?" + urllib.parse.urlencode(params)
            await self.fetch(quit_url)

    async def quit_playing_with_friends(self):
        """There is a BGA feature called "playing with friends". Remove friends from the session"""
        quit_url = self.base_url + "/group/group/removeAllFromGameSession.html"
        params = {"dojo.preventCache": str(int(time.time()))}
        quit_url += "?" + urllib.parse.urlencode(params)
        await self.fetch(quit_url)

    async def create_table(self, game_name_part):
        """Create a table and return its url. 201,0 is to set to normal mode.
        Partial game names are ok, like race for raceforthegalaxy.
        Returns (table id (int), error string (str))"""
        # Try to close any logged-in session gracefully
        lower_game_name = re.sub(r"[^a-z0-9]", "", game_name_part.lower())
        await self.quit_table()
        await self.quit_playing_with_friends()
        games, err_msg = await get_game_list()
        if len(err_msg) > 0:
            return -1, err_msg
        lower_games = {}
        for game in games:
            lower_name = re.sub(r"[^a-z0-9]", "", game.lower())
            lower_games[lower_name] = games[game]
        # If name is unique like "race" for "raceforthegalaxy", use that
        games_found = []
        game_name = ""
        for game_i in list(lower_games.keys()):
            if game_i == lower_game_name:  # if there's an exact match, take it!
                game_name = lower_game_name
            elif game_i.startswith(lower_game_name):
                games_found.append(game_i)
        if len(game_name) == 0:
            if len(games_found) == 0:
                err = (
                    f"`{lower_game_name}` is not available on BGA. Check your spelling "
                    f"(capitalization and special characters do not matter)."
                )
                return -1, err
            elif len(games_found) > 1:
                err = f"`{lower_game_name}` matches [{','.join(games_found)}]. Use more letters to match."
                return -1, err
            game_name = games_found[0]
        game_id = lower_games[game_name]
        url = self.base_url + "/table/table/createnew.html"
        params = {
            "game": game_id,
            "gamemode": "async",
            "forceManual": "true",
            "is_meeting": "false",
            "dojo.preventCache": str(int(time.time())),
        }
        url += "?" + urllib.parse.urlencode(params)
        resp = await self.fetch(url)
        try:
            resp_json = json.loads(resp)
        except json.decoder.JSONDecodeError:
            logger.error("Unable to decode response json:" + resp)
            return -1, "Unable to parse JSON from Board Game Arena."
        if resp_json["status"] == "0":
            err = resp_json["error"]
            if err.startswith("You have a game in progress"):
                matches = re.match(r"(^[\w !]*)[^\/]*([^\"]*)", err)
                err = matches[1] + "Quit this game first (1 realtime game at a time): " + self.base_url + matches[2]
            return -1, err
        table_id = resp_json["data"]["table"]
        return table_id, ""

    async def set_table_options(self, options, table_id):
        url_data = await self.parse_options(options, table_id)
        if isinstance(url_data, str):  # In this case it's an error
            return url_data
        logger.debug("Got url data :" + str(url_data))
        for url_datum in url_data:
            await self.set_option(table_id, url_datum["path"], url_datum["params"])

    async def set_option(self, table_id, path, params):
        """Change the game options for the specified."""
        url = self.base_url + path
        params.update({"table": table_id, "dojo.preventCache": str(int(time.time()))})
        url += "?" + urllib.parse.urlencode(params)
        await self.fetch(url)

    async def parse_options(self, options, table_id):
        """Create url data that can be parsed as urls"""
        # Set defaults if they're not present
        defaults = {
            "mode": "normal",
            "presentation": "Made by discord BGA bot (github.com/pocc/bga_discord)",
        }
        # options will overwrite defaults if they are there
        defaults.update(options)
        updated_options = defaults

        if "open" not in updated_options \
           and "restrictgroup" in updated_options:
            updated_options["open"] = "true"

        url_data = []
        final_url_data = []
        for option in updated_options:
            value = updated_options[option]
            option_data = {}
            logger.debug(f"Reading option `{option}` with key `{value}`")
            if option == "mode":
                option_data["path"] = "/table/table/changeoption.html"
                mode_name = updated_options[option]
                if mode_name not in list(MODE_TYPES.keys()):
                    return f"Valid modes are training and normal. You entered {mode_name}."
                mode_id = MODE_TYPES[mode_name]
                option_data["params"] = {"id": 201, "value": mode_id}
            elif option == "speed":
                option_data["path"] = "/table/table/changeoption.html"
                speed_name = updated_options[option]
                if speed_name not in list(SPEED_TYPES.keys()):
                    return f"{speed_name} is not a valid speed. Check !bga options."
                speed_id = SPEED_TYPES[speed_name]
                option_data["params"] = {"id": 200, "value": speed_id}
            elif option == "minrep":
                option_data["path"] = "/table/table/changeTableAccessReputation.html"
                if value not in list(KARMA_TYPES.keys()):
                    return f"Invalid minimum karma {value}. Valid values are 0, 50, 65, 75, 85."
                option_data["params"] = {"karma": KARMA_TYPES[value]}
            elif option == "presentation":
                # No error checking is necessary as every string is valid.
                option_data["path"] = "/table/table/setpresentation.html"
                option_data["params"] = {"value": updated_options[option]}
            elif option == "levels":
                if "-" not in value:
                    return "levels requires a dash between levels like `good-strong`."
                [min_level, max_level] = value.lower().split("-")
                if min_level not in LEVEL_VALUES:
                    return f"Min level {min_level} is not a valid level ({','.join(LEVEL_VALUES)})"
                if max_level not in LEVEL_VALUES:
                    return f"Max level {max_level} is not a valid level ({','.join(LEVEL_VALUES)})"
                level_enum = {LEVEL_VALUES[i]: i for i in range(len(LEVEL_VALUES))}
                min_level_num = level_enum[min_level]
                max_level_num = level_enum[max_level]
                level_keys = {}
                for i in range(7):
                    if min_level_num <= i <= max_level_num:
                        level_keys["level" + str(i)] = "true"
                    else:
                        level_keys["level" + str(i)] = "false"
                option_data["path"] = "/table/table/changeTableAccessLevel.html"
                option_data["params"] = level_keys
            elif option == "players":
                # Change minimum and maximum number of players
                option_data["path"] = "/table/table/changeWantedPlayers.html"
                [minp, maxp] = updated_options[option].split("-")
                option_data["params"] = {"minp": minp, "maxp": maxp}
            elif option == "restrictgroup":
                option_data["path"] = "/table/table/restrictToGroup.html"
                group_options = await self.get_group_options(table_id)
                group_id = -1
                for group_o in group_options:
                    if group_o[1].startswith(value):
                        group_id = group_o[0]
                if group_id != -1:
                    option_data["params"] = {"group": group_id}
                else:
                    groups_str = "[`" + "`,`".join([g[1] for g in group_options if g[1] != "-"]) + "`]"
                    return f"Unable to find group {value}. You are a member of groups {groups_str}."
            elif option == "lang":
                option_data["path"] = "/table/table/restrictToLanguage.html"
                option_data["params"] = {"lang": updated_options[option]}
            elif option == "open":
                if updated_options["open"].lower() in {"1", "on", "true", "y", "yes"}:
                    option_data["path"] = "/table/table/openTableNow.html"
                    option_data["params"] = {}
                elif updated_options["open"].lower() in {"0", "off", "false", "n", "no"}:
                    continue
                else:
                    return f"Option `open` should have value `true` or `false`."
            elif option.isdigit():
                # If this is an HTML option, set it as such
                option_data["path"] = "/table/table/changeoption.html"
                option_data["params"] = {"id": option, "value": updated_options[option]}
            else:
                return f"Option {option} not a valid option."

            url_data.append(option_data)
        url_data.extend(final_url_data)
        return url_data

    async def get_group_id(self, group_name):
        """For BGA groups of people."""
        uri_vars = {"q": group_name, "start": 0, "count": "Infinity"}
        group_uri = urllib.parse.urlencode(uri_vars)
        full_url = self.base_url + f"/group/group/findgroup.html?{group_uri}"
        result_str = await self.fetch(full_url)
        result = json.loads(result_str)
        group_id = result["items"][0]["id"]  # Choose ID of first result
        logger.debug(f"Found {group_id} for group {group_name}")
        return group_id

    async def create_table_url(self, table_id):
        """Given the table id, make the table url."""
        return self.base_url + "/table?table=" + str(table_id)

    async def verify_privileged(self):
        """Verify that the user is logged in by accessing a url they should have access to."""
        community_text = await self.fetch(self.base_url + "/community")
        return "You must be logged in to see this page." not in community_text

    async def get_group_options(self, table_id):
        """The friend group id is unique to every user. Search the table HTML for it."""
        table_url = self.base_url + "/table?table=" + str(table_id)
        html_text = await self.fetch(table_url)
        restrict_group_select = re.search(r'<select id="restrictToGroup">([\s\S]*?)<\/select>', html_text)[0]
        options = re.findall(r'"(\d*)">([^<]*)', restrict_group_select)
        return options

    async def get_player_id(self, player):
        """Given the name of a player, get their player id."""
        url = self.base_url + "/player/player/findplayer.html"
        params = {"q": player, "start": 0, "count": "Infinity"}
        url += "?" + urllib.parse.urlencode(params)
        resp = await self.fetch(url)
        resp_json = json.loads(resp)
        if len(resp_json["items"]) == 0:
            return -1
        return resp_json["items"][0]["id"]

    async def invite_player(self, table_id, player_id):
        """Invite a player to a table you are creating."""
        url = self.base_url + "/table/table/invitePlayer.html"
        params = {
            "table": table_id,
            "player": player_id,
            "dojo.preventCache": str(int(time.time())),
        }
        url += "?" + urllib.parse.urlencode(params)
        resp = await self.fetch(url)
        resp_json = json.loads(resp)
        if "status" in resp_json:
            if resp_json["status"] == "0":
                return resp_json["error"]
            else:
                return ""
        else:
            raise IOError("Problem encountered: " + str(resp))

    async def add_friend(self, friend_name):
        friend_id = await self.get_player_id(friend_name)
        if friend_id == -1:
            return f"Player {friend_name} not found. Make sure they exist and check spelling."
        params = {"id": friend_id, "dojo.preventCache": str(int(time.time()))}
        path = "?" + urllib.parse.urlencode(params)
        await self.fetch(self.base_url + "/community/community/addToFriend.html" + path)

    async def get_tables(self, player_id):
        """Get all of the tables that a player is playing at. Tables are returned as json objects."""
        url = self.base_url + "/tablemanager/tablemanager/tableinfos.html"
        params = {"playerfilter": player_id, "dojo.preventCache": str(int(time.time()))}
        url += "?" + urllib.parse.urlencode(params)
        resp = await self.fetch(url)
        resp_json = json.loads(resp)
        return resp_json["data"]["tables"]

    async def get_table_metadata(self, table_data):
        """Get the numbure of moves and progress of the game as strings"""
        table_id = table_data["id"]
        game_server = table_data["gameserver"]
        game_name = table_data["game_name"]
        table_url = f"{self.base_url}/{game_server}/{game_name}?table={table_id}"
        resp = await self.fetch(table_url)
        game_progress_match = re.search('updateGameProgression":"([^"]*)"', resp)
        if game_progress_match:
            game_progress = game_progress_match[1]
        else:
            game_progress = ""
        num_moves_match = re.search('move_nbr":"([^"]*)"', resp)
        if num_moves_match:
            num_moves = num_moves_match[1]
        else:
            num_moves = ""
        return game_progress, num_moves, table_url

    async def open_table(self, table_id):
        """Function to open the table to other people for a specific table.
        You must have created the table to be able to use this function.
        example get url https://boardgamearena.com/table/table/openTableNow.html?table=121886720&dojo.preventCache=1604627527457
        """
        url = self.base_url + "/table/table/openTableNow.html"
        params = {"table": table_id, "dojo.preventCache": str(int(time.time()))}
        url += "?" + urllib.parse.urlencode(params)
        await self.fetch(url)

    async def close_connection(self):
        """Close the connection. aiohttp complains otherwise."""
        await self.session.close()
