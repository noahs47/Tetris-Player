import pygame
import random
import sys
import copy

# Initialize Pygame
pygame.init()

CELL_SIZE = 30
COLS, ROWS = 10, 20
SIDEBAR_WIDTH = 200
WIDTH, HEIGHT = COLS * CELL_SIZE + SIDEBAR_WIDTH, ROWS * CELL_SIZE

# Colors for pieces, consistent per shape
COLORS = {
    'I': (0, 255, 255),   # Cyan
    'O': (255, 255, 0),   # Yellow
    'T': (128, 0, 128),   # Purple
    'S': (0, 255, 0),     # Green
    'Z': (255, 0, 0),     # Red
    'J': (0, 0, 255),     # Blue
    'L': (255, 165, 0),   # Orange
    'grid': (40, 40, 40),
    'bg': (20, 20, 20),
    'text': (255, 255, 255)
}

# Shapes: list of rotation states with block coordinates relative to (0,0)
SHAPES = {
    'I': [
        [(0,1),(1,1),(2,1),(3,1)],
        [(2,0),(2,1),(2,2),(2,3)]
    ],
    'O': [
        [(0,0),(1,0),(0,1),(1,1)]
    ],
    'T': [
        [(1,0),(0,1),(1,1),(2,1)],
        [(1,0),(1,1),(2,1),(1,2)],
        [(0,1),(1,1),(2,1),(1,2)],
        [(1,0),(0,1),(1,1),(1,2)]
    ],
    'S': [
        [(1,0),(2,0),(0,1),(1,1)],
        [(1,0),(1,1),(2,1),(2,2)]
    ],
    'Z': [
        [(0,0),(1,0),(1,1),(2,1)],
        [(2,0),(1,1),(2,1),(1,2)]
    ],
    'J': [
        [(0,0),(0,1),(1,1),(2,1)],
        [(1,0),(2,0),(1,1),(1,2)],
        [(0,1),(1,1),(2,1),(2,2)],
        [(1,0),(1,1),(0,2),(1,2)]
    ],
    'L': [
        [(2,0),(0,1),(1,1),(2,1)],
        [(1,0),(1,1),(1,2),(2,2)],
        [(0,1),(1,1),(2,1),(0,2)],
        [(0,0),(1,0),(1,1),(1,2)]
    ]
}

font = pygame.font.SysFont("consolas", 20)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

def create_board():
    return [[None for _ in range(COLS)] for _ in range(ROWS)]

def check_collision(board, shape_blocks, offset_x, offset_y):
    for x,y in shape_blocks:
        bx, by = x + offset_x, y + offset_y
        if bx < 0 or bx >= COLS or by >= ROWS:
            return True
        if by >= 0 and board[by][bx] is not None:
            return True
    return False

def place_piece(board, shape_blocks, offset_x, offset_y, color):
    for x,y in shape_blocks:
        bx, by = x + offset_x, y + offset_y
        if 0 <= by < ROWS and 0 <= bx < COLS:
            board[by][bx] = color

def clear_lines(board):
    new_board = [row for row in board if any(cell is None for cell in row)]
    lines_cleared = ROWS - len(new_board)
    for _ in range(lines_cleared):
        new_board.insert(0, [None for _ in range(COLS)])
    return new_board, lines_cleared

def count_holes(board):
    holes = 0
    for col in range(COLS):
        block_found = False
        for row in range(ROWS):
            if board[row][col] is not None:
                block_found = True
            elif block_found:
                holes +=1
    return holes

def aggregate_height(board):
    total = 0
    for col in range(COLS):
        col_height = 0
        for row in range(ROWS):
            if board[row][col] is not None:
                col_height = ROWS - row
                break
        total += col_height
    return total

def bumpiness(board):
    heights = []
    for col in range(COLS):
        col_height = 0
        for row in range(ROWS):
            if board[row][col] is not None:
                col_height = ROWS - row
                break
        heights.append(col_height)
    total = 0
    for i in range(len(heights)-1):
        total += abs(heights[i] - heights[i+1])
    return total

class Piece:
    def __init__(self, shape):
        self.shape = shape
        self.rotation = 0
        self.blocks = SHAPES[shape][self.rotation]
        self.x = 3
        self.y = 0
        self.color = COLORS[shape]

    def rotate(self):
        self.rotation = (self.rotation + 1) % len(SHAPES[self.shape])
        self.blocks = SHAPES[self.shape][self.rotation]

    def rotate_back(self):
        self.rotation = (self.rotation - 1) % len(SHAPES[self.shape])
        self.blocks = SHAPES[self.shape][self.rotation]

class TetrisAI:
    def __init__(self):
        self.board = create_board()
        self.score = 0
        self.level = 0
        self.lines_cleared = 0
        self.bag = list(SHAPES.keys())
        random.shuffle(self.bag)
        self.current = self.get_new_piece()
        self.next = self.get_new_piece()
        self.game_over = False
        self.fall_delay = 600
        self.last_fall_time = pygame.time.get_ticks()
        self.target_x = None
        self.target_rotation = None
        self.move_queue = []  # list of moves to get piece where it needs to be

    def get_new_piece(self):
        if not self.bag:
            self.bag = list(SHAPES.keys())
            random.shuffle(self.bag)
        return Piece(self.bag.pop())

    def valid(self, piece, x=None, y=None, blocks=None):
        px = x if x is not None else piece.x
        py = y if y is not None else piece.y
        blks = blocks if blocks is not None else piece.blocks
        return not check_collision(self.board, blks, px, py)

    def place_and_score(self, board, piece, x, rotation):
        # Create a copy board
        test_board = copy.deepcopy(board)
        blocks = SHAPES[piece.shape][rotation]

        # Find lowest y where piece can be placed without collision
        y = 0
        while not check_collision(test_board, blocks, x, y):
            y +=1
        y -=1  # step back up one because last y collided

        if y < 0:
            return None, -999999  # invalid placement

        place_piece(test_board, blocks, x, y, COLORS[piece.shape])
        test_board, lines_cleared = clear_lines(test_board)

        # Calculate heuristics
        holes = count_holes(test_board)
        agg_height = aggregate_height(test_board)
        bump = bumpiness(test_board)

        # Weights tuned to prioritize clearing lines and avoiding holes
        score = (lines_cleared * 1000) - (holes * 500) - (agg_height * 10) - (bump * 10)

        # Bonus for Tetris (4 lines)
        if lines_cleared == 4:
            score += 5000

        return (y, rotation, x), score

    def pick_best_move(self):
        best_score = -999999
        best_move = None
        # Check all rotations and all x positions
        for rotation in range(len(SHAPES[self.current.shape])):
            blocks = SHAPES[self.current.shape][rotation]
            min_x = -min(x for x,_ in blocks)
            max_x = COLS - max(x for x,_ in blocks) -1
            for x in range(min_x, max_x +1):
                result, score = self.place_and_score(self.board, self.current, x, rotation)
                if result is not None and score > best_score:
                    best_score = score
                    best_move = result  # (y, rotation, x)
        return best_move

    def generate_move_queue(self):
        move = self.pick_best_move()
        if move is None:
            return []
        _, rotation_target, x_target = move
        self.target_x = x_target
        self.target_rotation = rotation_target
        self.move_queue.clear()

        # Determine rotation moves needed
        rotation_diff = (self.target_rotation - self.current.rotation) % len(SHAPES[self.current.shape])
        for _ in range(rotation_diff):
            self.move_queue.append('rotate')

        # Determine horizontal moves needed
        dx = self.target_x - self.current.x
        if dx > 0:
            self.move_queue.extend(['right'] * dx)
        elif dx < 0:
            self.move_queue.extend(['left'] * (-dx))

    def step_move(self):
        if not self.move_queue:
            return
        move = self.move_queue.pop(0)
        if move == 'rotate':
            self.current.rotate()
            if not self.valid(self.current):
                self.current.rotate_back()  # undo rotation if invalid
        elif move == 'left':
            if self.valid(self.current, x=self.current.x -1):
                self.current.x -=1
        elif move == 'right':
            if self.valid(self.current, x=self.current.x +1):
                self.current.x +=1

    def hard_drop(self):
        while self.valid(self.current, y=self.current.y +1):
            self.current.y +=1
        self.freeze_piece()

    def freeze_piece(self):
        place_piece(self.board, self.current.blocks, self.current.x, self.current.y, self.current.color)
        self.board, cleared = clear_lines(self.board)
        if cleared > 0:
            self.lines_cleared += cleared
            self.score += (0, 40, 100, 300, 1200)[cleared] * (self.level + 1)
            self.level = self.lines_cleared // 10
            self.fall_delay = max(100, 600 - self.level * 50)
        self.current = self.next
        self.next = self.get_new_piece()
        self.target_x = None
        self.target_rotation = None
        self.move_queue.clear()
        if not self.valid(self.current):
            self.game_over = True

    def update(self):
        now = pygame.time.get_ticks()

        # If no moves queued, find best move
        if not self.move_queue and not self.game_over:
            self.generate_move_queue()

        # Step one move per frame to look human-like
        if self.move_queue and not self.game_over:
            self.step_move()

        # Auto piece fall timing
        if now - self.last_fall_time > self.fall_delay and not self.game_over:
            if self.valid(self.current, y=self.current.y + 1):
                self.current.y += 1
            else:
                # If moves remain, do hard drop after moving
                if self.move_queue:
                    # wait until move queue is empty before locking
                    pass
                else:
                    self.freeze_piece()
            self.last_fall_time = now

    def draw_board(self):
        for y in range(ROWS):
            for x in range(COLS):
                cell = self.board[y][x]
                rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(screen, COLORS['grid'], rect, 1)
                if cell:
                    pygame.draw.rect(screen, cell, rect.inflate(-2, -2))

    def draw_piece(self, piece, offset_x, offset_y):
        for x,y in piece.blocks:
            bx, by = offset_x + x, offset_y + y
            if by >= 0:
                rect = pygame.Rect(bx * CELL_SIZE, by * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(screen, piece.color, rect.inflate(-2, -2))

    def draw_sidebar(self):
        sidebar_x = COLS * CELL_SIZE + 20
        score_surf = font.render(f"Score: {self.score}", True, COLORS['text'])
        screen.blit(score_surf, (sidebar_x, 50))
        level_surf = font.render(f"Level: {self.level}", True, COLORS['text'])
        screen.blit(level_surf, (sidebar_x, 80))
        next_surf = font.render("Next:", True, COLORS['text'])
        screen.blit(next_surf, (sidebar_x, 130))
        for x,y in self.next.blocks:
            rect = pygame.Rect(sidebar_x + x * CELL_SIZE, 160 + y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, self.next.color, rect.inflate(-2, -2))

def main():
    game = TetrisAI()

    while not game.game_over:
        screen.fill(COLORS['bg'])
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        game.update()
        game.draw_board()
        game.draw_piece(game.current, game.current.x, game.current.y)
        game.draw_sidebar()

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
