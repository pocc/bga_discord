# BGA Discord 

This is a bot to help you set up board game arena (BGA) and terraforming mars (TFM) games in discord.
These commands will work in any channel @BGA is on and also as direct messages to @BGA.

BGA commands start with `!bga` and TFM games start with `!tfm`

## Server Bot Setup

Run the following on any VPS

```bash
pip install -r requirements.txt
```

Follow the steps required to [set up a Discord bot account](https://discordpy.readthedocs.io/en/latest/discord.html) with the following permissions:

- Send Messages
- Send TTS Messages
- Manage Messages
- Read Message History

Create a file called `keys.py` and paste the bot token into it:

```
TOKEN = 'yOUR tOkeN hEre'
```

Generate an encryption key with:

```bash
python -c 'from cryptography.fernet import Fernet; print("FERNET_KEY = %s" % Fernet.generate_key())' >> keys.py
```

Run:

```bash
make run
```


## Available commands

Check one of the help documents for more information about each subcommand:

* `bga`: [BGA Help](bga_help_msg.md)
* `tfm`: [TFM Help](tfm_help_msg.md)

## License

Apache2