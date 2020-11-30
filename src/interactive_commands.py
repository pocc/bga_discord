"""Interact with the bot if you are missing options in your command.

This works by changing the global `contexts` for a discord user for every message they send.
Each message that is meaningful to the bot will change the context.
Each different context will route them to the appropriate location.
"""
import time

from discord_utils import send_options_embed, send_simple_embed
from bga_game_list import get_game_list
from bga_create_game import setup_bga_game
from tfm_create_game import AVAILABLE_TFM_OPTIONS
from utils import normalize_name


GAME_OPTIONS = ["Add a player", "Change a game option", "Change target channel for embed", "Finish and create game"]


async def trigger_interactive_response(message, contexts, curr_ctx):
    """Interactive way to get input.

    Setup:
        Check for BGA username: Ask for BGA username if none found
        Show current settings (and show options):
            1. Set Board Game Arena password
            2. Set Board Game Arena default options
            3. Set Terraforming Mars default options
    Play:
        if args == 1: ask for game;
        if args == 2: ask for player/option;
        player/option:
            These are the current players and settings for the game
            <...>

            1. Add a player
            2. Change a game setting
            3. Change destination channel of embed
            4. Done
    Tables:
        Show current settings (and show options):
            1. Add a game (optional)
            2. Add a player (optional)
            3. Done
    """
    author = str(message.author)
    if message.content.startswith("cancel"):
        # quit current interactive session
        await message.channel.send("Canceled operation")
        contexts[author] = {}
        return
    if curr_ctx == "choose subprogram" and message.content.isdigit() and 1 <= int(message.content) <= 4:
        curr_ctx = ["setup", "play", "tables"][int(message.content) - 1]
    if curr_ctx in ["setup", "play", "tables"] or author not in contexts:
        contexts[author] = {"context": curr_ctx, "timestamp": time.time(), "channel": message.channel}
        in_thirty_sec_window = True
    else:
        in_thirty_sec_window = contexts[author]["timestamp"] > time.time() - 30
    if in_thirty_sec_window:
        contexts[author]["timestamp"] = time.time()  # reset timer
        if curr_ctx == "timeout":
            await send_options_embed(message, "BGA bot option", ["setup", "play", "tables"])
            contexts[author]["context"] = "choose subprogram"
        elif curr_ctx == "setup":
            if message.content.contains("1"):
                contexts[author]["context"] = "bga password"
                await send_options_embed(message, "password", [])
            elif message.content.contains("2"):
                contexts[author]["context"] = "bga options"
                bga_options = [
                    "Mode",
                    "Speed",
                    "Minrep",
                    "Presentation",
                    "Number of players",
                    "Min Level",
                    "Max Level",
                    "Restrict Group",
                    "Lang",
                ]
                await send_options_embed(message, "BGA option", bga_options)
            elif message.content.contains("3"):
                contexts[author]["context"] = "tfm options"
                await send_options_embed(message, "TFM option", AVAILABLE_TFM_OPTIONS)
        elif curr_ctx == "bga password":
            # Set password
            pass
        elif curr_ctx == "bga options":
            # set bga options
            pass
        elif curr_ctx == "tfm options":
            # set tfm options
            pass
        elif curr_ctx == "play":
            await send_simple_embed(message, "Enter the name of the game you want to play")
            contexts[author]["context"] = "choose game"
        elif curr_ctx == "choose game":
            contexts[author]["game"] = {}
            game_name = message.content
            normalized_name = normalize_name(game_name)
            games, errs = await get_game_list()
            if errs:
                await message.channel.send(errs)
                return
            normalized_bga_games = [normalize_name(game) for game in games]
            for bga_game in normalized_bga_games:
                if bga_game.startswith(normalized_name):
                    await send_options_embed(
                        message,
                        f"{game_name} game option",
                        GAME_OPTIONS,
                    )
                    contexts[author]["game"]["name"] = game_name
                    contexts[author]["context"] = "game option"
            if contexts[author] == "choose game":  # If no games of the same name were found
                await message.channel.send(f"Game `{game_name}` not found. Try again (or cancel to quit).")
        elif curr_ctx == "game option":
            if message.content.isdigit() and 1 <= int(message.content) <= len(GAME_OPTIONS):
                choice = int(message.content)
                contexts[author]["context"] = GAME_OPTIONS[choice - 1]
                contexts[author]["game"]["players"], contexts[author]["game"]["options"] = [], []
                title_opt = contexts[author]["context"]
                await send_options_embed(message, title_opt, [])
            else:
                await message.channel.send(f"Enter a number between 1 and {len(GAME_OPTIONS)}")
        elif curr_ctx == "Add a player":
            contexts[author]["game"]["players"].append(message.content)
            await message.channel.send("Added player " + message.content)
        elif curr_ctx == "Change a game option":
            contexts[author]["game"]["options"].append(message.content)
            await message.channel.send("Added option " + message.content)
        elif curr_ctx == "Change target channel for embed":
            contexts[author]["channel"] = message.content
        elif curr_ctx == "Finish and create game":
            game = contexts[author]["game"]["name"]
            players = contexts[author]["game"]["players"]
            options = contexts[author]["game"]["options"]
            await setup_bga_game(message, message.author.id, game, players, options)
        elif curr_ctx == "add current player to game":
            # add player to game
            pass
        elif "tables".startswith(curr_ctx):
            await message.channel.send("In context tables")
        else:
            await message.channel.send(
                "No interactive contexts found. Use !setup to setup your account, !play to start a game, and !tables to check the status of a game.",
            )
    else:
        await message.channel.send("Session ended because you waited too long (start over).")
