import json

from bga_account import BGAAccount, SPEED_VALUES, MODE_VALUES, LEVEL_VALUES, KARMA_VALUES
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
        if message.content.isdigit() and message.content >= "1" and message.content <= "5":
            await parse_setup_menu(message, contexts)
        else:
            await message.channel.send("Enter 1, 2, 3, 4, or 5 for the option in the embed above.")
        return
    # Will run on first setup menu run
    elif context == "":
        await send_main_setup_menu(message, contexts)
    elif context == "bga username":
        save_data(message.author.id, username=message.content)
        await message.channel.send(f"Username set to `{message.content}`")
        await send_main_setup_menu(message, contexts)
    elif context == "bga password":
        logins = get_all_logins()
        if not logins[str(message.author.id)]["username"]:
            await message.channel.send("You must first enter your username before entering a password.")
            contexts[str(message.author)]["context"] = "setup"
            return
        account = BGAAccount()
        login_successful = await account.login(logins[str(message.author.id)]["username"], message.content)
        await account.logout()
        if login_successful:
            save_data(message.author.id, password=message.content)
            await message.channel.send("BGA username/password verified and password saved.")
            await send_main_setup_menu(message, contexts)
        else:
            await message.channel.send("BGA did not like that username/password combination. Not saving password.")
            contexts[str(message.author)]["context"] = ""
            await send_main_setup_menu(message, contexts)
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
    # BGA options/TFM options menu. Not checking input yet.
    else:

        async def save_pref_data(message, context, new_value, platform, game_prefs_name):
            options = {context: new_value}
            ret_msg = f"{context} successfully set to {new_value}"
            if platform == "bga" and game_prefs_name:
                ret_msg += f" for game {game_name}"
                save_data(message.author.id, bga_game_options={game_prefs_name: options})
            elif platform == "bga":
                save_data(message.author.id, bga_global_options=options)
            elif platform == "tfm":
                save_data(message.author.id, tfm_global_options=options)
            await message.channel.send(ret_msg)

        game_prefs_name = ""
        if "bga prefs for game" in contexts[str(message.author)]:
            game_prefs_name = contexts[str(message.author)]["bga prefs for game"]
        is_interactive_session_over = True
        if context in ["presentation", "players", "restrictgroup", "lang"]:
            options = {context: message.content}
            await save_pref_data(message, options, message.content, "bga", game_prefs_name)
        elif context == "mode":
            new_value = MODE_VALUES[int(message.content) - 1]
            await save_pref_data(message, context, new_value, "bga", game_prefs_name)
        elif context == "speed":
            new_value = SPEED_VALUES[int(message.content) - 1]
            await save_pref_data(message, context, new_value, "bga", game_prefs_name)
        elif context == "karma":
            new_value = KARMA_VALUES[int(message.content) - 1]
            await save_pref_data(message, context, new_value, "bga", game_prefs_name)
        elif context == "min level":
            new_value = LEVEL_VALUES[int(message.content) - 1]
            await save_pref_data(message, context, new_value, "bga", game_prefs_name)
        elif context == "max level":
            new_value = LEVEL_VALUES[int(message.content) - 1]
            await save_pref_data(message, context, new_value, "bga", game_prefs_name)
        elif context == "tfm choose game prefs":
            pref_name = AVAILABLE_TFM_OPTIONS[int(message.content) - 1]
            await save_pref_data(message, pref_name, True, "tfm", game_prefs_name)
        else:
            is_interactive_session_over = False
        if is_interactive_session_over:
            # Keep on going until user hits cancel
            reset_context(contexts, message.author)
            await send_main_setup_menu(message, contexts)


async def send_main_setup_menu(message, contexts):
    opt_type = "option"
    logins = get_all_logins()
    if str(message.author.id) in logins:
        user_data = get_all_logins()[str(message.author.id)]
    else:
        user_data = {}
    if "username" in user_data:
        desc = f"**User**: `{user_data['username']}`"
    else:
        desc = "**User**: [*unset*]"
    if "password" in user_data:
        desc += "\n**Password**: `********`"
    else:
        desc += "\n**Password**: [*unset*]"
    if "bga options" in user_data:
        option_str = json.dumps(user_data["bga options"], indent=2).replace("\n ", "\n> ")
        desc += f"\n__BGA Global Options__: {option_str}"
    if "bga game options" in user_data:
        option_str = (
            json.dumps(user_data["bga game options"], indent=2).replace("\n   ", "\n> . ").replace("\n ", "\n> ")
        )
        desc += f"\n__BGA Game Options__: {option_str}"
    if "tfm options" in user_data:
        option_str = json.dumps(user_data["tfm options"], indent=2).replace("\n   ", "\n> . ").replace("\n ", "\n> ")
        desc += f"\n__TFM Options__: {option_str}"
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
        contexts[str(message.author)]["context"] = "tfm choose game prefs"


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
        contexts[str(message.author)]["context"] = "min level"
        await send_options_embed(message, "min level", LEVEL_VALUES)
    elif message.content == "7":
        contexts[str(message.author)]["context"] = "max level"
        await send_options_embed(message, "max level", LEVEL_VALUES)
    elif message.content == "8":
        contexts[str(message.author)]["context"] = "restrictgroup"
        await message.channel.send("What is the name of the BGA group to restrict by?")
    elif message.content == "9":
        contexts[str(message.author)]["context"] = "lang"
        await message.channel.send("What 2 letter language code to set to?")
