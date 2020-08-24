import numpy as np

# constants
WIN_SCORE = 30
MIN_PLAYERS = 1
DELETED_CARDS = [152, 164, 161] # because wordpress.com only allows one copy of a filename, ever, even after deletion
NUM_CARDS = 164 + len(DELETED_CARDS)


class Card:
    def __init__(self, card_num):
        self.player_id = None
        self.player_name = None
        self.id = card_num
        self.img = 'cards/card' + str(card_num)


class Player:
    def __init__(self, name, id):
        self.id = id
        self.name = name
        self.reset()
        self.score = 0
        self.score_change = 0
        self.hand = dict()

    def reset(self):
        # resets hand to game beginning configuration
        self.score = 0
        self.score_change = 0
        self.hand = dict()

    def draw(self, deck, hand_size):
        # adds cards to hand
        while len(self.hand) < hand_size:
            if not deck:
                return False
            card = deck.pop()
            card.player_id = self.id
            card.player_name = self.name
            self.hand[card.id] = card
        return True


class Game:
    def __init__(self):
        self.players = dict()
        self.cards = [Card(i) for i in range(NUM_CARDS) if i not in DELETED_CARDS]
        self.deck = []
        self.code_giver = None
        self.hand_size = None
        self.guesses = []
        self.previous_guesses = []
        self.previous_plays = dict()
        self.plays_pp = None
        self.in_progress = False
        self.final_scores = []
        self.cards_played = dict()
        self.next_id = 1

    def add_player(self, name):
        # add player
        self.players.update({self.next_id:(Player(name, self.next_id))})

        # update game settings
        if self.in_progress:
            self.hand_size = 7 if len(self.players) == 3 else 6
            self.plays_pp = 2 if len(self.players) == 3 else 1
            self.players[self.next_id].draw(self.deck,self.hand_size)

        # update next player's id
        self.next_id += 1
        return self.next_id - 1

    def new_game(self):
        # check if we can start game
        if len(self.players) < MIN_PLAYERS:
            return (False, "Not enough players")

        # reset values to starting configurations
        for player in self.players.values():
            player.reset()
        self.deck = list(np.random.permutation(self.cards))
        self.code_giver = np.random.choice(list(self.players.values()))
        self.plays_pp = 2 if len(self.players) == 3 else 1
        self.hand_size = 7 if len(self.players) == 3 else 6
        self.in_progress = True
        self.start_turn()
        return [True]

    def start_turn(self):
        # choose code giver
        idx = (list(self.players.values()).index(self.code_giver) + 1) % len(self.players)
        self.code_giver = self.players[list(self.players.keys())[idx]]

        # clear previous turn
        self.previous_guesses = self.all_guesses()
        self.previous_plays = self.cards_played
        self.guesses = []
        self.cards_played = dict()
        return self.draw()

    def draw(self):
        # makes all player's draw
        for player in self.players.values():
            if not player.draw(self.deck, self.hand_size):
                self.in_progress = False
                return False
        return True

    def action(self,player_id,card_id):
        # validate cards
        try:
            player_id = int(player_id)
            card_id = int(card_id)
        except:
            return False

        # perform guess/play
        if self.in_play():
            return self.register_guess(player_id, card_id)
        else:
            return self.register_play(player_id, card_id)

    def register_play(self,player_id,card_id):
        # verify player exists
        if player_id not in self.players:
            return False

        # select player
        player = self.players[player_id]

        # verify card is playable and register play
        if card_id not in player.hand:
            return False

        card = player.hand[card_id]

        # verify user hasn't played too many cards
        if player == self.code_giver and [True for c in self.cards_played.values() if c.player_id == player_id]:
            return False
        if player != self.code_giver and len([True for c in self.cards_played.values() if c.player_id == player_id]) >= self.plays_pp:
            return False

        # verify user isn't playing cards before the clue giver has given a clue
        if player != self.code_giver and len(self.cards_played) == 0:
            return False

        self.cards_played[card.id] = card
        del player.hand[card_id]
        return True

    def register_guess(self, player_id, card_id):
        # verify card/player exists
        if player_id not in self.players or card_id >= NUM_CARDS or card_id in DELETED_CARDS:
            return False

        # select player
        player = self.players[player_id]

        # verify card is guessable
        if card_id not in self.cards_played:
            return False

        # select card
        card = self.cards_played[card_id]

        # verify isn't user's own card
        if card.player_id == player.id:
            return False

        # verify user hasn't already guessed too much or is the clue giver
        if [guess for guess in self.guesses if guess[0].id == player_id] or player == self.code_giver:
            return False

        # register guess
        self.guesses.append((player, card))
        self.check_guesses()
        return True

    def check_guesses(self):
        # ready to check?
        if len(self.guesses) < len(self.players) - 1:
            return

        # reset score changes
        for player in self.players.values():
            player.score_change = 0

        # check each guess
        correct_guesses = [card.player_id == self.code_giver.id for _, card in self.guesses]

        # if everyone or no one got it right, everyone gets two except the  clue giver
        if all(correct_guesses) or not any(correct_guesses):
            for player, card in self.guesses:
                player.score += 2
                player.score_change += 2
                if card.player_id != self.code_giver.id:
                    self.players[card.player_id].score += 1
                    self.players[card.player_id].score_change += 1

        # otherwise, everyone who got it right, and the clue giver, gets 3
        else:
            for player, card in self.guesses:
                # everyone whose card was guessed gets one
                if card.player_id != self.code_giver.id:
                    self.players[card.player_id].score += 1
                    self.players[card.player_id].score_change += 1
                # everyone who guesses right gets three
                else:
                    player.score += 3
                    player.score_change += 3
            self.code_giver.score +=3
            self.code_giver.score_change +=3

        # start next turn
        self.start_turn()
        self.winner()

    # returns list of card player is currently viewing (either guessing or in their hand) in random order
    def get_cards(self,player_id):
        cards = self.in_play()
        if cards:
            return list(np.random.permutation(cards))
        else:
            return [id for id in self.players[player_id].hand]

    # returns sorted list of players' scores
    def scores(self):
        return sorted([(player.name, player.score, player.score_change) for player in self.players.values()], key=lambda p: -p[1])

    # returns list of guesses made once all guesses have been made
    def all_guesses(self):
        if len(self.guesses) < len(self.players) - 1:
            return []
        return [(guess[0].name,guess[1].id) for guess in self.guesses]

    # returns list of cards in play
    def in_play(self):
        if len(self.cards_played) == (len(self.players) - 1) * self.plays_pp + 1:
            return [id for id in self.cards_played]
        else:
            return None

    # updates game if there's a winner
    def winner(self):
        winning = max(self.scores(),key=lambda score : score[1])
        if winning[1] >= WIN_SCORE or not self.in_progress:
            self.in_progress = False
            self.final_scores = self.scores()
            self.players = dict()

    # removes a player
    def remove_player(self,player_name):
        # find player
        player = list(filter(lambda player: player.name == player_name,self.players.values()))
        if not player:
            return False
        player_id = player[0].id

        # make sure not to mess up ongoing game
        if self.in_progress:
            # end game if too few people
            if len(self.players) - 1 < MIN_PLAYERS:
                self.players.pop(player_id)
                self.in_progress = False
                return True

            # if code giver, start next round
            if self.code_giver == player[0]:
                self.start_turn()

            # remove cards played by player
            for card in self.cards_played.values():
                if card.player_id == player_id:
                    self.cards_played.pop(card.id)

            # remove player
            player = self.players.pop(player_id)

            # change hand size
            self.hand_size = 7 if len(self.players) == 3 else 6
            self.plays_pp = 2 if len(self.players) == 3 else 1

            # return cards to deck
            self.deck.extend(player.hand.values())

            # check if it's time to analyze guesses
            self.check_guesses()
            return True
        else:
            self.players.pop(player_id)
            return True

    # returns dict with keys, id of cards played and values, tuple with first, name of card player and second, list of guessers
    def previous_turn(self):
        if self.previous_plays:
            plays = dict([(card.id,(card.player_name,[])) for card in self.previous_plays.values()])
            for name, card in self.previous_guesses:
                plays[card][1].append(name)
            N = len(max(plays.values(),key=lambda t : len(t[1]))[1])
            for key in plays:
                plays[key] = (plays[key][0], plays[key][1] + ['']* (N - len(plays[key][1])))
            return dict(sorted(plays.items(),key= lambda item : item[1][0]))
        else:
            return dict()