# BGA Discord

[![Build Status](https://travis-ci.com/pocc/bga_discord.svg?branch=master)](https://travis-ci.com/pocc/bga_discord)

![](https://i.imgur.com/KgvqoU0.png)

This is a bot to help you set up [board game arena](https://boardgamearena.com) (BGA)
and [terraforming mars](https://github.com/bafolts/terraforming-mars) (TFM) games in discord.

You can add the bot to your server by [giving it access](https://discord.com/api/oauth2/authorize?client_id=711844812424216598&permissions=79872&scope=bot).

These commands will work in any channel @BGA is on and also as direct messages to @BGA.

## Available commands

BGA commands start with `!bga` and TFM games start with `!tfm`

Check one of the help documents for more information about each subcommand:

* `bga`: [BGA Help](src/docs/bga_help_msg.md)
* `tfm`: [TFM Help](src/docs/tfm_help_msg.md)

## Server Bot Setup

**NOTE: This section is for hosting this bot yourself. To add it to your server, use [this link](https://discord.com/api/oauth2/authorize?client_id=711844812424216598&permissions=79872&scope=bot).**

Run the following on any VPS

```bash
pip install -r requirements.txt
```

Follow the steps required to [set up a Discord bot account](https://discordpy.readthedocs.io/en/latest/discord.html) with the following privileged gateway intents:

- Server Members Intent

Add the following permissions:

- Send Messages
- Send TTS Messages
- Manage Messages
- Read Message History

Create a file called `src/keys.py` and paste the bot token into it:

```
TOKEN = 'yOUR tOkeN hEre'
```

Generate an encryption key with:

```bash
( umask 077 && python -c 'from cryptography.fernet import Fernet; print("FERNET_KEY = %s" % Fernet.generate_key())' >> src/keys.py )
```

Store your Discord username (replacing `$USER` in the following command):

```bash
python -c 'from pprint import pformat; import sys; print("CONTRIBUTORS = " + pformat(sys.argv[1:]))' "$USER" >> src/keys.py
```

Run:

```bash
make run
```

## License

Apache2
