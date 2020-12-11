import json

from bga_account import SPEED_VALUES, MODE_VALUES, LEVEL_VALUES, KARMA_VALUES
from bga_creds_iface import get_all_logins
from discord_utils import send_options_embed
from tfm_create_game import AVAILABLE_TFM_OPTIONS
from bga_creds_iface import save_data
from keys import CONTRIBUTORS


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
    elif context == "bga password":
        save_data(message.author.id, password=message.content)
    elif context == "bga options":
        await ctx_bga_options(message, contexts)
    elif context == "tfm password":
        ctx_tfm_options(message, contexts)

    # BGA options menu. Not checking input yet.
    elif context in ["presentation", "players", "restrictgroup", "lang"]:
        save_data(message.author.id, options={context: message.content})
        await message.channel.send(f"{context} successfully set to {message.content}")
    elif context == "mode":
        save_data(message.author.id, options={context: MODE_VALUES[int(message.content) - 1]})
        await message.channel.send(f"{context} successfully set to {MODE_VALUES[int(message.content)-1]}")
    elif context == "speed":
        save_data(message.author.id, options={context: SPEED_VALUES[int(message.content) - 1]})
        await message.channel.send(f"{context} successfully set to {SPEED_VALUES[int(message.content)-1]}")
    elif context == "karma":
        save_data(message.author.id, options={context: KARMA_VALUES[int(message.content) - 1]})
        await message.channel.send(f"{context} successfully set to {KARMA_VALUES[int(message.content)-1]}")
    elif context == "levels":
        save_data(message.author.id, options={context: LEVEL_VALUES[int(message.content) - 1]})
        await message.channel.send(f"{context} successfully set to {LEVEL_VALUES[int(message.content)-1]}")


async def send_main_setup_menu(message, contexts):
    opt_type = "option"
    user_data = get_all_logins()[str(message.author.id)]
    desc = f"User: {user_data['username']}\nPassword: {user_data['password']}"
    if "bga options" in user_data:
        option_str = json.dumps(user_data["bga options"], indent=2).replace("\n ", "\n> ")
        desc += f"\nOptions: {option_str}"
    options = [
        "Set Board Game Arena username",
        "Set Board Game Arena password",
        "Set Board Game Arena default options",
        "Set Terraforming Mars default options",
    ]
    await send_options_embed(message, opt_type, options, description=desc)
    contexts[str(message.author)]["context"] = "setup"


async def parse_setup_menu(message, contexts):
    if message.content == "1":
        contexts[str(message.author)]["context"] = "bga username"
        await message.channel("Enter your BGA username")
    elif message.content == "2":
        contexts[str(message.author)]["context"] = "bga password"
        await message.channel("Enter your BGA password")
    elif message.content == "3":
        await ctx_bga_options_menu(message, contexts)
    elif message.content == "4":
        contexts[str(message.author)]["context"] = "tfm options"
        await send_options_embed(message, "TFM option", AVAILABLE_TFM_OPTIONS)


async def ctx_bga_options_menu(message, contexts):
    contexts[str(message.author)]["context"] = "bga options"
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


async def ctx_bga_options(message, contexts):
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
