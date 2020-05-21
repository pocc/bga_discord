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
    def __init__(self):
        self.session = aiohttp.ClientSession()

    async def fetch(self, url):
        """Generic get."""
        async with self.session.get(url) as response:
            return await response.text()

    async def post(self, url, params):
        """Generic post."""
        await self.session.post(url, data=params)

    async def login(self, username, password):
        """Login to BGA provided the username/password. The session will
        now have cookies to use for privileged actions."""
        url = "https://en.boardgamearena.com/account/account/login.html"
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
        url = "https://boardgamearena.com/player"
        resp = await self.fetch(url)
        # Some version of "You are playing" or "Playing now at:"
        matches = re.search(r"[Pp]laying[^<]*<a href=\"\/table\?table=(\d+)", resp)
        if matches is not None:
            table_id = matches[1]
            print("Quitting table", table_id)
            quit_url = "https://boardgamearena.com/table/table/quitgame.html"
            params = {
                "table": table_id,
                "neutralized": "true",
                "s": "table_quitgame",
                "dojo.preventCache": str(int(time.time()))
            }
            quit_url += "?" + urllib.parse.urlencode(params)
            await self.fetch(quit_url)

    async def create_table(self, game_name, players):
        """Create a table and return its url."""
        lower_game_name = game_name.lower()
        if not isinstance(players, list):
            raise ValueError("Players needs to be a list, not a string")
        await self.quit_table()
        games = await get_game_list()
        lower_games = {}
        for game in games:
            lower_games[game.lower()] = games[game]
        if lower_game_name not in lower_games.keys():
            return game_name + " is not a known BGA game"
        game_id = lower_games[lower_game_name]
        url = "https://boardgamearena.com/table/table/createnew.html"
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
        # Set table to normal mode
        await self.set_option(table_id, 201, 0)
        # Set table to no time limit
        await self.set_option(table_id, 200, 20)
        for player in players:
            player_id = await self.get_player_id(player)
            await self.invite_player(table_id, player_id)
        return "https://boardgamearena.com/table?table=" + str(table_id)

    async def verify_privileged(self):
        """Verify that the user is logged in by accessing a url they should have access to."""
        community_text = await self.fetch("https://boardgamearena.com/community")
        return "You must be logged in to see this page." not in community_text

    async def get_player_id(self, player):
        """Given the name of a player, get their player id."""
        url = "https://boardgamearena.com/player/player/findplayer.html"
        params = {
            "q": player,
            "start": 0,
            "count": "Infinity"
        }
        url += "?" + urllib.parse.urlencode(params)
        resp = await self.fetch(url)
        resp_json = json.loads(resp)
        if len(resp_json) == 0:
            raise IOError("No player by that name!")
        return resp_json["items"][0]["id"]

    async def invite_player(self, table_id, player_id):
        """Invite a player to a table you are creating."""
        url = "https://boardgamearena.com/table/table/invitePlayer.html"
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

    async def set_option(self, table_id, option, value):
        """Change the game options for the specified."""
        url = "https://boardgamearena.com/table/table/changeoption.html"
        params = {
            "table": table_id,
            "id": option,
            "value": value,
            "dojo.preventCache": str(int(time.time()))
        }
        url += "?" + urllib.parse.urlencode(params)
        await self.fetch(url)

    async def close_connection(self):
        """Close the connection. aiohttp complains otherwise."""
        await self.session.close()
