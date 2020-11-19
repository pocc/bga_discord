# Via https://stackoverflow.com/questions/7160737/how-to-validate-a-url-in-python-malformed-or-not
from urllib.parse import urlparse


def is_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

async def send_help(message, help_type):
    """Send the user a help message from a file"""
    filename = "src/docs/" + help_type + "_msg.md"
    with open(filename) as f:
        text = f.read()
    remainder = text.replace(4*" ", "\t")
    await send_message_partials(message.author, remainder)

async def send_message_partials(destination, remainder):
    # Loop over text and send message parts from the remainder until remainder is no more
    while len(remainder) > 0:
        chars_per_msg = 2000
        if len(remainder) < chars_per_msg:
            chars_per_msg = len(remainder)
        msg_part = remainder[:chars_per_msg]
        remainder = remainder[chars_per_msg:]
        # Only break on newline
        if len(remainder) > 0:
            while remainder[0] != "\n":
                remainder = msg_part[-1] + remainder
                msg_part = msg_part[:-1]
            # Discord will delete whitespace before a message
            # so preserve that whitespace by inserting a character
            while remainder[0] == "\n":
                remainder = remainder[1:]
            if remainder[0] == "\t":
                remainder = ".   " + remainder[1:]
        await destination.send(msg_part)