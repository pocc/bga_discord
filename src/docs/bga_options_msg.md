Options can be specified only with make and with a colon like `speed:slow`.

__**Available options**__

The default is marked with a *

**mode**: *The type of game*
    normal
    training

**speed**: *How fast to play. /day is moves per day. nolimit means no time limit.*
    fast
    medium
    slow
    24/day
    12/day
    8/day
    4/day
    3/day
    2/day
    1/day *
    1/2days
    nolimit

**minrep**: *The minimum reputation required. Reputation is how often you quit midgame.*
    0 *
    50
    65
    75
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

**open**: If `true`, the table will be immediately opened for joining. Defaults to `true` if and only if `restrictgroup` is set.

_You can also specify options/values like 200:12 if you know what they are by looking at the HTML._
