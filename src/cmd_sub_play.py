"""Subcommands for choosing a game to play
"""
from bga_game_list import is_game_valid
from bga_create_game import setup_bga_game
from discord_utils import send_options_embed, send_simple_embed
from cmd_sub_setup import ctx_bga_options_menu, ctx_bga_parse_options
from bga_account import MODE_VALUES, SPEED_VALUES, KARMA_VALUES, LEVEL_VALUES
from utils import reset_context


GAME_OPTIONS = ["finish and create game", "add a player", "change a game option", "change target channel for embed"]


async def ctx_play(message, contexts, args):
    context = contexts[str(message.author)]["context"]
    # If there's a valid game name, don't ask for it
    game_name = ""
    for arg in args:
        if await is_game_valid(arg):
            game_name = arg
            context = "choose game"
            break
    if context == "":
        await send_simple_embed(message, "Enter the name of the game you want to play")
        contexts[str(message.author)]["context"] = "choose game"
    elif context == "choose game":
        await ctx_choose_game(message, contexts, game_name)
    elif context == "add player":
        await ctx_add_a_player(message, contexts, args)
        await send_game_options(message, contexts)
    elif context == "change bga option":
        await ctx_bga_parse_options(message, contexts)
    elif context == "change channel":
        await ctx_change_target_channel_for_embed(message, contexts, args)
        await send_game_options(message, contexts)
    # BGA options menu. Not checking input yet.
    elif context in ["presentation", "players", "restrictgroup", "lang", "mode", "speed", "karma", "levels"]:
        is_session_finished = True
        if context in ["presentation", "players", "restrictgroup", "lang"]:
            contexts[str(message.author)]["game"]["options"][context] = message.content
            await message.channel.send(f"{context} successfully set to {message.content}")
        elif context == "mode":
            contexts[str(message.author)]["game"]["options"][context] = MODE_VALUES[int(message.content) - 1]
            await message.channel.send(f"{context} successfully set to {MODE_VALUES[int(message.content)-1]}")
        elif context == "speed":
            contexts[str(message.author)]["game"]["options"][context] = SPEED_VALUES[int(message.content) - 1]
            await message.channel.send(f"{context} successfully set to {SPEED_VALUES[int(message.content)-1]}")
        elif context == "karma":
            contexts[str(message.author)]["game"]["options"][context] = KARMA_VALUES[int(message.content) - 1]
            await message.channel.send(f"{context} successfully set to {KARMA_VALUES[int(message.content)-1]}")
        elif context == "levels":
            contexts[str(message.author)]["game"]["options"][context] = LEVEL_VALUES[int(message.content) - 1]
            await message.channel.send(f"{context} successfully set to {LEVEL_VALUES[int(message.content)-1]}")
        else:
            is_session_finished = False
        if is_session_finished:
            reset_context(contexts, message.author)
        await send_game_options(message, contexts)  # resend the game edit options once option is seleceted
    else:
        if message.content.isdigit() and 1 <= int(message.content) <= len(GAME_OPTIONS):
            if message.content == "1":
                await ctx_finish_and_create_game(message, contexts, args)
            elif message.content == "2":
                await message.channel.send("What is the player's name?")
                contexts[str(message.author)]["context"] = "add player"
            elif message.content == "3":
                await ctx_bga_options_menu(message, contexts)
                contexts[str(message.author)]["context"] = "change bga option"
            else:
                await message.channel.send("Which channel should the embed be sent to?")
                contexts[str(message.author)]["context"] = "change channel"
        else:
            await message.channel.send(f"Invalid number sent. Needs to be between 1 and {len(GAME_OPTIONS)}")


async def ctx_choose_game(message, contexts, game_name):
    contexts[str(message.author)]["game"] = {"players": [message.author.name], "name": game_name, "options": {}}
    if str(message.channel.type) == "private":
        contexts[str(message.author)]["game"]["channel"] = "DM with Bot"
        contexts[str(message.author)]["game"]["channel_id"] = message.channel.id
    else:
        contexts[str(message.author)]["game"]["channel"] = message.channel.name
        contexts[str(message.author)]["game"]["channel_id"] = message.channel.id
    if not game_name:
        game_name = message.content
    if await is_game_valid(game_name):
        # SEND THE GAME OPTIONS if it's a valid game
        await send_game_options(message, contexts, game_name=game_name)
        contexts[str(message.author)]["game"]["name"] = game_name
    if contexts[str(message.author)] == "choose game":  # If no games of the same name were found
        await message.channel.send(f"Game `{game_name}` not found. Try again (or cancel to quit).")


async def send_game_options(message, contexts, game_name=""):
    if not game_name:
        game_name = contexts[str(message.author)]["game"]["name"]
    players = contexts[str(message.author)]["game"]["players"]
    options = contexts[str(message.author)]["game"]["options"]
    channel = contexts[str(message.author)]["game"]["channel"]
    await send_options_embed(
        message,
        f"{game_name} game option",
        GAME_OPTIONS,
        description=f"Players: {players}\nOptions: {options}\nChannel: {channel}",
    )
    contexts[str(message.author)]["context"] = "game option"


async def ctx_game_option(message, contexts, args):
    if message.content.isdigit() and 1 <= int(message.content) <= len(GAME_OPTIONS):
        choice = int(message.content)
        contexts[str(message.author)]["context"] = GAME_OPTIONS[choice - 1]
        contexts[str(message.author)]["game"]["players"], contexts[str(message.author)]["game"]["options"] = [], []
        title_opt = contexts[str(message.author)]["context"]
        await send_options_embed(message, title_opt, [])
    else:
        await message.channel.send(f"Enter a number between 1 and {len(GAME_OPTIONS)}")


async def ctx_add_a_player(message, contexts, args):
    contexts[str(message.author)]["game"]["players"].append(message.content)
    await message.channel.send("Added player " + message.content)
    reset_context(contexts, message.author)


async def ctx_change_target_channel_for_embed(message, contexts, args):
    contexts[str(message.author)]["channel"] = message.content
    await message.channel.send("Changed channel to " + message.content)
    reset_context(contexts, message.author)


async def ctx_finish_and_create_game(message, contexts, args):
    game = contexts[str(message.author)]["game"]["name"]
    players = contexts[str(message.author)]["game"]["players"]
    options = contexts[str(message.author)]["game"]["options"]
    errs = await setup_bga_game(message, str(message.author.id), game, players, options)
    if errs:
        message.channel.send(errs)
    reset_context(contexts, message.author)
