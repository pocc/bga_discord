"""Bot to create games on discord."""
from cryptography.fernet import Fernet
import discord
import json
import os
import re
import shlex
import traceback

from keys import TOKEN, FERNET_KEY
from bga_mediator import BGAAccount, get_game_list
from tfm_mediator import TFMGame, TFMPlayer


client = discord.Client()


@client.event
async def on_ready():
    """Let the user who started the bot know that the connection succeeded."""
    print(f'{client.user.name} has connected to Discord!')
    # Create words under bot that say "Listening to !bga"
    listening_to_help = discord.Activity(type=discord.ActivityType.listening, name="!bga")
    await client.change_presence(activity=listening_to_help)


@client.event
async def on_message(message):
    """Listen to messages so that this bot can do something."""
    # Don't respond to this bot's own messages!
    if message.author == client.user:
        return
    if message.content.startswith('!bga') or message.content.startswith('!tfm'):
        # Replace the quotes on a German keyboard with regular ones.
        message.content.replace('„', '"').replace('“', '"')
        if message.content.count("\"") % 2 == 1:
            await message.author.send(f"You entered \n`{message.content}`\nwhich has an odd number of \" characters. Please fix this and retry.")
            return
        print("Received message", message.content)
        try:
            if message.content.startswith('!bga'):
                await init_bga_game(message)
            if message.content.startswith('!tfm'):
                await init_tfm_game(message)
        except Exception as e:
            print("Encountered error:", e, "\n", traceback.format_exc())
            await message.channel.send("Tell <@!234561564697559041> to fix his bot.")


async def init_bga_game(message):
    args = shlex.split(message.content)
    if len(args) == 1:
        await message.channel.send("Sending BGA help your way.")
        await send_help(message)
        return
    command = args[1]
    if command == "list":
        await bga_list_games(message)
    elif command == "setup":
        if len(args) != 4:
            await message.channel.send("Setup requires a BGA username and "
                                      "password. Run `!bga` to see setup examples.")
            return
        bga_user = args[2]
        bga_passwd = args[3]
        await setup_bga_account(message, bga_user, bga_passwd)
    elif command == "link":
        # expected syntax is `!bga link $discord_tag $bga_username`
        if len(args) != 4:
            await message.channel.send("link got the wrong number of arguments. Run `!bga` to see link examples.")
        discord_tag = args[2]
        if discord_tag[0] != "<":
            await message.channel.send("Unable to link. Syntax is `!bga link @discord_tag 'bga username'`. "
                                      "Make sure that the discord tag has an @ and is purple.")
            return
        discord_id = discord_tag[3:-1]  # Remove <@!...> part of discord tag
        bga_user = args[3]
        await link_accounts(message, discord_id, bga_user)
    elif command == "make":
        options = []
        if len(args) < 3:
            await message.channel.send("make requires a BGA game. Run `!bga` to see make examples.")
            return
        game = args[2]
        players = args[3:]
        for arg in args:
            if ":" in arg:
                key, value = arg.split(":")[:2]
                options.append([key, value]) 
                # Options with : are not players
                players.remove(arg)
        await setup_bga_game(message, game, players, options)
    elif command == "friend":
        await add_friends(args[2:], message)
    elif command == "options":
        await send_options(message)
    else:
        await message.channel.send(f"You entered invalid command `{command}`. "
                                  f"Valid commands are list, link, setup, and make.")
        await send_help(message)

async def init_tfm_game(message):
    """Format of message is !tfm +cpv player1;bgy;urd.
    See the help message for more info."""
    args = shlex.split(message.content)
    global_opts = ""
    players = []
    if len(args) == 1:
        await message.author.send("No command entered! Showing the help for !tfm.")
        await send_tfm_help(message)
        return
    if args[1][0] == "+":
        global_opts = args[1][1:]
        args.remove(args[1])
    for arg in args[1:]:
        print(f"Parsing arg `{arg}`")
        all_args = arg.split(';')
        if len(all_args) == 2:
            name, colors = all_args
            opts = ""
        elif len(all_args) == 3:
            name, colors, opts = all_args 
        else: 
            await message.author.send("Too many semicolons in player string (expected 2-3)!")
            return
        if not re.match("[rygbpk]+", colors):
            await message.author.send(f"Color in {colors} for player {name} is not valid.")
            return
        if not re.match("[cpvchetourdbswalim23456]*", opts):
            await message.author.send(f"Opt in {opts} for player {name} is not valid.")
            return
        new_player = TFMPlayer(name, colors, opts)
        players.append(new_player)
    game = TFMGame()
    options = await game.generate_shared_params(global_opts, players)
    data = await game.create_table(options)
    player_lines = []
    i = 1
    for player in data:
        color_circle = f":{player['color']}_circle:"
        player_line = f"**{i} {color_circle} {player['name']}**\t [Link to Game]({player['player_link']})"
        guild_members = [m.display_name.lower() for m in message.guild.members] 
        player_lines.append(player_line)
        i += 1
    author_line = ""  # It's not as important to have a game creator - the bot is the game creator
    player_list_str = '\n'.join(player_lines)
    options_str = ""
    option_names = list(options.keys())
    option_names.sort()
    for key in option_names:
        if key != "players":
            options_str += f"{key}   =   {options[key]}\n"
    await send_table_embed(message, "Terraforming Mars", "In the 2400s, mankind begins to terraform the planet Mars", author_line, player_list_str, "Options", options_str)
    await game.close_connection()


async def send_tfm_help(message):
    help_msg = """__**Terraforming Mars Table Creation**__

Use the following options to create a Terraforming Mars game.
The options below correspond to options in the game. Global options,
specified with a starting `+`, override player options. If all players have
shared preferences for an option, then it will be added.

Format your command like
`!tfm +<global opts> <p1>;<p1 colors>;<p1 opts> <p2>;<p2 colors>;<p2 opts> ...`

As an example:
`!tfm +a3brewds Pocc;pbkg;covept Seth;r;`

Here, Seth wants to play as red (r) and doesn't care about game options.
Pocc wants to play as color purple, blue, black, green in that order. And then expansions `cvpte` with o for promos.

The mapping between letters and options is below.
For an explanation of options, see `https://github.com/bafolts/terraforming-mars/wiki/Variants`

__=> **Options**__

__=> **Colors**__
Colors preferences are (**r**)ed, (**y**)ellow, (**g**)reen, (**b**)lue, (**p**)urple, blac(**k**)
Use the first letter of each color to represent it or **k** for black

__**Board**__
Board options start with `b`: `bt` for tharsis, `bh` for hellas, `be` for elysium, `br` for random

__**Expansions**__
`e` **corporateEra** : Extra corporations to use. `https://boardgamegeek.com/boardgame/241497/terraforming-mars-bgg-user-created-corporation-pac`
`p` **prelude** : Starting bonuses to speed up the game. `https://boardgamegeek.com/boardgameexpansion/247030/terraforming-mars-prelude`
`v` **venusNext**/includeVenusMA : 4th TR meter with a set of extra venus cards. `https://boardgamegeek.com/boardgameexpansion/231965/terraforming-mars-venus-next`
`c` **colonies** : Ganymede-like extra colonies to settle. `https://boardgamegeek.com/boardgameexpansion/255681/terraforming-mars-colonies`
`t` **turmoil** : Makes the game much longer. `https://boardgamegeek.com/boardgameexpansion/273473/terraforming-mars-turmoil`

__**Promos**__
`o` **promoCardsOption** : 7 extra sets of cards (see link above)
"""
    help_msg2 = """

__**Options**__
`u` **undoOption**
> Enable players to undo their first move of each turn (requires refresh).
`r` **randomMA** (Random Milestones and Awards)
> Picks 5 milestones and awards at random (6 if playing with Venus Next expansion).
`d` **draftVariant**
> During the Research phase, players select cards one at a time and pass the remaining cards clockwise (during 
> even generations) or anti-clockwise (during odd generations), before deciding how many cards to purchase.
`s` **showOtherPlayersVP**
> Show other players VPs, including from milestones, awards, and cards. This is dynamically updated.
`w` **solarPhaseOption** (World Government Terraforming)
> At the end of each generation, the active player raises a global parameter of his/her choice, without gaining any TR or bonuses from this action.
`a` **startingCorporations** (followed by the number)
> Set the number of starting corporations dealt to each player.
`l` **soloTR**
> Win by achieving a Terraform Rating of 63 by game end, instead of the default goal of completing all global parameters.
`i` **initialDraft**
> Adds a draft mechanic for starting cards. Choose 1 project cards among 5 and pass the rest to the player on your left. 
> Then 1 project cards among 4 and pass the rest to the player on your left. Same process with another 5 project cards 
> but pass to the player on your right. If prelude option is activated, choose 1 prelude card among 4 and pass the rest 
> to the player on your left. Then 1 prelude card among 3 and pass the rest to the player on your left. Repeat.*
> Random Milestones and Awards
`m` **shuffleMapOption**
> Shuffles all available tiles to generate a dynamic board. Noctis City and volcanic areas will always remain as land areas.
"""
    unimplemented = """

__**Unimplemented**__ (bug Ross if this bugs you)

Community Corporations
> Adds some fan-made corporations to the game.

Beginner Corporations
> Start with 42 MC and immediately receive 10 cards in hand, without having to pay for any cards during the initial Research phase.
> Shuffle player order and randomly pick the first player.

TR Boost
> Give player(s) up to 10 additional starting TR as a game handicap.

Fast Mode
> Cannot end turn after one action (either play 2 actions or pass for the current generation).

Remove Negative Global Events
> Exclude all global events that decrease player resources, production or global parameters.

Set Predefined Game
> Replay a previous game by selecting the game seed.
"""
    await message.channel.send(help_msg)
    await message.channel.send(help_msg2)
    await message.channel.send(unimplemented)


async def add_friends(friends, message):
    account = await get_active_session(message)
    for friend in friends:
        err_msg = await account.add_friend(friend)
        if err_msg:
            await message.channel.send(err_msg)
            await account.close_connection()
            return
        else:
            await message.channel.send(f"{friend} added successfully as a friend.")
    await account.close_connection()

async def bga_list_games(message):
    """List the games that BGA currently offers."""
    game_data = await get_game_list()
    game_list = list(game_data.keys())
    # Need to truncate at 1000 chars because max message length for discord is 2000
    tr_games = [g[:22] for g in game_list]
    retmsg = ""
    for i in range(len(tr_games)//5): 
        retmsg += "\n`{:<24}{:<24}{:<24}{:<24}{:<24}`".format(*tr_games[5*i:5*(i+1)]) 
        print("Next line", retmsg, len(retmsg))
        if len(retmsg) > 1000:
            await message.channel.send(retmsg)
            retmsg = ""
    if len(retmsg) > 0:
        await message.channel.send(retmsg)


async def setup_bga_account(message, bga_username, bga_password):
    """Save and verify login info."""
    # Delete account info posted on a public channel
    discord_id = message.author.id
    if message.guild:
        await message.delete()
    account = BGAAccount()
    logged_in = await account.login(bga_username, bga_password)
    player_id = await account.get_player_id(bga_username)
    await account.close_connection()
    if logged_in:
        save_data(discord_id, player_id, bga_username, bga_password)
        await message.channel.send(f"Account {bga_username} setup successfully.")
    else:
        await message.author.send("Bad username or password. Try putting quotes around both.")


async def get_active_session(message):
    """Get an active session with the author's login info."""
    discord_id = message.author.id
    login_info = get_login(discord_id)
    if not login_info:
        await message.channel.send("You need to run setup before you can use the `make` or `link` subcommands. Type `!bga` for more info.")
        return
    # bogus_password ("") used for linking accounts, but is not full account setup
    if login_info["password"] == "":
        await message.channel.send("You have to sign in to host a game. Run `!bga` to get info on setup.")
        return
    connection_msg = await message.channel.send("Establishing connection to BGA...")
    account = BGAAccount()
    logged_in = await account.login(login_info["username"], login_info["password"])
    await connection_msg.delete()
    if logged_in:
        return account
    else:
        await message.channel.send("Bad username or password. Try putting quotes around both.")


async def link_accounts(message, discord_id, bga_username):
    """Link a BGA account to a discord account"""
    # An empty password signifies a linked but not setup account
    bogus_password = ""
    account = await get_active_session(message)
    if not account:
        return
    bga_id = await account.get_player_id(bga_username)
    if bga_id == -1:
        await message.channel.send(f"Unable to find {bga_username}. Are you sure it's spelled correctly?")
        return
    save_data(discord_id, bga_id, bga_username, bogus_password)
    await message.channel.send(f"Discord <@!{str(discord_id)}> successfully linked to BGA {bga_username}.")
    await account.close_connection()


async def setup_bga_game(message, game, players, options):
    """Setup a game on BGA based on the message."""
    account = await get_active_session(message)
    if account == None: # If err, fail now
        return
    table_msg = await message.channel.send("Creating table...")
    await create_bga_game(message, account, game, players, options)
    await table_msg.delete()
    await account.close_connection()


async def create_bga_game(message, bga_account, game, players, options):
    """Create the actual BGA game."""
    # If the player is a discord tag, this will be
    # {"bga player": "discord tag"}, otherwise {"bga player":""}
    error_players = []
    bga_discord_user_map = await find_bga_users(players, error_players)
    bga_players = list(bga_discord_user_map.keys())
    table_id, create_err = await bga_account.create_table(game)
    if len(create_err) > 0:
        await message.channel.send(create_err)
        return
    valid_bga_players = []
    invited_players = []
    err_msg = await bga_account.set_table_options(options, table_id)
    if err_msg:
        await message.channel.send(err_msg)
        return
    table_url = await bga_account.create_table_url(table_id)
    author_bga = get_login(message.author.id)["username"]
    # Don't invite the creator to their own game!
    if author_bga in bga_players:
        bga_players.remove(author_bga)
    for bga_player in bga_players:
        bga_player_id = await bga_account.get_player_id(bga_player)
        if bga_player_id == -1:
            error_players.append(f"`{bga_player}` is not a BGA player")
        else:
            await bga_account.invite_player(table_id, bga_player_id)
            valid_bga_players.append(bga_player)
    for bga_name in valid_bga_players:
        discord_tag = bga_discord_user_map[bga_name]
        if len(discord_tag) > 0:  # If the player was passed in as a discord tag
            invited_players.append(f"{discord_tag} (BGA {bga_name})")
        else:  # If the player was passed in as a BGA player name
            discord_id = get_discord_id(bga_name, message)
            if discord_id != -1:
                discord_tag = f"<@!{discord_id}>"
                invited_players.append(f"{discord_tag} (BGA {bga_name})")
            else:
                invited_players.append(f"(BGA {bga_name}) needs to run `!bga link <discord user> <bga user>` on discord (discord tag not found)")
    author_str = f"\n:crown: <@!{message.author.id}> (BGA {author_bga})"
    invited_players_str = "".join(["\n:white_check_mark: " + p for p in invited_players])
    error_players_str = "".join(["\n:x: " + p for p in error_players])
    await send_table_embed(message, game, table_url, author_str, invited_players_str, "Failed to Invite", error_players_str)


async def find_bga_users(players, error_players):
    """Given a set of discord names, find the BGA players we have saved.

    Returns {BGA_username: "discord_tag"}.
    If no discord tag was passed in, then that value be empty."""
    bga_discord_user_map = {}
    for i in range(len(players)):
        # discord @ mentions look like <@!12345123412341> in message.content
        if players[i][0] == "<":
            player_discord_id = players[i][3:-1]
            # If we have login data cached locally for this player, use it.
            bga_player = get_login(player_discord_id)
            if bga_player:
                bga_discord_user_map[bga_player["username"]] = players[i]
            else:
                # This should be non-blocking as not everyone will have it set up
                error_players.append(f"{players[i]} needs to run `!bga link <discord user> <bga user>` on discord")
        else:
            bga_discord_user_map[players[i]] = ""
    return bga_discord_user_map


def save_data(discord_id, bga_userid, bga_username, bga_password):
    """save data."""
    cipher_suite = Fernet(FERNET_KEY)
    user_json = get_all_logins()
    user_json[str(discord_id)] = {"bga_userid": bga_userid, "username": bga_username, "password": bga_password}
    updated_text = json.dumps(user_json)
    reencrypted_text = cipher_suite.encrypt(bytes(updated_text, encoding="utf-8"))
    with open("bga_keys", "wb") as f:
        f.write(reencrypted_text)


def get_all_logins():
    """Get the login details from the text store."""
    cipher_suite = Fernet(FERNET_KEY)
    if os.path.exists("bga_keys"):
        with open("bga_keys", "rb") as f:
            encrypted_text = f.read()
            text = cipher_suite.decrypt(encrypted_text).decode('utf-8')
    else:
        text = "{}"
    user_json = json.loads(text)
    return user_json


def get_login(discord_id):
    """Get login info for a specific user."""
    discord_id_str = str(discord_id)
    logins = get_all_logins()
    if discord_id_str in logins:
        return logins[discord_id_str]
    return None


def get_discord_id(bga_name, message):
    """Search through logins to find the discord id for a bga name."""
    users = get_all_logins()
    for discord_id in users:
        if users[discord_id]["username"] == bga_name:
            return discord_id
    # Search for discord id if BGA name == discord nickname
    for member in message.guild.members:
        if member.display_name.startswith(bga_name):
            return member.id
    return -1


async def send_table_embed(message, game, desc, author, players, second_title, second_content):
    """Create a discord embed to send the message about table creation."""
    print(f"Sending embed with message {message}, game {game}, url {desc}, author {author}, players {players}, 2nd title {second_title}, 2nd content {second_content}")
    retmsg = discord.Embed(
        title=game,
        description=desc,
        color=3447003,
    )
    retmsg.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
    if len(author) > 0:
        retmsg.add_field(name="Creator", value=author, inline=False)
    if players:
        retmsg.add_field(name="Invited", value=players, inline=False)
    if second_content:
        retmsg.add_field(name=second_title, value=second_content, inline=False)
    await message.channel.send(embed=retmsg)


async def send_help(message):
    """Send the user a help message"""
    help_text1 = """BGA is a bot to help you set up board game arena games in discord.
These commands will work in any channel @BGA is on and also as direct messages to @BGA.

__**Available commands**__

    **list**
        List all of the 100+ games on Board Game Arena

    **setup bga_username bga_password**
        setup is used to save your BGA account details.
        This bot will delete this message after you send it.
        If either username or password has spaces, use quotes.

    **link @discord_tag bga_username**
        NOTE: If you run setup, linking accounts is done automatically.

        link is used to connect someone's discord account to their 
        BGA account if you already know both. They will not have 
        to run setup, but they will not be able to host games.
    
    **make game user1 user2...**
        make is used to create games on BGA using the account details from setup.
        The game is required, but the number of other users can be >= 0.
        Each user can be a discord_tag if it has an @ in front of it; otherwise, it
        will be treated as a board game arena account name.

    **options**
        Print the available options that can be specified with make.
        Board game arena options must be specified like `speed:slow`.
"""
    help_text2 = """
__**Examples**__

    **setup** 
        Example setup of account for Alice (`Pixlane` on BGA):
        
        `!bga setup "Pixlane" "MySuperSecretPassword!"`
        
        On success, output should be:
        
        `Account Pixlane setup successfully!`
        
        If you send this message in a public channel, this bot will read and immediately delete it.
    
     **Link** 
        Example setup of account by Alice for Bob (`D Fang` on BGA, @Bob on discord):
        
        `!bga link @Bob "D Fang"`
        
        On success, output should be:
        
        `Discord @Bob successfully linked to BGA D Fang.`
    
    **make**
        1. For example, Alice (`Pixlane` on BGA) wants to create a game of Race for the Galaxy
        and wants to invite Bob (`D Fang` on BGA) and Charlie (`_Evanselia_` on Discord), 
        using their BGA usernames. To do this, she would type
        
        `!bga make "Race for the Galaxy" "D Fang" @Evanselia`
        
        Note: Alice does not need to invite herself to her own game, so she does not add her own name.
        
        2. Let's say that Alice wants to type their discord names instead. It would look like 
        
        `!bga make "Race for the Galaxy" @Bob @Charlie`
        
        Note: Everyone listed needs to have run `!bga setup <bga user> <bga pass>` for this to work.
        On success, output for both options should look like:
    
        `@Alice invited @Bob (D Fang), @Charlie (_Evanselia_): https://boardgamearena.com/table?table=88710056`
"""
    help_text1 = help_text1.replace(4*" ", "\t")
    help_text2 = help_text2.replace(4*" ", "\t")
    await message.author.send(help_text1)
    await message.author.send(help_text2)


async def send_options(message):
    """Send the user a list of supported bga options."""
    options_text = """Options can be specified only with make and with a colon like `speed:slow`.

__**Available options**__

The default is marked with a *

**mode**: *The type of game*
    normal
    training
**speed**: *How fast to play. /day is moves per day. nolimit means no time limit.*
    fast
    medium *
    slow
    24/day
    12/day
    8/day
    4/day
    3/day
    2/day
    1/day
    1/2days
    nolimit
**minrep**: *The minimum reputation required. Reputation is how often you quit midgame.*
    0
    50
    65
    75 *
    85
**presentation**: *The game's description shown beneath it in the game list.*
    <any string with double quotes>
**players**: *The minimum and maximum number of players a game can have. The min/max numbers can be the same.*
    <min players>-<max players> like `2-5`
**minlevel**: The minimum or maximum level of player to play against. You must be at least your min level to choose it.
    `beginner *  (0)`
    `apprentice  (1-99)`
    `average     (100-199)`
    `good        (200-299)`
    `strong      (300-499)`
    `export      (500-600)`
    `master      (600+)`
     
    ex: `minlevel:apprentice`
**maxlevel**: The maximum level of player to play against. You must be at least your max level to choose it.
    `beginner    (0)`
    `apprentice  (1-99)`
    `average     (100-199)`
    `good        (200-299)`
    `strong      (300-499)`
    `export      (500-600)`
    `master *    (600+)`
    
    ex: `maxlevel:expert`
**restrictgroup**: A group name in double quotes to restrict the game to. You should be able to find the group here if it exists: boardgamearena.com/community. You can only use this option if you are a member of that community.
    Default is no group restriction
    Ex: restrictgroup:"BGA Discord Bosspiles" will limit a game to this group
    Ex: "My friends" is a valid group for everyone.
**lang**: ISO639-1 language code like en, es, fr, de. To find yours: en.wikipedia.org/wiki/List_of_ISO_639-1_codes 
    Default language is none

_You can also specify options/values like 200:12 if you know what they are by looking at the HTML._
"""
    options_text = options_text.replace(4*" ", "\t")
    await message.channel.send(options_text)


client.run(TOKEN)
