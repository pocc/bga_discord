# BGA Discord 

BGA is a bot to help you set up board game arena games in discord.
These commands will work in any channel @BGA is on and also as direct messages to @BGA.

## Server Bot Setup

Run the following on any VPS

```bash
pip install -r requirements.txt
make run
```

## Available commands

    **list**
        List all of the 100+ games on Board Game Arena

    **setup <username> <password>**
        setup is used to save your BGA account details.
        This bot will delete this message after you send it.
    
    **make <game> <user1> <user2>...**
        make is used to create games on BGA using the account details from setup.
        The game is required, but the number of other users can be >= 0.

### Examples

    **setup** 
        Example setup of an account:
        
        `!bga setup "Pocc" "MySuperSecretPassword!"`
        
        On success, output should be:
        
        `Account Pocc setup successfully!`
    
    **make**
        For example, if you wanted to create a game of Race for the Galaxy and 
        invite Ross (Pocc on BGA) and Seth (montesat on BGA), you would use
        
        `!bga make "Race for the Galaxy" "Pocc" "montesat"`
        
        Or use discord names (everyone listed needs to have run setup for this to work):
        
        `!bga make "Race for the Galaxy" @Ross @Seth`
        
        On success, output should look like:
    
        `Table created: https://boardgamearena.com/table?table=88710056`
