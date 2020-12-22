"""Interact with the bot if you are missing options in your command.

This works by changing the global `contexts` for a discord user for every message they send.
Each message that is meaningful to the bot will change the context.
Each different context will route them to the appropriate location.
"""
import time

from creds_iface import purge_data
from discord_utils import send_options_embed
from cmd_sub_play import ctx_play
from cmd_sub_setup import ctx_setup
from cmd_sub_status import ctx_status
from cmd_sub_friend import ctx_friend


async def trigger_interactive_response(message, contexts, curr_ctx, args):
    """Interactive menu triggers when there is an error state with the command entered
    and not enough arguments are provided or the wrong arguments are provided.

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
    Status: if players < 2
        Show current settings (and show options):
            1. Add a game (optional)
            2. Add a player (optional)
            3. Done
    Friend:
        Show friend list
            0. Done
            1. Add BGA friend
            2. Add all members of a BGA group as friends
            3. Join BGA group
    """
    if curr_ctx == "purge":
        purge_data(str(message.author.id))
        await message.channel.send(f"Deleted data for {message.author.name}.")
        return
    author = str(message.author)
    if message.content.startswith("cancel"):
        # quit current interactive session
        await message.channel.send("Canceled operation")
        contexts[author] = {}
        return
    if curr_ctx == "choose subprogram" and message.content.isdigit() and 1 <= int(message.content) <= 4:
        curr_ctx = [ctx_setup, ctx_play, ctx_status][int(message.content) - 1]
    if curr_ctx in ["setup", "play", "status", "friend"] or author not in contexts or "timeout" not in contexts[author]:
        contexts[author] = {
            "subcommand": curr_ctx,
            "context": "",
            "timestamp": time.time(),
            "channel": message.channel,
            "menu": "",
        }
        in_five_min_window = True
    else:
        in_five_min_window = contexts[author]["timestamp"] > time.time() - 300
    if in_five_min_window:
        contexts[author]["timestamp"] = time.time()  # reset timer
        if contexts[author]["subcommand"] == "choose subprogram":
            if message.content.isdigit() and "1" <= message.content <= "3":
                contexts[author]["subcommand"] = ["setup", "play", "status"][int(message.content) - 1]
            else:
                await message.channel.send("Enter a number between 1 and 3 (see embed above)")
                return
        if contexts[author]["subcommand"] == "timeout":
            await send_options_embed(message, "BGA bot option", ["setup", "play", "status"])
            contexts[author]["subcommand"] = "choose subprogram"
            return
        context_cmd = contexts[author]["subcommand"]
        if context_cmd:
            cmd = {
                "setup": ctx_setup,
                "play": ctx_play,
                "status": ctx_status,
                "friend": ctx_friend,
            }[context_cmd]
            await cmd(message, contexts, args)
        else:
            await message.channel.send(
                "No interactive contexts found. Use `!setup` to setup your account, `!play` to start a game, and `!status` to check the status of a game.",
            )
    else:
        await message.channel.send("Session ended because you waited > 5min (start over).")
