from dataclasses import dataclass, replace
import copy
import numpy as np
from enum import IntEnum, Enum, auto
from typing import List, Tuple, Optional, Dict, Set
import random

class Phase(IntEnum):
    PlaceRing   = 0
    MoveRing    = 1
    RemoveChain = 2
    RemoveRing  = 3
    GameOver    = 4

class CellState(IntEnum):
    OutOfBounds = 0
    Empty       = 1
    Player0     = 2
    Player1     = 3
    Player0Ring = 4
    Player1Ring = 5

class ActionType(IntEnum):
    PlaceRing   = 0
    MoveRing    = 1
    RemoveChain = 2
    RemoveRing  = 3

class Direction(IntEnum):
    HorizontalForward   = 0
    HorizontalBackward  = 1
    VerticalForward     = 2
    VerticalBackward    = 3
    DiagonalForward     = 4
    DiagonalBackward    = 5
    NoDirection         = 6

@dataclass()
class YinshAction:
    action_type: ActionType
    coord: (int, int)
    direction: Optional[Direction] = None
    distance: Optional[int] = None

@dataclass()
class Chain:
    player: int
    coord: (int, int)
    direction: Direction

class YinshState:
    def __init__(self, game, board):
        self.game : YinshGame = game
        self.board : np.ndarray = board
        self.phase : Phase = Phase.PlaceRing
        self.rings = [[], []]
        # self.score : [int, int] = [0, 0]
        self.current_player : int = 0
        self.turn_player : int= 0
        self.turn_count : int = 0

    def __repr__(self):
        return str(self.board)
    
    def LegalActions(self):
        if self.phase == Phase.PlaceRing:
            return self.LegalActionsPlaceRing()
        elif self.phase == Phase.MoveRing:
            return self.LegalActionsMoveRing()
        elif self.phase == Phase.RemoveChain:
            return self.LegalActionsRemoveChain()
        elif self.phase == Phase.RemoveRing:
            return self.LegalActionsRemoveRing()
        else:
            return []

    def IsTerminal(self):
        return (self.phase == Phase.GameOver)

    def CurrentPlayer(self):
        return self.current_player

    def CurrentPhase(self):
        return self.phase
    
    def ApplyActionPlaceRing(self, action):
        if self.current_player == 0:
            ring_state = CellState.Player0Ring
        else:
            ring_state = CellState.Player1Ring

        self.board[action.coord] = ring_state
        self.rings[self.current_player].append(action.coord)

        if len(self.rings[0]) == 5 and len(self.rings[1]) == 5:
            self.phase = Phase.MoveRing

        self.turn_count += 1
        self.turn_player = 1 - self.turn_player
        self.current_player = self.turn_player

        

    def ApplyActionMoveRing(self, action):
        if self.current_player == 0:
            ring_state = CellState.Player0Ring
            tile_state = CellState.Player0
        else:
            ring_state = CellState.Player1Ring
            tile_state = CellState.Player1

        self.board[action.coord] = tile_state
        end_coord = YinshGame.CoordPlusVector(action.coord, action.direction, action.distance)
        # print("tile_state", tile_state)
        self.board[end_coord] = ring_state
        for i, ring in enumerate(self.rings[self.current_player]):
            if ring == action.coord:
                self.rings[self.current_player][i] = end_coord

        # flip tiles
        flip_coords = YinshGame.get_coords_between(action.coord, action.direction, action.distance)
        
        for coord in flip_coords:
            if self.board[coord] == CellState.Player0:
                self.board[coord] = CellState.Player1
            elif self.board[coord] == CellState.Player1:
                self.board[coord] = CellState.Player0

        chains = self.GetChains()
        if len(chains) > 0:
            print("chains", chains)
            self.phase = Phase.RemoveChain
            turn_player_has_chain = any([chain.player == self.turn_player for chain in chains])
            if turn_player_has_chain:
                self.current_player = self.turn_player
            else:
                self.current_player = 1 - self.turn_player
        else:
            self.phase = Phase.MoveRing
            self.turn_player = 1 - self.turn_player
            self.current_player = self.turn_player

            self.turn_count += 1

    def ApplyActionRemoveChain(self, action):
        coords_to_remove = YinshGame.get_coords_between(action.coord, action.direction, 5) + [action.coord]
        for coord in coords_to_remove:
            self.board[coord] = CellState.Empty

        self.phase = Phase.RemoveRing
    
    def ApplyActionRemoveRing(self, action):
        self.board[action.coord] = CellState.Empty
        self.rings[self.current_player].remove(action.coord)

        if len(self.rings[0]) == 2:
            self.phase = Phase.GameOver
            self.winner = 0
        elif len(self.rings[1]) == 2:
            self.phase = Phase.GameOver
            self.winner = 1
        else:
            chains = self.GetChains()
            if len(chains) > 0:
                self.phase = Phase.RemoveChain

                turn_player_has_chain = any([chain.player == self.turn_player for chain in chains])
                if turn_player_has_chain:
                    self.current_player = self.turn_player
                else:
                    self.current_player = 1 - self.turn_player
            else:
                self.phase = Phase.MoveRing
                self.turn_player = 1 - self.turn_player
                self.current_player = self.turn_player

                self.turn_count += 1

    def ApplyAction(self, action):
        if self.phase == Phase.PlaceRing:
            self.ApplyActionPlaceRing(action)
        elif self.phase == Phase.MoveRing:
            self.ApplyActionMoveRing(action)
        elif self.phase == Phase.RemoveChain:
            self.ApplyActionRemoveChain(action)
        elif self.phase == Phase.RemoveRing:
            self.ApplyActionRemoveRing(action)

    def ToString(self):

        turn_player_string = str(self.turn_player)
        current_player_string = str(self.current_player)
        phase_string = str(int(self.phase))
        turn_count_string = str(self.turn_count)

        board_string = ''
        for row in range(self.game.kNumRows):
            for col in range(self.game.kNumCols):
                board_string += str(self.board[row,col])
        # return board_string

        state_string = ','.join([turn_player_string, current_player_string, phase_string, turn_count_string, board_string])
        return state_string
        

    def FromString(self, state_string):
        turn_player_string, current_player_string, phase_string, turn_count_string, board_string = state_string.split(',')
        self.turn_player = int(turn_player_string)
        self.current_player = int(current_player_string)
        self.phase = Phase(int(phase_string))
        self.turn_count = int(turn_count_string)
        str_idx = 0
        for row in range(self.game.kNumRows):
            for col in range(self.game.kNumCols):
                self.board[row,col] = int(board_string[str_idx])
                str_idx += 1
                if (self.board[row,col] == CellState.Player0Ring):
                    self.rings[0].append((row,col))
                elif (self.board[row,col] == CellState.Player1Ring):
                    self.rings[1].append((row,col))

    def DisplayString(self):
        state_strings = {}
        state_strings[CellState.OutOfBounds] = " "
        state_strings[CellState.Empty] = "."
        state_strings[CellState.Player0] = "0"
        state_strings[CellState.Player1] = "1"
        state_strings[CellState.Player0Ring] = "2"
        state_strings[CellState.Player1Ring] = "3"

        print("   ", end='')
        for col in range(self.game.kNumCols):
            print('{0: <2}'.format(str(col)), end='')
        print()
        print("   ", end='')
        for col in range(self.game.kNumCols):
            print('--', end='')
        print()
        for row in range(self.game.kNumRows):
            print('{0: <2}'.format(str(row)), end='|')
            for col in range(self.game.kNumCols):
                print(state_strings[self.board[row,col]], end=' ')
            print()

    ## Legal Actions
    def LegalActionsPlaceRing(self):
        actions = []
        for coord in self.game.coords:
            if self.board[coord] == CellState.Empty:
                actions.append(YinshAction(ActionType.PlaceRing, coord))
        return actions

    def LegalActionsMoveRing(self):
        player = self.current_player
        rings = self.rings[player]
        actions = []
        for ring in rings:
            for direction in YinshGame.move_directions:
                actions += self.LegalActionsMoveRingDirection(ring, direction)
        return actions
    
    def LegalActionsMoveRingDirection(self, ring, direction):
        actions = []
        in_block = False
        for distance in range(1, YinshGame.kMaxDistance):

            end_coord = YinshGame.CoordPlusVector(ring, direction, distance)

            if end_coord[0] < 0 or end_coord[0] >= YinshGame.kNumRows or end_coord[1] < 0 or end_coord[1] >= YinshGame.kNumCols:
                break

            if self.board[end_coord] == CellState.OutOfBounds:
                break

            if self.board[end_coord] == CellState.Empty:
                actions.append(YinshAction(ActionType.MoveRing, ring, direction, distance))
            elif self.board[end_coord] == CellState.Player0 or self.board[end_coord] == CellState.Player1:
                in_block = True
            elif self.board[end_coord] == CellState.Player0Ring or self.board[end_coord] == CellState.Player1Ring:
                break

            if in_block and self.board[end_coord] == CellState.Empty:
                break
        return actions
    
    def GetChainsWithCoordsArrays(self, coords_arrays, direction):
        player_state = [CellState.Player0, CellState.Player1]
        chains = []

        for coord_array in coords_arrays:
            in_chain = [False, False]
            chain_length = 0
            for coord in coord_array:
                row, col = coord

                if row >= YinshGame.kNumRows or col >= YinshGame.kNumCols:
                    break

                if self.board[row, col] == CellState.OutOfBounds:
                    continue
                
                for player in range(2):
                    if self.board[row, col] == player_state[player]:
                        if not in_chain[player]:
                            in_chain[player] = True
                            in_chain[1-player] = False
                            chain_length = 1
                        else:
                            chain_length += 1
                            if chain_length >= 5:
                                chains.append(Chain(player, coord, direction))
                
                if self.board[row, col] == CellState.Empty or self.board[row, col] == CellState.Player0Ring or self.board[row, col] == CellState.Player1Ring:
                    in_chain = [False, False]
                    chain_length = 0

        return chains
    
    def GetChains(self):
        chains = []

        # horizontal chains
        horiz_coords = []
        for row in range(YinshGame.kNumCols):
            coord_array = []
            for col in range(YinshGame.kNumCols):
                coord_array.append((row, col))
            horiz_coords.append(coord_array)
        chains += self.GetChainsWithCoordsArrays(horiz_coords, Direction.HorizontalBackward)

        # vertical chains
        vert_coords = []
        for col in range(YinshGame.kNumCols):
            coord_array = []
            for row in range(YinshGame.kNumCols):
                coord_array.append((row, col))
            vert_coords.append(coord_array)
        chains += self.GetChainsWithCoordsArrays(vert_coords, Direction.VerticalBackward)

        # diagonal chains
        diag_coords = []
        for start_coord in YinshGame.diag_starts:
            coord_array = []
            for step in range(YinshGame.kMaxDistance):
                coord_array.append(YinshGame.CoordPlusVector(start_coord, Direction.DiagonalForward, step))
            diag_coords.append(coord_array)
        chains += self.GetChainsWithCoordsArrays(diag_coords, Direction.DiagonalBackward)

        return chains

    def LegalActionsRemoveChain(self):
        actions = []
        player = self.current_player
        chains = self.GetChains()
        for chain in chains:
            if chain.player == player:
                actions.append(YinshAction(ActionType.RemoveChain, chain.coord, chain.direction))
        return actions

    def LegalActionsRemoveRing(self):
        player = self.current_player
        rings = self.rings[player]
        actions = []
        for ring in rings:
            actions.append(YinshAction(ActionType.RemoveRing, ring))
        return actions

class YinshGame:
    kNumRows = 11
    kNumCols = 11
    kMaxDistance = 10
    diag_starts = [(4, 0), (3, 0), (2, 0), (1, 0), (1, 1), (0, 1), (0, 2), (0, 3), (0, 4)]
    move_directions = [Direction.HorizontalForward, Direction.HorizontalBackward, Direction.VerticalForward, Direction.VerticalBackward, Direction.DiagonalForward, Direction.DiagonalBackward]

    def __init__(self):

        # board and coords
        self.oob_coords, self.coords = self.create_board_coords()

    def create_board_coords(self):
        oob_coords = [(0, 0),
                    (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (10, 0),
                    (7, 1), (8, 1), (9, 1), (10, 1),
                    (8, 2), (9, 2), (10, 2),
                    (9, 3), (10, 3),
                    (10, 4),
                    (0, 5), (10, 5),
                    (10, 10),
                    (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (0, 10),
                    (1, 7), (1, 8), (1, 9), (1, 10),
                    (2, 8), (2, 9), (2, 10),
                    (3, 9), (3, 10),
                    (4, 10),
                    (5, 10)]
        inbounds_coords = [(row, col) for row in range(YinshGame.kNumRows) for col in range(YinshGame.kNumCols) if (row, col) not in oob_coords]
        return oob_coords, inbounds_coords

    def get_initial_board(self):
        board = np.full((YinshGame.kNumRows, YinshGame.kNumCols), CellState.Empty)
        for coord in self.oob_coords:
            board[coord] = CellState.OutOfBounds
        
        return board
    
    def get_initial_state(self):
        initial_board = self.get_initial_board()
        return YinshState(self, initial_board)
    
    def CoordPlusVector(coord, direction, distance):
        if direction == Direction.HorizontalForward:
            return (coord[0], coord[1] + distance)
        elif direction == Direction.HorizontalBackward:
            return (coord[0], coord[1] - distance)
        elif direction == Direction.VerticalForward:
            return (coord[0] + distance, coord[1])
        elif direction == Direction.VerticalBackward:
            return (coord[0] - distance, coord[1])
        elif direction == Direction.DiagonalForward:
            return (coord[0] + distance, coord[1] + distance)
        elif direction == Direction.DiagonalBackward:
            return (coord[0] - distance, coord[1] - distance)
        
    def get_coords_between(coord, direction, distance):
        coords = []
        for step in range(1, distance):
            coords.append(YinshGame.CoordPlusVector(coord, direction, step))
        return coords

class YinshFrontend():
    def to_frontend_state(state):
        pass

    def from_frontend_state(state):
        pass

    def from_frontend_action(action):
        pass

if __name__ == "__main__":
    game = YinshGame()
    state = game.get_initial_state()
    # for i in range(100):
    while not state.IsTerminal():
        legal_actions = state.LegalActions()
        # for action in legal_actions:
            # print(action)
        action = random.choice(legal_actions)
        state.ApplyAction(action)
        print('\n')
        print(state.ToString())
    print('\n')
    print(state.ToString())
    print(f'Winner: Player {state.winner}')

    state_string = state.ToString()

    new_state = game.get_initial_state()
    new_state.DisplayString()
    new_state.FromString(state_string)
    new_state.DisplayString()
    
    # print(legal_actions)