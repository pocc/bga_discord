BGA is a bot to help you set up board game arena games in discord.
These commands will work in any channel @BGA is on and also as direct messages to @BGA.

You can run these commands interactively: `!play`, or `!status`. `!setup` is a work in a progress.

# __**Available commands**__

## **!list**
    List all of the 100+ games on Board Game Arena. Can also be called with `!list_games` if it's being used by some other bot.

## **!setup bga_username bga_password**
    setup is used to save your BGA username and password so
    this bot can create game tables on your behalf. This bot
    will delete this message after you send it if it is sent
    on a public channel. If either username/password has spaces,
    use quotes.

    To delete your stored username, password, or options, set them to
    something else using the command `!setup` or change them on BGA.

## **!play game user1 user2...**
    play is used to create games on BGA using the account details from setup.
    The game is required, but the number of other users can be >= 0.
    Each user can be a discord_tag if it has an @ in front of it; otherwise, it
    will be treated as a board game arena account name.

## **!status user1 user2...**
    tables shows the tables that all specified users are playing at.
    To see just the games you are playing at use `tables <your bga username>`.

## **!message user1**
    Send a message to a BGA user. On success, you will see `Message sent`. Can shorten to `!msg`.

## **!options**
    Print the available options that can be specified with make.
    Board game arena options must be specified like `speed:slow`.

## **!purge**
    Delete all of the data you see in !setup. This is irreversible.

---

# __**Examples**__

## **!setup**
    Example setup of account for Alice (`Pixlane` on BGA):

    `!setup "Pixlane" "MySuperSecretPassword!"`

    On success, output should be:

    `Account Pixlane setup successfully!`

    If you send this message in a public channel, this bot will read and immediately delete it.

## **!play**
    1. For example, Alice (`Pixlane` on BGA) wants to create a game of Race for the Galaxy
    and wants to invite Bob (`D Fang` on BGA) and Charlie (`_Evanselia_` on Discord),
    using their BGA usernames. To do this, she would type

    `!play "Race for the Galaxy" "D Fang" @Evanselia`

    Note: Alice does not need to invite herself to her own game, so she does not add her own name.

    2. Let's say that Alice wants to type their discord names instead. It would look like

    `!play "Race for the Galaxy" @Bob @Charlie`

    Note: Everyone listed needs to have run `!setup <bga user> <bga pass>` for this to work.
    On success, output for both options should look like:

    `@Alice invited @Bob (D Fang), @Charlie (_Evanselia_): https://boardgamearena.com/table?table=88710056`
