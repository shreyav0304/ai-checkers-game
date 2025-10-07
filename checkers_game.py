import pygame
import sys
from math import inf

# --- Constants & Configuration ---
WIDTH, HEIGHT = 1200, 800
BOARD_SIZE = 640
SIDEBAR_WIDTH = 340
PADDING = 40
BOARD_POS = (PADDING, (HEIGHT - BOARD_SIZE) // 2)

# Colors
COLOR_BG = (17, 24, 39)
COLOR_CARD = (31, 41, 55)
COLOR_BORDER = (75, 85, 99)
COLOR_DARK_SQUARE = (125, 94, 63)
COLOR_LIGHT_SQUARE = (240, 217, 181)
COLOR_RED_PIECE = (200, 70, 70)
COLOR_BLACK_PIECE = (47, 47, 47)
COLOR_KING = (255, 215, 0)
COLOR_GREEN = (22, 163, 74)
COLOR_BLUE = (59, 130, 246)
COLOR_PURPLE = (139, 92, 246)
COLOR_GHOST = (55, 65, 81)
COLOR_TEXT = (229, 231, 235)
COLOR_LABEL = (156, 163, 175)
COLOR_VALID_MOVE = (255, 255, 255, 100)
COLOR_SELECTED_GLOW = (59, 130, 246, 100)
COLOR_HINT_GLOW = (22, 163, 74, 150)

# Game Constants
ROWS, COLS = 8, 8
SQUARE_SIZE = BOARD_SIZE // COLS
EMPTY = 0
RED, BLACK = 1, 2
KING_R, KING_B = 3, 4

# --- Sound Manager ---
class SoundManager:
    def __init__(self):
        pygame.mixer.init()
        try:
            self.move_sound = pygame.mixer.Sound("sounds/move.mp3")
            self.select_sound = pygame.mixer.Sound("sounds/select.mp3")
            self.capture_sound = pygame.mixer.Sound("sounds/capture.mp3")
            self.win_sound = pygame.mixer.Sound("sounds/win.mp3")
            print("Sound effects loaded successfully.")
        except pygame.error:
            print("Warning: Sound files not found in 'sounds/' folder. Game will run with limited audio.")
            self.move_sound = self.select_sound = self.capture_sound = self.win_sound = None

    def play(self, sound_type):
        if sound_type == "move" and self.move_sound: self.move_sound.play()
        elif sound_type == "select" and self.select_sound: self.select_sound.play()
        elif sound_type == "capture" and self.capture_sound: self.capture_sound.play()
        elif sound_type == "win" and self.win_sound: self.win_sound.play()

# --- Game Logic Class ---
class Board:
    def __init__(self):
        self.board_state = []
        self.red_left = self.black_left = 12
        self.red_kings = self.black_kings = 0
        self.create_board()

    def clone(self):
        new_board = Board()
        new_board.board_state = [row[:] for row in self.board_state]
        new_board.red_left, new_board.black_left = self.red_left, self.black_left
        new_board.red_kings, new_board.black_kings = self.red_kings, self.black_kings
        return new_board

    def create_board(self):
        self.board_state = [
            [EMPTY, BLACK, EMPTY, BLACK, EMPTY, BLACK, EMPTY, BLACK],
            [BLACK, EMPTY, BLACK, EMPTY, BLACK, EMPTY, BLACK, EMPTY],
            [EMPTY, BLACK, EMPTY, BLACK, EMPTY, BLACK, EMPTY, BLACK],
            [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY],
            [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY],
            [RED,   EMPTY, RED,   EMPTY, RED,   EMPTY, RED,   EMPTY],
            [EMPTY, RED,   EMPTY, RED,   EMPTY, RED,   EMPTY, RED],
            [RED,   EMPTY, RED,   EMPTY, RED,   EMPTY, RED,   EMPTY]
        ]
        self.red_left = self.black_left = 12
        self.red_kings = self.black_kings = 0

    def move(self, piece_pos, move_pos):
        start_row, start_col = piece_pos
        end_row, end_col = move_pos
        piece = self.board_state[start_row][start_col]
        self.board_state[end_row][end_col] = piece
        self.board_state[start_row][start_col] = EMPTY

        is_capture = abs(start_row - end_row) == 2
        if is_capture:
            mid_row, mid_col = (start_row + end_row) // 2, (start_col + end_col) // 2
            if self.board_state[mid_row][mid_col] in (RED, KING_R): self.red_left -= 1
            else: self.black_left -= 1
            self.board_state[mid_row][mid_col] = EMPTY

        self.check_for_promotion(end_row, end_col)
        self.update_king_count()
        return is_capture

    def check_for_promotion(self, r, c):
        p = self.get_piece(r, c)
        if r == 0 and p == RED: self.board_state[r][c] = KING_R
        if r == ROWS - 1 and p == BLACK: self.board_state[r][c] = KING_B

    def update_king_count(self):
        self.red_kings = sum(row.count(KING_R) for row in self.board_state)
        self.black_kings = sum(row.count(KING_B) for row in self.board_state)

    def get_piece(self, r, c): return self.board_state[r][c]

    def get_all_valid_moves(self, color):
        all_moves = {}
        has_jump = any(self._get_jumps((r, c)) for r in range(ROWS) for c in range(COLS) if self.is_own_piece(self.get_piece(r, c), color))
        
        for r in range(ROWS):
            for c in range(COLS):
                if self.is_own_piece(self.get_piece(r, c), color):
                    moves = self._get_jumps((r, c)) if has_jump else self._get_regular_moves((r, c))
                    if moves: all_moves[(r, c)] = moves
        return all_moves

    def _get_jumps(self, pos):
        r, c = pos; p = self.get_piece(r, c); jumps = {}
        move_dirs = [(-1,-1), (-1,1), (1,-1), (1,1)] if p in (KING_R,KING_B) else [(-1,-1), (-1,1)] if p==RED else [(1,-1), (1,1)]
        for dr, dc in move_dirs:
            mid_r, mid_c, end_r, end_c = r+dr, c+dc, r+2*dr, c+2*dc
            if self.is_valid_square(end_r, end_c) and self.get_piece(end_r, end_c) == EMPTY and self.is_opponent(mid_r, mid_c, p):
                jumps[(end_r, end_c)] = (mid_r, mid_c)
        return jumps

    def _get_regular_moves(self, pos):
        r, c = pos; p = self.get_piece(r, c); moves = {}
        move_dirs = [(-1,-1), (-1,1), (1,-1), (1,1)] if p in (KING_R,KING_B) else [(-1,-1), (-1,1)] if p==RED else [(1,-1), (1,1)]
        for dr, dc in move_dirs:
            end_r, end_c = r+dr, c+dc
            if self.is_valid_square(end_r, end_c) and self.get_piece(end_r, end_c) == EMPTY:
                moves[(end_r, end_c)] = None
        return moves

    def is_valid_square(self, r, c): return 0 <= r < ROWS and 0 <= c < COLS
    def is_own_piece(self, p, color): return (color == RED and p in (RED, KING_R)) or (color == BLACK and p in (BLACK, KING_B))
    def is_opponent(self, r, c, piece):
        p = self.get_piece(r, c)
        return p != EMPTY and not self.is_own_piece(p, RED if piece in (RED, KING_R) else BLACK)

    def winner(self):
        if self.red_left <= 0 or not self.get_all_valid_moves(RED): return BLACK
        if self.black_left <= 0 or not self.get_all_valid_moves(BLACK): return RED
        return None

    def evaluate(self): return (self.black_left-self.red_left) + (self.black_kings*1.5-self.red_kings*1.5)

    def minimax(self, board, depth, alpha, beta, maximizing_player):
        if depth == 0 or board.winner() is not None:
            return board.evaluate(), None
        best_move = None
        player_color = BLACK if maximizing_player else RED
        if maximizing_player:
            max_eval = -inf
            for piece_pos, moves in board.get_all_valid_moves(player_color).items():
                for move_pos in moves.keys():
                    temp_board = board.clone(); temp_board.move(piece_pos, move_pos)
                    evaluation = self.minimax(temp_board, depth-1, alpha, beta, False)[0]
                    if evaluation > max_eval: max_eval, best_move = evaluation, (piece_pos, move_pos)
                    alpha = max(alpha, evaluation)
                    if beta <= alpha: break
                if beta <= alpha: break
            return max_eval, best_move
        else:
            min_eval = inf
            for piece_pos, moves in board.get_all_valid_moves(player_color).items():
                for move_pos in moves.keys():
                    temp_board = board.clone(); temp_board.move(piece_pos, move_pos)
                    evaluation = self.minimax(temp_board, depth-1, alpha, beta, True)[0]
                    if evaluation < min_eval: min_eval, best_move = evaluation, (piece_pos, move_pos)
                    beta = min(beta, evaluation)
                    if beta <= alpha: break
                if beta <= alpha: break
            return min_eval, best_move

# --- UI Classes ---
class Button:
    def __init__(self, rect, text, normal_color, hover_color, font, callback):
        self.rect, self.text, self.font, self.callback = rect, text, font, callback
        self.normal_color, self.hover_color = normal_color, hover_color
    def draw(self, screen, mouse_pos):
        color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.normal_color
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        text_surf = self.font.render(self.text, True, COLOR_TEXT)
        screen.blit(text_surf, text_surf.get_rect(center=self.rect.center))
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos): self.callback()

# --- Main Game Class ---
class Game:
    def __init__(self, screen):
        self.screen = screen
        self.sounds = SoundManager()
        self.reset_to_menu()
    
    def init_fonts_and_ui(self):
        self.font_sm = pygame.font.SysFont("inter", 18); self.font_md = pygame.font.SysFont("inter", 22, bold=True)
        self.font_lg = pygame.font.SysFont("inter", 32, bold=True); self.font_title = pygame.font.SysFont("inter", 60, bold=True)
        self.init_menu_buttons(); self.init_game_buttons()

    def init_menu_buttons(self):
        self.menu_buttons = [
            Button(pygame.Rect(WIDTH//2-150, HEIGHT//2-80, 300, 50), "Player vs AI", COLOR_GREEN, tuple(min(255,c+20) for c in COLOR_GREEN), self.font_md, lambda: self.start_game("ai")),
            Button(pygame.Rect(WIDTH//2-150, HEIGHT//2-10, 300, 50), "2 Players", COLOR_BLUE, tuple(min(255,c+20) for c in COLOR_BLUE), self.font_md, lambda: self.start_game("2p")),
            Button(pygame.Rect(WIDTH//2-150, HEIGHT//2+60, 300, 50), "Training Mode (Hints)", COLOR_PURPLE, tuple(min(255,c+20) for c in COLOR_PURPLE), self.font_md, lambda: self.start_game("training")),
            Button(pygame.Rect(WIDTH//2-150, HEIGHT//2+130, 300, 40), f"Difficulty: {'Easy' if self.difficulty==2 else 'Medium' if self.difficulty==4 else 'Hard'}", COLOR_GHOST, COLOR_BORDER, self.font_sm, self.toggle_difficulty)
        ]

    def init_game_buttons(self):
        sidebar_x = BOARD_POS[0] + BOARD_SIZE + PADDING
        self.game_buttons = [
            Button(pygame.Rect(sidebar_x+PADDING, BOARD_POS[1]+160, 140, 50), "Main Menu", COLOR_GREEN, tuple(min(255,c+20) for c in COLOR_GREEN), self.font_md, self.reset_to_menu),
            Button(pygame.Rect(sidebar_x+PADDING+160, BOARD_POS[1]+160, 100, 50), "Undo", COLOR_GHOST, COLOR_BORDER, self.font_md, self.undo_move),
            Button(pygame.Rect(sidebar_x+PADDING, BOARD_POS[1]+520, SIDEBAR_WIDTH-80, 50), "How to Play", COLOR_GHOST, COLOR_BORDER, self.font_md, lambda: setattr(self, 'show_instructions', True))
        ]

    def start_game(self, mode):
        self.game_mode = mode; self.reset()
        
    def reset(self):
        self.board = Board(); self.turn = BLACK; self.selected_piece, self.valid_moves, self.winner = None, {}, None
        self.history = []; self.best_move_hint = None; self.game_state = "PLAYING"
        self.turn_start_time = pygame.time.get_ticks()
        if self.game_mode == 'training' and self.turn == RED: self.calculate_hint()

    def reset_to_menu(self):
        self.game_state = "MENU"; self.difficulty = 4; self.show_instructions = False
        self.init_fonts_and_ui()

    def run(self):
        clock = pygame.time.Clock()
        while True:
            clock.tick(60)
            if self.game_state == "MENU": self.run_menu()
            elif self.game_state == "PLAYING": self.run_game()
            elif self.game_state == "GAME_OVER": self.run_game_over()
    
    def run_menu(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(), sys.exit()
            for button in self.menu_buttons: button.handle_event(event)
        self.screen.fill(COLOR_BG); self.draw_text("AI Checkers", self.font_title, COLOR_TEXT, (WIDTH//2, HEIGHT//2 - 160))
        for button in self.menu_buttons: button.draw(self.screen, pygame.mouse.get_pos())
        pygame.display.update()

    def run_game(self):
        if self.game_mode in ["ai", "training"] and self.turn == BLACK and not self.winner:
            self.handle_ai_turn()

        if self.game_mode in ["ai", "2p"] and not self.best_move_hint and not self.winner:
            if not (self.game_mode == "ai" and self.turn == BLACK):
                if (pygame.time.get_ticks() - self.turn_start_time) / 1000 >= 10:
                    self.calculate_hint()

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(), sys.exit()
            if self.show_instructions:
                if event.type == pygame.MOUSEBUTTONDOWN: self.show_instructions = False
                continue
            for button in self.game_buttons: button.handle_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN: self.handle_board_click(pygame.mouse.get_pos())
        
        winner_check = self.board.winner()
        if winner_check and not self.winner: 
            self.winner, self.game_state = winner_check, "GAME_OVER"
            self.sounds.play("win")
        
        self.draw_game_ui(); pygame.display.update()
        
    def run_game_over(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(), sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN: self.reset_to_menu()
        self.draw_game_ui(); overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((0,0,0,180))
        self.screen.blit(overlay, (0,0)); winner_text = "Red Wins!" if self.winner == RED else "Black Wins!"
        self.draw_text(winner_text, self.font_title, COLOR_TEXT, (WIDTH//2, HEIGHT//2 - 40))
        self.draw_text("Click to return to Menu", self.font_md, COLOR_LABEL, (WIDTH//2, HEIGHT//2 + 40))
        pygame.display.update()

    def handle_board_click(self, pos):
        if self.winner: return
        if not (BOARD_POS[0] < pos[0] < BOARD_POS[0]+BOARD_SIZE and BOARD_POS[1] < pos[1] < BOARD_POS[1]+BOARD_SIZE): return
        row, col = (pos[1] - BOARD_POS[1])//SQUARE_SIZE, (pos[0] - BOARD_POS[0])//SQUARE_SIZE
        
        if self.selected_piece:
            if (row, col) in self.valid_moves:
                self.execute_move(self.selected_piece, (row, col))
            elif self.selected_piece == (row, col): # Clicking the same piece deselects it
                self.selected_piece, self.valid_moves = None, {}
            else: # Clicking another piece, try to select it
                self.selected_piece, self.valid_moves = None, {}
                self.handle_board_click(pos)
        else:
            all_moves = self.board.get_all_valid_moves(self.turn)
            if (row, col) in all_moves:
                has_jumps = any(v for moves in all_moves.values() for v in moves.values())
                piece_can_jump = any(all_moves.get((row, col), {}).values())
                if has_jumps and not piece_can_jump: return
                self.sounds.play("select")
                self.selected_piece, self.valid_moves = (row, col), all_moves.get((row, col), {})

    def execute_move(self, start_pos, end_pos):
        self.history.append({'board': self.board.clone(), 'turn': self.turn})
        is_capture = self.board.move(start_pos, end_pos)
        self.sounds.play("capture" if is_capture else "move")
        further_jumps = self.board._get_jumps(end_pos) if is_capture else {}
        
        if further_jumps:
            self.selected_piece = end_pos
            self.valid_moves = further_jumps
            self.turn_start_time = pygame.time.get_ticks()
        else:
            self.change_turn()
            
    def handle_ai_turn(self):
        pygame.time.wait(300)
        _, best_move = self.board.minimax(self.board, self.difficulty, -inf, inf, True)
        if best_move:
            self.history.append({'board': self.board.clone(), 'turn': self.turn})
            start_pos, end_pos = best_move
            is_capture = self.board.move(start_pos, end_pos)
            self.sounds.play("capture" if is_capture else "move")
            
            further_jumps = self.board._get_jumps(end_pos) if is_capture else {}
            while further_jumps:
                self.draw_game_ui(); pygame.display.update(); pygame.time.wait(500)
                next_jump_pos = list(further_jumps.keys())[0]
                self.board.move(end_pos, next_jump_pos)
                self.sounds.play("capture")
                end_pos = next_jump_pos
                further_jumps = self.board._get_jumps(end_pos)
        self.change_turn()

    def change_turn(self):
        self.selected_piece, self.valid_moves = None, {}
        self.turn = BLACK if self.turn == RED else RED
        self.best_move_hint = None
        self.turn_start_time = pygame.time.get_ticks()
        if self.game_mode == 'training' and self.turn == RED and not self.winner:
            self.calculate_hint()

    def calculate_hint(self):
        is_maximizing = self.turn == BLACK
        _, best_move = self.board.minimax(self.board, self.difficulty, -inf, inf, is_maximizing)
        self.best_move_hint = best_move

    def toggle_difficulty(self):
        self.difficulty = 2 if self.difficulty == 6 else self.difficulty + 2
        self.init_menu_buttons()

    def undo_move(self):
        if not self.history: return
        last_state = self.history.pop()
        self.board, self.turn = last_state['board'], last_state['turn']
        self.winner, self.selected_piece, self.valid_moves, self.best_move_hint = None, None, {}, None
        self.turn_start_time = pygame.time.get_ticks()
        if self.game_mode == 'training' and self.turn == RED: self.calculate_hint()

    def draw_game_ui(self):
        self.screen.fill(COLOR_BG); self.draw_board_and_pieces(); self.draw_sidebar()
        self.draw_captured_pieces();
        if self.show_instructions: self.draw_instructions()

    def draw_board_and_pieces(self):
        pygame.draw.rect(self.screen,(30,20,10),(BOARD_POS[0]-10,BOARD_POS[1]-10,BOARD_SIZE+20,BOARD_SIZE+20),border_radius=12)
        for r in range(ROWS):
            for c in range(COLS):
                color = COLOR_LIGHT_SQUARE if (r+c)%2==0 else COLOR_DARK_SQUARE
                pygame.draw.rect(self.screen,color,(BOARD_POS[0]+c*SQUARE_SIZE,BOARD_POS[1]+r*SQUARE_SIZE,SQUARE_SIZE,SQUARE_SIZE))
        
        if self.best_move_hint and not self.selected_piece:
            show_hint = (self.game_mode == 'training' and self.turn == RED) or \
                        (self.game_mode in ['ai', '2p'] and ((pygame.time.get_ticks() - self.turn_start_time) / 1000 >= 10))
            if show_hint and self.best_move_hint:
                start_pos, end_pos = self.best_move_hint
                for r, c in [start_pos, end_pos]:
                    s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA); s.fill(COLOR_HINT_GLOW)
                    self.screen.blit(s, (BOARD_POS[0] + c*SQUARE_SIZE, BOARD_POS[1] + r*SQUARE_SIZE))

        if self.selected_piece:
            r, c = self.selected_piece
            s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA); s.fill(COLOR_SELECTED_GLOW)
            self.screen.blit(s, (BOARD_POS[0] + c*SQUARE_SIZE, BOARD_POS[1] + r*SQUARE_SIZE))

        for r, c in self.valid_moves:
            s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            pygame.draw.circle(s, COLOR_VALID_MOVE, (SQUARE_SIZE//2, SQUARE_SIZE//2), 15)
            self.screen.blit(s, (BOARD_POS[0] + c*SQUARE_SIZE, BOARD_POS[1] + r*SQUARE_SIZE))

        for r in range(ROWS):
            for c in range(COLS):
                p_val = self.board.get_piece(r, c)
                if p_val != EMPTY:
                    color = COLOR_RED_PIECE if p_val in (RED, KING_R) else COLOR_BLACK_PIECE
                    radius = SQUARE_SIZE//2 - 12
                    center_x, center_y = BOARD_POS[0]+c*SQUARE_SIZE+SQUARE_SIZE//2, BOARD_POS[1]+r*SQUARE_SIZE+SQUARE_SIZE//2
                    pygame.draw.circle(self.screen, (0,0,0,50), (center_x, center_y+4), radius)
                    pygame.draw.circle(self.screen, color, (center_x, center_y), radius)
                    if p_val in (KING_R, KING_B):
                        crown_font = pygame.font.SysFont("arial", 30, bold=True)
                        crown = crown_font.render('👑', True, COLOR_KING)
                        self.screen.blit(crown, (center_x-crown.get_width()//2, center_y-crown.get_height()//2))

    def draw_sidebar(self):
        sidebar_x = BOARD_POS[0] + BOARD_SIZE + PADDING
        card1_rect = pygame.Rect(sidebar_x, BOARD_POS[1], SIDEBAR_WIDTH, 220)
        pygame.draw.rect(self.screen, COLOR_CARD, card1_rect, border_radius=16)
        self.draw_text("AI Checkers", self.font_lg, COLOR_TEXT, (card1_rect.centerx, card1_rect.y + 45))
        self.draw_text("A game of strategy", self.font_sm, COLOR_LABEL, (card1_rect.centerx, card1_rect.y + 80))
        
        status_text, status_color = self.get_status_info()
        status_rect = pygame.Rect(card1_rect.x+20, card1_rect.y+110, card1_rect.width-40, 40)
        pygame.draw.rect(self.screen, status_color, status_rect, border_radius=10)
        self.draw_text(status_text, self.font_md, COLOR_TEXT, status_rect)

        card2_rect = pygame.Rect(sidebar_x, card1_rect.bottom + 20, SIDEBAR_WIDTH, 350)
        pygame.draw.rect(self.screen, COLOR_CARD, card2_rect, border_radius=16)
        
        for button in self.game_buttons: button.draw(self.screen, pygame.mouse.get_pos())
    
    def get_status_info(self):
        if self.winner: return ("Red Wins!", COLOR_RED_PIECE) if self.winner == RED else ("Black Wins!", COLOR_BLACK_PIECE)
        p1_name = "Player 1 (Black)" if self.game_mode == '2p' else "AI (Black)"
        p2_name = "Player 2 (Red)" if self.game_mode == '2p' else "Your Turn (Red)"
        if self.game_mode == 'training': p1_name = "AI (Black)"
        return (p1_name, COLOR_BLACK_PIECE) if self.turn == BLACK else (p2_name, COLOR_RED_PIECE)

    def draw_captured_pieces(self):
        y_pos = BOARD_POS[1] + BOARD_SIZE + 20
        red_captured = 12 - self.board.black_left
        black_captured = 12 - self.board.red_left
        self.draw_text(f"Red Captured: {red_captured}", self.font_sm, COLOR_LABEL, (BOARD_POS[0], y_pos), "left")
        self.draw_text(f"Black Captured: {black_captured}", self.font_sm, COLOR_LABEL, (BOARD_POS[0] + BOARD_SIZE, y_pos), "right")

    def draw_instructions(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((0,0,0,180))
        self.screen.blit(overlay, (0,0))
        card_rect = pygame.Rect(0, 0, 500, 300); card_rect.center = (WIDTH//2, HEIGHT//2)
        pygame.draw.rect(self.screen, COLOR_CARD, card_rect, border_radius=16)
        self.draw_text("How to Play", self.font_lg, COLOR_TEXT, (card_rect.centerx, card_rect.y + 40))
        instructions = ["- The player with the black pieces moves first.", "- Select a piece to see its valid moves.", "- If a jump is available, you MUST take it.", "- If a piece can make another jump after capturing, it MUST continue.", "- Pieces become Kings (👑) at the opponent's back rank.", "- Kings can move and capture forwards and backwards."]
        for i, line in enumerate(instructions): self.draw_text(line, self.font_sm, COLOR_LABEL, (card_rect.x + 40, card_rect.y + 90 + i*30), "left")
        self.draw_text("Click anywhere to close", self.font_sm, COLOR_TEXT, (card_rect.centerx, card_rect.bottom - 30))

    def draw_text(self, text, font, color, container, align="center"):
        text_surf = font.render(text, True, color)
        text_rect = text_surf.get_rect()
        if isinstance(container, pygame.Rect):
            if align == "center": text_rect.center = container.center
            else: text_rect.midleft = (container.left + 20, container.centery)
        else:
            if align == "center": text_rect.center = container
            elif align == "left": text_rect.topleft = container
            elif align == "right": text_rect.topright = container
        self.screen.blit(text_surf, text_rect)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("AI Checkers Pro")
    Game(screen).run()

if __name__ == "__main__":
    main()