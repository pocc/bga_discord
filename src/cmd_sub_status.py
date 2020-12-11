"""sub menu for status if player isn't specified.

Status:

players == 0/1: players need to be specified, game optional

Show current settings (and show options):
    0. Done
    1. Add a game (optional)
    2. Add a player (optional)
"""

from bga_game_list import is_game_valid
from discord_utils import send_simple_embed
from bga_table_status import get_tables_by_players


async def ctx_status(message, contexts, args):
    """Provide the menu to do things with status."""
    if contexts[str(message.author)]["context"] == "status":
        if message.content.isdigit() and message.content >= "0" and message.content <= "2":
            await parse_status_menu(message, contexts)
        else:
            message.channel.send("Enter 0, 1, or 2 for the option in the embed above.")
        return
    # Will run on first status menu run
    elif contexts[str(message.author)]["context"] == "":
        game = ""
        contexts[str(message.author)]["game"] = message.content
        for arg in contexts:
            if await is_game_valid(arg):
                game = arg
                args.remove(game)
        contexts[str(message.author)]["game"] = game
        contexts[str(message.author)]["players"] = args
    elif contexts[str(message.author)]["context"] == "choose bga game":
        contexts[str(message.author)]["game"] = message.content
    elif contexts[str(message.author)]["context"] == "add bga player":
        contexts[str(message.author)]["players"].append(message.content)
    await send_status_menu(message, contexts)


async def parse_status_menu(message, contexts):
    if message.content == "0":
        if len(contexts[str(message.author)]["players"]) >= 1:
            players = contexts[str(message.author)]["players"]
            game = contexts[str(message.author)]["game"]
            await get_tables_by_players(players, message, game_target=game)
            contexts[str(message.author)] = {}
        else:
            message.channel.send("You must check the table of at least one player! Type 2 to add a player.")
    elif message.content == "1":
        await message.channel.send("Enter the game name")
        contexts[str(message.author)]["context"] = "choose bga game"
    elif message.content == "2":
        await message.channel.send("Enter the player name")
        contexts[str(message.author)]["context"] = "add bga player"


async def send_status_menu(message, contexts):
    players = contexts[str(message.author)]["players"]
    players_str = f"[{', '.join(players)}]"
    game = contexts[str(message.author)]["game"]
    if game == "":
        game = "any"  # To provide context to user
    title = "BGA Game Status"
    desc = f"**Running status interactively.**\nHave players **{players_str}**\nNeed {2-len(players)} or more players."
    options = {"Options": f"\n**0** Finish\n**1** Change game from {game}\n**2** Add a player to {players_str}"}
    contexts[str(message.author)]["context"] = "status"
    await send_simple_embed(message, title, description=desc, fields=options)
