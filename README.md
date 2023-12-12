# Canasta Game

This is a Python backend implementation of the card game Canasta.

## Setup

To set up the game locally, follow these steps:

1. Clone the repository:
   `git clone https://github.com/lucasluize-tech/canastra.git`

2. Navigate into the project directory: `cd canastra`
3. make sure to get all the requirements: `pip install -r requirements.txt`
4. Run the game: `python main.py`

## Game Rules

Canastra is a card game where the goal is to 'chin' by getting rid of all of your cards. Players divide into two teams of two, and each team's cards are placed on the table. When the game is over , the team with the most points wins.

#### **Setup**:

11 cards for each player, 4 new hands of 11 cards ( 2 for each team)

#### **Draw Phase:**

each team's player takes turns to play. Each turn, a player can either pick up a card from the deck or pick up the entire discard pile called 'The Trash'. After picking up, the player can play cards from their hand to the table.

#### **Playing cards:**

If a player have a set in hand or can extend a set in the team's table, you can choose to play the cards in the table. A set is a group of cards of the same _suit_, If you don't have a set in the table, a set must be of length 3 or more to start. If you have a set in the table, you can extend it by adding cards of the same _suit_ to it. The card with rank **2** is treated as **Wild Card**, you can use it as a 2 or a card of any rank if needed.

#### **Discard Phase**

After a player finished playing, they must discard a card from their hand to the discard pile.

#### **No Cards in Hand**

If a player have no cards in hand after playing or after discarding:

- if a player played all of your cards without discarding, the player pick up a brand new hand of 11 cards from the separated new hand piles and keep playing.
- if a player discarded a card, the players passes the turn and get a new hand of 11 cards.

but if there is no new hands left for the team (they got both already) and the player's team has a _CLEAN CANASTRA_, then the player chin and the game ends.

#### **Finishing the Game**

To 'chin', the team needs a _CLEAN CANASTRA_ to end the game.
A 'Clean Canastra' is a set that has no wild cards in it and length of at least 7 cards (2,3,4,5,6,7,8 of ♣ is a clean canstra).

The game can also end if there are no more cards in the deck. At any time if the deck runs out of cards and there is still new hands to be picked up, one of the new hands becomes the new deck, repeating until there are no more new hands to be picked up.

#### **Scoring**

after a player chin, the game ends and the team's points are calculated:

Points are as following:

- 1000 pts for a Canastra from Ace ... Ace
- 500 pts for a Canastra from 2 ... Ace
- 200 pts for a Clean Canastra
- 100 pts for a Canastra (length 7+)
- 10 pts for each card still on the table
- 100 pts for each new hand picked up for the team
- 100 pts if the team chin

First sum the cards on each team's hands, _each team needs to remove from their table that quantity._

**DISCLAIMER**
This is my family's way of playing Canastra, it's not the official rules, but it's the way we play it.

For a more 'official' explanation of the rules, see [this guide](https://www.bicyclecards.com/how-to-play/canasta/).
some of the changes is that we don't use the jokers, we don't use the 'freeze' rule, and we don't use the 'black and red threes' rule.

## Features

- Team-based gameplay: Play with a friend against two AI opponents.
- Automatic scoring: The game automatically calculates scores based on the cards in each team's sets.
- Color-coded output: The game's output is color-coded to make it easier to understand what's happening.

## Contributing

Contributions are welcome! Please fork the repository and create a pull request with your changes.

you will realize that the game is playable, but it relies on the terminal to show the cards, so although it's a multiplayer game, it's not very fun to play with friends since you all know the cards you are playing with. My intention is to transform this into a web app!

Going forward:

1. Create a API to generate instances of the game when 4 players are connected.
2. Create a frontend to show the cards and the game state.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
