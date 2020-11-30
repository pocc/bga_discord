"""Utils that require discord."""
import logging

import discord

logger = logging.getLogger(__name__)
logging.getLogger(__name__).setLevel(logging.DEBUG)


async def send_table_embed(message, game, desc, author, players, second_title, second_content):
    """Create a discord embed to send the message about table creation."""
    logger.debug(
        f"Sending embed with message: {message}, game {game}, url {desc}, author {author}, players {players}, 2nd title {second_title}, 2nd content {second_content}",
    )
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


async def send_options_embed(message, opt_type, options, cancellable=True):
    """Ask the user which option they want and return the number."""
    options_text = ""
    for i in range(len(options)):
        option = options[i]
        options_text += f"\n**{i+1}** {option}"
    retmsg = discord.Embed(
        title=f"Choose the {opt_type} with a number",
        description=options_text,
        color=3447003,
    )
    if cancellable:
        retmsg.set_footer(text="Type cancel to quit")
    await message.author.send(embed=retmsg)


async def send_simple_embed(message, title):
    retmsg = discord.Embed(
        title=title,
        color=3447003,
    )
    retmsg.set_footer(text="Type cancel to quit")
    await message.author.send(embed=retmsg)
