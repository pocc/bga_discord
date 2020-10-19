BGA is a bot to help you set up board game arena games in discord.
These commands will work in any channel @BGA is on and also as direct messages to @BGA.

# __**Available commands**__

## **list**
    List all of the 100+ games on Board Game Arena

## **setup bga_username bga_password**
    setup is used to save your BGA account details.
    This bot will delete this message after you send it.
    If either username or password has spaces, use quotes.

    This bot will remember your BGA password forever. If you’d like to
    deauthorise the bot from acting on your behalf, change your password at
    <https://boardgamearena.com/preferences?section=account>.

## **link @discord_tag bga_username**
    NOTE: If you run setup, linking accounts is done automatically.

    link is used to connect someone's discord account to their
    BGA account if you already know both. They will not have
    to run setup, but they will not be able to host games.

## **make game user1 user2...**
    make is used to create games on BGA using the account details from setup.
    The game is required, but the number of other users can be >= 0.
    Each user can be a discord_tag if it has an @ in front of it; otherwise, it
    will be treated as a board game arena account name.

## **tables user1 user2...**
    tables shows the tables that all specified users are playing at.
    To see just the games you are playing at use `tables <your bga username>`.

## **options**
    Print the available options that can be specified with make.
    Board game arena options must be specified like `speed:slow`.

---

# __**Examples**__

## **setup**
    Example setup of account for Alice (`Pixlane` on BGA):

    `!bga setup "Pixlane" "MySuperSecretPassword!"`

    On success, output should be:

    `Account Pixlane setup successfully!`

    If you send this message in a public channel, this bot will read and immediately delete it.

## **Link**
    Example setup of account by Alice for Bob (`D Fang` on BGA, @Bob on discord):

    `!bga link @Bob "D Fang"`

    On success, output should be:

    `Discord @Bob successfully linked to BGA D Fang.`

## **make**
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
