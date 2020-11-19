# BGA Discord 

![](https://i.imgur.com/KgvqoU0.png)

This is a bot to help you set up [board game arena](https://boardgamearena.com) (BGA) 
and [terraforming mars](https://github.com/bafolts/terraforming-mars) (TFM) games in discord.

You can add the bot to your server by [giving it access](https://discord.com/api/oauth2/authorize?client_id=711844812424216598&permissions=79872&scope=bot).

These commands will work in any channel @BGA is on and also as direct messages to @BGA.

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

Create a file called `src/keys.py` and paste the bot token into it:

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

BGA commands start with `!bga` and TFM games start with `!tfm`

Check one of the help documents for more information about each subcommand:

* `bga`: [BGA Help](bga_help_msg.md)
* `tfm`: [TFM Help](tfm_help_msg.md)

## License

Apache2