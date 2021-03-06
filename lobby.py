from game import Game
from lobby_game import LobbyGame
from preset_decks import PRESET_DECKS, PRESET_TARGETS, PRESET_SEEDS, PRESET_WRONG_PROPERTIES

class InvalidGameId(Exception):
  pass

class Lobby(object):
  def __init__(self, game_expiry):
    self.game_expiry = game_expiry

    self.games = []
    self.game_id_to_game = {}
    self.socket_to_game = {}

    self.game_list_sockets = []

  def new_game(self, game_type, name, parent, quick, use_preset_decks, training):
    if len(self.games) == 0:
      next_id = 0
    else:
      next_id = max(self.game_id_to_game.keys()) + 1

    if use_preset_decks:
      game = Game(game_type, quick=quick, deck=PRESET_DECKS[game_type], targets=PRESET_TARGETS[game_type], seed=PRESET_SEEDS[game_type], wrong_properties=PRESET_WRONG_PROPERTIES[game_type])
    else:  
      game = Game(game_type, quick=quick)
    lobby_game = LobbyGame(next_id, game, self, training)
    self.games.append(lobby_game)
    self.game_id_to_game[next_id] = lobby_game

    if parent is not None and self.is_valid_game(parent):
      parent_game = self.game_id_to_game[parent]
      parent_game.add_chat(name, (game_type, next_id), "new_game")

    self.send_game_list_update_to_all()
    
    return lobby_game

  def is_valid_game(self, game_id):
    return game_id in self.game_id_to_game

  def get_game(self, game_id):
    if not self.is_valid_game(game_id):
      raise InvalidGameId()
    return self.game_id_to_game[game_id]

  def cleanup_games(self):
    updated = False
    for game in self.games:
      if game.cleanup(self.game_expiry):
        updated = True
    if updated:
      self.send_game_list_update_to_all()

  def get_games(self, see_more_ended):
    sorted_games = filter(lambda game: not game.hidden, sorted(self.games, None, lambda game: game.id))
    new_games = filter(lambda g: not g.game.started, sorted_games)
    started_games = filter(lambda g: g.game.started and not g.game.ended, sorted_games)
    if see_more_ended:
      ended_games = filter(lambda g: g.game.ended, sorted_games)
    else:
      ended_games = filter(lambda g: g.game.ended, sorted_games)[-5:]
    return (new_games, started_games, ended_games)

  def send_game_list_update_to_all(self):
    for socket in self.game_list_sockets:
      socket.send_game_list_update(*self.get_games(socket.see_more_ended))

  def get_players_in_lobby(self):
    return sorted(set([socket.name for socket in self.game_list_sockets]))

  def send_lobby_player_list_update_to_all(self):
    players = self.get_players_in_lobby()
    for socket in self.game_list_sockets:
      socket.send_player_list_update(players)

  def get_players_in_game(self, game_id):
    game = self.game_id_to_game[game_id]
    return sorted(set([socket.name for socket in game.sockets]))

  def update_game_list_socket(self, socket, see_more_ended):
    socket.send_player_list_update(self.get_players_in_lobby())
    socket.send_game_list_update(*self.get_games(see_more_ended))

  def open_game_list_socket(self, socket):
    self.game_list_sockets.append(socket)
    self.send_lobby_player_list_update_to_all()

  def close_game_list_socket(self, socket):
    self.game_list_sockets.remove(socket)
    self.send_lobby_player_list_update_to_all()
