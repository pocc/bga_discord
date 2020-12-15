import json

from bga_account import SPEED_VALUES, MODE_VALUES, LEVEL_VALUES, KARMA_VALUES
from bga_game_list import is_game_valid
from creds_iface import get_all_logins
from discord_utils import send_options_embed
from tfm_create_game import AVAILABLE_TFM_OPTIONS
from creds_iface import save_data
from keys import CONTRIBUTORS
from utils import normalize_name, reset_context


async def ctx_setup(message, contexts, args):
    """Provide the menu to do things with status."""
    context = contexts[str(message.author)]["context"]
    if context == "setup":
        if message.content.isdigit() and message.content >= "1" and message.content <= "4":
            await parse_setup_menu(message, contexts)
        else:
            await message.channel.send("Enter 1, 2, 3, or 4 for the option in the embed above.")
        return
    # Will run on first setup menu run
    elif context == "":
        await send_main_setup_menu(message, contexts)
    elif context == "bga username":
        save_data(message.author.id, username=message.content)
        reset_context(contexts, str(message.author))
    elif context == "bga password":
        save_data(message.author.id, password=message.content)
        reset_context(contexts, str(message.author))
    elif context == "bga global prefs":
        await ctx_bga_parse_options(message, contexts)
    elif context == "bga choose game prefs":
        game_name = message.content
        if await is_game_valid(game_name):
            contexts[str(message.author)]["bga prefs for game"] = normalize_name(game_name)
            await ctx_bga_options_menu(message, contexts, option_name=game_name + " option")
        else:
            await message.channel.send(
                f"{game_name} is not a valid game. Spelling matters, but not spaces, captilazition, or punctuation. Try again.",
            )
    elif context == "tfm password":
        ctx_tfm_options(message, contexts)

    # BGA options menu. Not checking input yet.
    else:

        async def save_pref_data(message, options, game_name):
            ret_msg = f"{context} successfully set to {message.content}"
            if game_prefs_name:
                ret_msg += f" for game {game_name}"
                save_data(message.author.id, bga_game_options={game_prefs_name: options})
            else:
                save_data(message.author.id, bga_global_options=options)
            await message.channel.send(ret_msg)

        game_prefs_name = ""
        if "bga prefs for game" in contexts[str(message.author)]:
            game_prefs_name = contexts[str(message.author)]["bga prefs for game"]
        if context in ["presentation", "players", "restrictgroup", "lang"]:
            options = {context: message.content}
            await save_pref_data(message, options, game_prefs_name)
        elif context == "mode":
            options = {context: MODE_VALUES[int(message.content) - 1]}
            await save_pref_data(message, options, game_prefs_name)
        elif context == "speed":
            options = {context: SPEED_VALUES[int(message.content) - 1]}
            await save_pref_data(message, options, game_prefs_name)
        elif context == "karma":
            options = {context: KARMA_VALUES[int(message.content) - 1]}
            await save_pref_data(message, options, game_prefs_name)
        elif context == "levels":
            options = {context: LEVEL_VALUES[int(message.content) - 1]}
            await save_pref_data(message, options, game_prefs_name)


async def send_main_setup_menu(message, contexts):
    opt_type = "option"
    user_data = get_all_logins()[str(message.author.id)]
    desc = f"**User**: {user_data['username']}\n**Password**: {user_data['password']}"
    if "bga options" in user_data:
        option_str = json.dumps(user_data["bga options"], indent=2).replace("\n ", "\n> ")
        desc += f"\n__BGA Global Options__: {option_str}"
    if "bga game options" in user_data:
        option_str = (
            json.dumps(user_data["bga game options"], indent=2).replace("\n   ", "\n> . ").replace("\n ", "\n> ")
        )
        desc += f"\n__BGA Game Options__: {option_str}"
    options = [
        "Set Board Game Arena username",
        "Set Board Game Arena password",
        "Set Board Game Arena default preferences",
        "Set Board Game Arena game preferences",
        "Set Terraforming Mars default preferences",
    ]
    await send_options_embed(message, opt_type, options, description=desc)
    contexts[str(message.author)]["context"] = "setup"


async def parse_setup_menu(message, contexts):
    if message.content == "1":
        contexts[str(message.author)]["context"] = "bga username"
        await message.channel.send("Enter your BGA username")
    elif message.content == "2":
        contexts[str(message.author)]["context"] = "bga password"
        await message.channel.send("Enter your BGA password")
    elif message.content == "3":
        await ctx_bga_options_menu(message, contexts)
    elif message.content == "4":
        await message.channel.send("What game should these preferences be saved for?")
        contexts[str(message.author)]["context"] = "bga choose game prefs"
    elif message.content == "5":
        contexts[str(message.author)]["context"] = "tfm options"
        await send_options_embed(message, "TFM option", AVAILABLE_TFM_OPTIONS)


async def ctx_bga_options_menu(message, contexts, option_name="BGA option"):
    contexts[str(message.author)]["context"] = "bga global prefs"
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
    await send_options_embed(message, option_name, bga_options)


async def ctx_bga_parse_options(message, contexts):
    if message.content == "1":
        contexts[str(message.author)]["context"] = "mode"
        await send_options_embed(message, "mode of play", MODE_VALUES)
    elif message.content == "2":
        contexts[str(message.author)]["context"] = "speed"
        await send_options_embed(message, "game speed", SPEED_VALUES)
    elif message.content == "3":
        contexts[str(message.author)]["context"] = "karma"
        await send_options_embed(message, "min karma", KARMA_VALUES)
    elif message.content == "4":
        if message.author.name in CONTRIBUTORS:
            contexts[str(message.author)]["context"] = "presentation"
            await message.channel.send("What presentation should your games have?")
        else:
            await message.channel.send("Setting presentation is reserved for contributors.")
    elif message.content == "5":
        contexts[str(message.author)]["context"] = "players"
        await message.channel.send("How many players (For 2 to 5 players, type `2-5`)?")
    elif message.content == "6":
        contexts[str(message.author)]["context"] = "levels"
        await send_options_embed(message, "min level", LEVEL_VALUES)
    elif message.content == "7":
        contexts[str(message.author)]["context"] = "levels"
        await send_options_embed(message, "max level", LEVEL_VALUES)
    elif message.content == "8":
        contexts[str(message.author)]["context"] = "restrictgroup"
        await message.channel.send("What is the name of the BGA group to restrict by?")
    elif message.content == "9":
        contexts[str(message.author)]["context"] = "lang"
        await message.channel.send("What 2 letter language code to set to?")


async def ctx_tfm_options(message, contexts):
    pass
