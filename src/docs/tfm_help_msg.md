# __**Terraforming Mars Table Creation**__

Use the following options to create a Terraforming Mars game.
The options below correspond to options in the game. Global options,
specified with a starting `+`, override player options. If all players have
shared preferences for an option, then it will be added.

The default tfm server is https://mars.ross.gg, but you can add any valid url
to the command and it will use that server instead, such as
* terraforming-mars.herokuapp.com
* tfm.msydevops.fr

## Examples
Format your command like
`!tfm +<global opts<p1>;<p1 colors>;<p1 opts<p2>;<p2 colors>;<p2 opts...`

As an example:
`!tfm +a3brewds Pocc;pbkg;covept Seth;r;`

Here, Seth wants to play as red (r) and doesn't care about game options.
Pocc wants to play as color purple, blue, black, green in that order. And then expansions `cvpte` with o for promos.

The mapping between letters and options is below.
For an explanation of options, see `https://github.com/bafolts/terraforming-mars/wiki/Variants`

## **Options**

### **Colors**
Colors preferences are (**r**)ed, (**y**)ellow, (**g**)reen, (**b**)lue, (**p**)urple, blac(**k**)
Use the first letter of each color to represent it or **k** for black

### **Board**
Board options start with `b`: `bt` for tharsis, `bh` for hellas, `be` for elysium, `br` for random

### **Expansions**
- `e` **corporateEra** : Extra corporations to use. <https://boardgamegeek.com/boardgame/241497/terraforming-mars-bgg-user-created-corporation-pac>
- `p` **prelude** : Starting bonuses to speed up the game. <https://boardgamegeek.com/boardgameexpansion/247030/terraforming-mars-prelude>
- `v` **venusNext**/includeVenusMA : 4th TR meter with a set of extra venus cards. <https://boardgamegeek.com/boardgameexpansion/231965/terraforming-mars-venus-next>
- `c` **colonies** : Ganymede-like extra colonies to settle. <https://boardgamegeek.com/boardgameexpansion/255681/terraforming-mars-colonies>
- `t` **turmoil** : Makes the game much longer. <https://boardgamegeek.com/boardgameexpansion/273473/terraforming-mars-turmoil>
- `f` **communityCardsOption** : Fanmade corps and preludes <https://docs.google.com/document/u/1/d/e/2PACX-1vQCccn7kj-MEliV0bBGzkb-kxJvCBk0T9CuIMs6eWjhUIBSinemTaKjKK1ISI4tq2wzJX7wQvoBZcQe/pub>

### **Promos**
- `o` **promoCardsOption** : 7 extra sets of cards (see link above)

### **Options**
- `a` **startingCorporations** (followed by the number)
    Set the number of starting corporations dealt to each player.
- `d` **draftVariant**
    During the Research phase, players select cards one at a time and pass the remaining cards clockwise (during
    even generations) or anti-clockwise (during odd generations), before deciding how many cards to purchase.
- `i` **initialDraft**
    Adds a draft mechanic for starting cards. Choose 1 project cards among 5 and pass the rest to the player on your left.
    Then 1 project cards among 4 and pass the rest to the player on your left. Same process with another 5 project cards
    but pass to the player on your right. If prelude option is activated, choose 1 prelude card among 4 and pass the rest
    to the player on your left. Then 1 prelude card among 3 and pass the rest to the player on your left. Repeat.*
    Random Milestones and Awards
- `l` **soloTR**
    Win by achieving a Terraform Rating of 63 by game end, instead of the default goal of completing all global parameters.
- `m` **shuffleMapOption**
    Shuffles all available tiles to generate a dynamic board. Noctis City and volcanic areas will always remain as land areas.
- `n` **Remove Negative Global Events**
    Exclude all global events that decrease player resources, production, or global parameters. Requires Turmoil to be selected.
- `r` **randomMA** (Random Milestones and Awards)
    Picks 5 milestones and awards at random (6 if playing with Venus Next expansion).
- `s` **showOtherPlayersVP**
    Show other players VPs, including from milestones, awards, and cards. This is dynamically updated.
- `u` **undoOption**
    Enable players to undo their first move of each turn (requires refresh).
- `w` **solarPhaseOption** (World Government Terraforming)
    At the end of each generation, the active player raises a global parameter of his/her choice, without gaining any TR or bonuses from this action.
- `R` **randomFirstPlayer**
    First player is chosen at random
- `A` **aresExtension**
    Ares fan expansion
- `M` **moonExpansion**
    Moon fan expansion
- `S` **showTimers**
    requiresVenusTrackCompletion
    "requiresMoonTrackCompletion",
    "moonStandardProjectVariant",
    "altVenusBoard"



## **Unimplemented** (bug Ross if this bugs you)

- **Beginner Corporations**
    Start with 42 MC and immediately receive 10 cards in hand, without having to pay for any cards during the initial Research phase.
    Shuffle player order and randomly pick the first player.

- **TR Boost**
    Give player(s) up to 10 additional starting TR as a game handicap.

- **Set Predefined Game**
    Replay a previous game by selecting the game seed.
