"""reate a connection to Board Game Arena and interact with it."""
import json
import re
import time
import urllib.parse
import random

import aiohttp

class TFMPlayer:
    def __init__(self, player_name, colors, options):
        self.name = player_name
        self.colors = [c.lower() for c in colors]
        # options is a string of chars that are each an opt
        self.options = options.lower()

class TFMGame:
    """Account user/pass and methods to login/create games with it."""
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.base_url = "https://terraforming-mars.herokuapp.com"
        self.table_id = 0
        self.created_player_list = []

    async def put_data(self, url, params):
        """Put data."""
        params_str = json.dumps(params)
        logger.info("\nTFM PUT:", url, "with params", params_str)
        async with self.session.put(url, data=params_str) as response:
            resp_text = await response.text()
            return resp_text

    async def generate_shared_params(self, global_opts, players):
        """Generate the shared options where global opts override and
        options that are shared between all players are added."""
        def choose_option(gl, pl, letter):
            """If it's in global_opts, override player opts. If it's in all player opts, then choose it."""
            return letter in gl or all([letter in p.options for p in pl])
        params = {
          "players": [],
          # Expansions
          "corporateEra": choose_option(global_opts, players, "e"),
          "prelude": choose_option(global_opts, players, "p"),
          "venusNext": choose_option(global_opts, players, "v"),
          "includeVenusMA": choose_option(global_opts, players, "v"),
          "colonies": choose_option(global_opts, players, "c"),
          "turmoil": choose_option(global_opts, players, "t"),
          "promoCardsOption": choose_option(global_opts, players, "o"),

          # Options
          "undoOption": choose_option(global_opts, players, "u"),
          "randomMA": choose_option(global_opts, players, "r"),
          "draftVariant": choose_option(global_opts, players, "d"),
          "showOtherPlayersVP": choose_option(global_opts, players, "s"),
          "solarPhaseOption": choose_option(global_opts, players, "w"),
          "soloTR": choose_option(global_opts, players, "l"),
          "initialDraft": choose_option(global_opts, players, "i"),
          "shuffleMapOption": choose_option(global_opts, players, "m"),
        }
        special_params = {
          "customCorporationsList": [],
          "customColoniesList": [],
          "seed": random.random(),
        }
        if "a" in global_opts:  # num_corps should be >=1, <=6
            a_pos = global_opts.index("a")
            num_corps = global_opts[a_pos+1]
            special_params["startingCorporations"] = num_corps
        elif "a" in all(["a" in p.options for p in players]):
            a_pos = players[0].index("a")
            num_corps = players[0][a_pos+1]
            special_params["startingCorporations"] = num_corps
        else:
            special_params["startingCorporations"] = "2"
        boards = {"r":"random", "h":"hellas", "e":"elysium", "t":"tharsis"}
        if "b" in global_opts:
            b_pos = global_opts.index("b")
            board_letter = global_opts[b_pos+1]
            special_params["board"] = boards[board_letter]
        elif "b" in all(["b" in p.options for p in players]):
            # Use player 0 arbitrarily because they are all the same
            b_pos = players[0].index("b")
            board_letter = players[0].options[b_pos+1]
            special_params["board"] = boards[board_letter]
        else:
            special_params["board"] = "random"
        params.update(special_params)
        used_colors = []
        color_mapping = {"r": "red", "y": "yellow", "g": "green", "b": "blue", "p": "purple", "k": "black"}
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
                "index": i+1, # their player array is 1-indexed
                "name": player.name,
                "color": player_color,
                "beginner": False,
                "handicap": 0,
                "first": i==0
              }
            params["players"].append(new_player)
        return params

    async def create_table(self, params):
        """Create a table and return its url."""
        # /new-game is for the gui, but /game is for game creation and an API endpoint
        url = self.base_url + "/game"
        resp = await self.put_data(url, params)
        logger.debug("Received response", resp)
        resp_json = json.loads(resp)
        self.table_id = resp_json["id"]
        # To create the player links that are sent to everyone, Use /player?id=<ID>
        self.created_player_list = [
            {
                "name":        player["name"],
                "color":       player["color"],
                "player_id":   player["id"],
                "player_link": self.base_url + "/player?id=" + player["id"]
            } for player in resp_json["players"]
        ]
        return self.created_player_list

    async def create_table_url(self, table_id):
        """Given the table id, make the table url."""
        return self.base_url + "/game?id=" + str(table_id)

    async def close_connection(self):
        """Close the connection. aiohttp complains otherwise."""
        await self.session.close()
