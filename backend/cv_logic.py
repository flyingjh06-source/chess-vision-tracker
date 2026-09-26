import base64
import cv2
import numpy as np
import chess

class ChessGameTracker:
    def __init__(self):
        self.board = chess.Board()
        self.prev_board_img = None
        # Coordinates mapping for 8x8 grid (from A8 to H1)
        # Note: In standard chess, A8 is top-left, H1 is bottom-right from White's perspective.
        self.is_white_bottom = True

    def process_frame(self, image_b64: str):
        # Decode base64 image
        if ',' in image_b64:
            image_b64 = image_b64.split(',')[1]
        img_data = base64.b64decode(image_b64)
        np_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            return {"error": "Invalid image"}

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # In a real scenario, you'd find the 4 corners of the board here and warp it.
        # For simplicity, assuming the image is mostly the board (cropped by mobile).
        # We resize it to 800x800 for consistent 100x100 squares
        warped = cv2.resize(gray, (800, 800))
        
        # Blur to reduce noise
        warped = cv2.GaussianBlur(warped, (5, 5), 0)

        if self.prev_board_img is None:
            self.prev_board_img = warped
            return {"no_change": True}

        # Compute difference
        diff = cv2.absdiff(self.prev_board_img, warped)
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        
        # Check for hands (massive changes)
        total_changed = cv2.countNonZero(thresh)
        if total_changed > 150000: # Tune this threshold
            return {"error": "Hand or obstacle detected"}
        if total_changed < 2000:
            return {"no_change": True}

        # Calculate changes per square
        square_size = 100
        changes = []
        for row in range(8):
            for col in range(8):
                square_roi = thresh[row*square_size:(row+1)*square_size, col*square_size:(col+1)*square_size]
                changed_pixels = cv2.countNonZero(square_roi)
                
                # Convert row, col to chess square index (0-63)
                # If white is at the bottom:
                # row 0 is rank 8, row 7 is rank 1
                # col 0 is file A, col 7 is file H
                rank = 7 - row
                file_idx = col
                square_idx = chess.square(file_idx, rank)
                
                changes.append((changed_pixels, square_idx))

        # Sort by most changed
        changes.sort(key=lambda x: x[0], reverse=True)
        
        # Top 4 changed squares might be involved (e.g., castling)
        top_squares = [s[1] for s in changes[:4] if s[0] > 500]
        
        if len(top_squares) < 2:
            return {"no_change": True}

        # Find a legal move that matches the changed squares
        legal_moves = list(self.board.legal_moves)
        best_move = None
        
        for move in legal_moves:
            # For a normal move, from_square and to_square should both be in top_squares
            if move.from_square in top_squares and move.to_square in top_squares:
                best_move = move
                break
                
        if best_move:
            self.board.push(best_move)
            self.prev_board_img = warped
            return {
                "moved": True,
                "move": best_move.uci(),
                "fen": self.board.fen(),
                "is_game_over": self.board.is_game_over()
            }
        else:
            return {"error": "Move not recognized as legal"}
