import base64
import cv2
import numpy as np
import chess

class ChessGameTracker:
    def __init__(self):
        self.board = chess.Board()
        self.prev_board_img = None
        self.board_corners = None
        self.error_count = 0

    def order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)] # Top-left
        rect[2] = pts[np.argmax(s)] # Bottom-right
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)] # Top-right
        rect[3] = pts[np.argmax(diff)] # Bottom-left
        return rect

    def process_frame(self, image_b64: str):
        if ',' in image_b64:
            image_b64 = image_b64.split(',')[1]
        img_data = base64.b64decode(image_b64)
        np_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            return {"error": "Invalid image"}

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # 1. Detect Board Outline if not locked
        if self.board_corners is None:
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blur, 50, 150)
            edges = cv2.dilate(edges, np.ones((5,5), np.uint8), iterations=1)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            
            found = False
            for c in contours[:5]:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.03 * peri, True)
                if len(approx) == 4:
                    self.board_corners = self.order_points(approx.reshape(4, 2))
                    found = True
                    break
            
            if not found:
                # Fallback to whole image if no square found
                self.board_corners = np.array([[0,0], [w,0], [w,h], [0,h]], dtype="float32")

        # Prepare response object to include corners
        response = {"board_corners": self.board_corners.tolist()}

        # 2. Warp to perfect 800x800 orthogonal grid
        dst = np.array([[0,0], [800,0], [800,800], [0,800]], dtype="float32")
        M = cv2.getPerspectiveTransform(self.board_corners, dst)
        warped = cv2.warpPerspective(gray, M, (800, 800))
        
        warped = cv2.GaussianBlur(warped, (15, 15), 0)

        if self.prev_board_img is None:
            self.prev_board_img = warped
            response["no_change"] = True
            return response

        # 3. Brightness match & Diff
        mean_prev = cv2.mean(self.prev_board_img)[0]
        mean_curr = cv2.mean(warped)[0]
        warped = cv2.convertScaleAbs(warped, alpha=1.0, beta=mean_prev - mean_curr)

        diff = cv2.absdiff(self.prev_board_img, warped)
        _, thresh = cv2.threshold(diff, 40, 255, cv2.THRESH_BINARY)
        
        kernel = np.ones((7,7), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        total_changed = cv2.countNonZero(thresh)
        
        # 4. Error handling & Self-healing
        if total_changed > 100000:
            self.error_count += 1
            if self.error_count >= 3:
                # Hard reset everything if stuck
                self.prev_board_img = None
                self.board_corners = None
                self.error_count = 0
                response["error"] = "Camera shifted. Recalibrating board..."
                return response
            
            response["error"] = "Hand or obstacle detected"
            return response
            
        self.error_count = 0

        if total_changed < 2000:
            response["no_change"] = True
            return response

        # 5. Find Moved Squares
        square_size = 100
        changes = []
        for row in range(8):
            for col in range(8):
                square_roi = thresh[row*square_size:(row+1)*square_size, col*square_size:(col+1)*square_size]
                changed_pixels = cv2.countNonZero(square_roi)
                
                rank = 7 - row
                file_idx = col
                square_idx = chess.square(file_idx, rank)
                changes.append((changed_pixels, square_idx))

        changes.sort(key=lambda x: x[0], reverse=True)
        top_squares = [s[1] for s in changes[:4] if s[0] > 500]
        
        if len(top_squares) < 2:
            response["no_change"] = True
            return response

        legal_moves = list(self.board.legal_moves)
        valid_moves = []
        
        for move in legal_moves:
            if move.from_square in top_squares and move.to_square in top_squares:
                score = sum([c[0] for c in changes if c[1] == move.from_square or c[1] == move.to_square])
                valid_moves.append((score, move))
                
        if valid_moves:
            valid_moves.sort(key=lambda x: x[0], reverse=True)
            best_move = valid_moves[0][1]
            
            self.board.push(best_move)
            self.prev_board_img = warped
            
            response["moved"] = True
            response["move"] = best_move.uci()
            response["fen"] = self.board.fen()
            response["is_game_over"] = self.board.is_game_over()
            return response
        else:
            response["error"] = "Move not recognized as legal"
            return response
