"""Interact with the bot if you are missing options in your command."""
import time

from discord_utils import send_options_embed, send_simple_embed
from bga_account import get_game_list
from tfm_game_generator import AVAILABLE_TFM_OPTIONS


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
    if curr_ctx in ["setup", "play", "tables"] or author not in contexts:
        contexts[author] = {"context": curr_ctx, "timestamp": time.time()}
        in_thirty_sec_window = True
    else:
        in_thirty_sec_window = contexts[author]["timestamp"] > time.time() - 30
    current_ctx = contexts[author]["context"]
    if in_thirty_sec_window:
        contexts[author]["timestamp"] = time.time()  # reset timer
        if current_ctx == "setup":
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
        elif current_ctx == "bga password":
            # Set password
            pass
        elif current_ctx == "bga options":
            # set bga options
            pass
        elif current_ctx == "tfm options":
            # set tfm options
            pass
        elif current_ctx == "play":
            await send_simple_embed(message, "Enter the name of the game you want to play")
            contexts[author]["context"] = "choose game"
        elif current_ctx == "choose game":
            game_name = message.content
            games, errs = await get_game_list()
            if errs:
                await message.channel.send(errs)
                return
            if game_name in games:
                await send_options_embed(
                    message,
                    "game option",
                    ["Add a player", "Change a game setting", "Change destination channel of embed", "Done"],
                )
                contexts[author]["context"] = "game option"
            else:
                await message.channel.send(f"Game {game_name} not found. Try again (or cancel to quit).")
        elif current_ctx == "game option":
            await send_options_embed(message, "BGA player name", [])
            contexts[author]["context"] = "add player to game"
        elif current_ctx == "add current player to game":
            # add player to game
            pass
        elif "tables".startswith(current_ctx):
            await message.channel.send("In context tables")
        else:
            message.channel.send(
                "No interactive contexts found. Use !setup to setup your account, !play to start a game, and !tables to check the status of a game.",
            )
    else:
        await message.channel.send("Session ended because you waited too long (start over).")
