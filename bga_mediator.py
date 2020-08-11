"""Create a connection to Board Game Arena and interact with it."""
import json
import re
import time
import urllib.parse

import aiohttp


async def get_game_list():
    """Get the list of games and numbers BGA assigns to each game."""
    url = 'https://boardgamearena.com/gamelist?section=all'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
            results = re.findall(r"item_tag_\d+_(\d+)[\s\S]*?name\">\s+([^<>]*)\n", html)
            # Sorting games isn't necessary, but I prefer it
            results.sort(key=lambda x: x[1])
            games = {}
            for r in results:
                games[r[1]] = int(r[0])
            return games


class BGAAccount:
    """Account user/pass and methods to login/create games with it."""
    # Select numbers for changing options in a game
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.base_url = "https://boardgamearena.com"

    async def fetch(self, url):
        """Generic get."""
        print("\nGET:", url)
        async with self.session.get(url) as response:
            resp_text = await response.text()
            is_json = resp_text[0] in ["{", "["]
            if is_json:
                print("RET JSON: " + resp_text)
            return resp_text

    async def post(self, url, params):
        """Generic post."""
        print("LOGIN: " + url + "\nEMAIL: " + params["email"])
        await self.session.post(url, data=params)

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
            "dojo.preventCache": str(int(time.time()))
        }
        await self.post(url, params)
        return await self.verify_privileged()

    async def quit_table(self):
        """ Quit the table if the player is currently at one"""
        url = self.base_url + "/player"
        resp = await self.fetch(url)
        # Some version of "You are playing" or "Playing now at:"
        matches = re.search(r"[Pp]laying[^<]*<a href=\"\/table\?table=(\d+)", resp)
        if matches is not None:
            table_id = matches[1]
            print("Quitting table", table_id)
            quit_url = self.base_url + "/table/table/quitgame.html"
            params = {
                "table": table_id,
                "neutralized": "true",
                "s": "table_quitgame",
                "dojo.preventCache": str(int(time.time()))
            }
            quit_url += "?" + urllib.parse.urlencode(params)
            await self.fetch(quit_url)

    async def create_table(self, game_name, options):
        """Create a table and return its url. 201,0 is to set to normal mode."""
        lower_game_name = re.sub(r"[^a-z0-9]", "", game_name.lower())
        await self.quit_table()
        games = await get_game_list()
        lower_games = {}
        for game in games:
            lower_name = re.sub(r"[^a-z0-9]", "", game.lower())
            lower_games[lower_name] = games[game]
        if lower_game_name not in lower_games.keys():
            return -1
        game_id = lower_games[lower_game_name]
        url = self.base_url + "/table/table/createnew.html"
        params = {
            "game": game_id,
            "gamemode": "realtime",
            "forceManual": "true",
            "is_meeting": "false",
            "dojo.preventCache": str(int(time.time()))
        }
        url += "?" + urllib.parse.urlencode(params)
        resp = await self.fetch(url)
        resp_json = json.loads(resp)
        if resp_json["status"] == "0":
            raise IOError("Problem encountered: " + str(resp))
        table_id = resp_json["data"]["table"]
        # Give BGA time for table to populate
        # If mode isn't specified, choose normal
        url_data = await self.parse_options(options)
        #return -2  # error code for option error
        print("Got url data ", url_data)
        for url_datum in url_data:
            await self.set_option(table_id, url_datum["path"], url_datum["params"])
        return table_id

    async def set_option(self, table_id, path, params):
        """Change the game options for the specified."""
        url = self.base_url + path
        params.update({
            "table": table_id,
            "dojo.preventCache": str(int(time.time()))
        })
        url += "?" + urllib.parse.urlencode(params)
        await self.fetch(url)

    async def parse_options(self, options):
        """Create url data that can be parsed as urls"""
        # Set defaults if they're not present
        defaults = {
            "mode": "normal",
            "speed": "normal",
            "presentation": "🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥",
            "minrep": "75",
        }
        # options will overwrite defaults if they are there
        defaults.update(options)
        updated_options = defaults
        url_data = []
        for option in updated_options:
            value = updated_options[option]
            option_data = {}
            print(f"Reading option `{option}` with key `{value}`")
            if option == "mode":
                option_data["path"] = "/table/table/changeoption.html"
                mode_name = updated_options[option]
                mode_id = {"normal": 0, "training": 1}[mode_name]
                option_data["params"] = {
                  "id": 201,
                  "value": mode_id
                }
            elif option == "speed":
                option_data["path"] = "/table/table/changeoption.html"
                speed_name = updated_options[option]
                speed_id = {
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
                   }[speed_name]
                option_data["params"] = {
                  "id": 200,
                  "value": speed_id
                }
            elif option == "minrep":
                option_data["path"] = "/table/table/changeTableAccessReputation.html"  
                karma_number = {"0": 0, "50": 1, "65": 2, "75": 3, "85": 4}
                option_data["params"] = {"karma": karma_number[value]}
            elif option == "presentation":
                option_data["path"] = "/table/table/setpresentation.html"  
                option_data["params"] = {"value": updated_options[option]}
            elif option == "levels":
                level_enum = {
                    "beginner": 0,
                    "apprentice": 1,
                    "average": 2,
                    "good": 3,
                    "strong": 4,
                    "expert": 5,
                    "master": 6,
                }
                [min_level, max_level] = updated_options[option].lower().split('-')
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
            elif option == "players": # Change minimum and maximum number of players
                option_data["path"] = "/table/table/changeWantedPlayers.html"
                [minp, maxp] = updated_options[option].split('-')
                option_data["params"] = {"minp": minp, "maxp": maxp}
            elif option == "restrictgroup":
                option_data["path"] = "/table/table/restrictToGroup.html"
                group_id = await self.get_group_id(updated_options[option])
                option_data["params"] = {"group": group_id}
            elif option == "lang":
                option_data["path"] = "/table/table/restrictToLanguage.html"
                option_data["params"] = {"lang": updated_options[option]}
            else:
                print(f"Option {option} not found.")
                return KeyError  # Incorrect key
        
            url_data.append(option_data)
        return url_data
           
    async def get_group_id(self, group_name):
        uri_vars = {"q": group_name, "start": 0, "count": "Infinity"}
        group_uri = urllib.parse.urlencode(uri_vars)
        full_url = self.base_url + f"/group/group/findgroup.html?{group_uri}"
        result_str = await self.fetch(full_url)
        result = json.loads(result_str)
        group_id = result["items"][0]["id"]  # Choose ID of first result
        print(f"Found {group_id} for group {group_name}")
        return group_id
    
    async def create_table_url(self, table_id):
        """Given the table id, make the table url."""
        return self.base_url + "/table?table=" + str(table_id)

    async def verify_privileged(self):
        """Verify that the user is logged in by accessing a url they should have access to."""
        community_text = await self.fetch(self.base_url + "/community")
        return "You must be logged in to see this page." not in community_text

    async def get_player_id(self, player):
        """Given the name of a player, get their player id."""
        url = self.base_url + "/player/player/findplayer.html"
        params = {
            "q": player,
            "start": 0,
            "count": "Infinity"
        }
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
            "dojo.preventCache": str(int(time.time()))
        }
        url += "?" + urllib.parse.urlencode(params)
        resp = await self.fetch(url)
        resp_json = json.loads(resp)
        if resp_json["status"] == "0":
            raise IOError("Problem encountered: " + str(resp))


    async def close_connection(self):
        """Close the connection. aiohttp complains otherwise."""
        await self.session.close()
