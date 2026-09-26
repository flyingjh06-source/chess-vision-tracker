import base64
import cv2
import numpy as np
import chess

class ChessGameTracker:
    def __init__(self):
        self.board = chess.Board()
        self.prev_board_img = None
        self.board_corners = None
        self.auto_orientation = None
        self.error_count = 0
        self.current_border_inset = '0'

    def order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)] # Top-left
        rect[2] = pts[np.argmax(s)] # Bottom-right
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)] # Top-right
        rect[3] = pts[np.argmax(diff)] # Bottom-left
        return rect

    def auto_detect_orientation(self, warped):
        means = {
            '0': np.mean(warped[600:800, :]),    # Bottom has White
            '180': np.mean(warped[0:200, :]),    # Top has White
            '90': np.mean(warped[:, 600:800]),   # Right has White
            '270': np.mean(warped[:, 0:200])     # Left has White
        }
        return max(means, key=means.get)

    def process_frame(self, image_b64: str, orientation='0', border_inset='0'):
        if self.current_border_inset != border_inset:
            self.prev_board_img = None
            self.current_border_inset = border_inset
            
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
            self.auto_orientation = None
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
                self.board_corners = np.array([[0,0], [w,0], [w,h], [0,h]], dtype="float32")

        response = {"board_corners": self.board_corners.tolist()}

        # 2. Warp to perfect 800x800 orthogonal grid
        dst = np.array([[0,0], [800,0], [800,800], [0,800]], dtype="float32")
        M = cv2.getPerspectiveTransform(self.board_corners, dst)
        warped = cv2.warpPerspective(gray, M, (800, 800))
        
        # Apply border inset crop if the user tapped the outer wooden frame
        try:
            inset_val = float(border_inset)
        except ValueError:
            inset_val = 0.0
            
        inset_px = int(800 * inset_val)
        if inset_px > 0:
            pts1 = np.float32([[inset_px, inset_px], [800-inset_px, inset_px], [800-inset_px, 800-inset_px], [inset_px, 800-inset_px]])
            pts2 = np.float32([[0,0], [800,0], [800,800], [0,800]])
            M2 = cv2.getPerspectiveTransform(pts1, pts2)
            warped = cv2.warpPerspective(warped, M2, (800, 800))
        
        # Apply user-defined or auto rotation to match White's perspective
        if orientation == 'auto':
            if getattr(self, 'auto_orientation', None) is None:
                self.auto_orientation = self.auto_detect_orientation(warped)
            active_orientation = self.auto_orientation
            response["orientation"] = active_orientation
        else:
            self.auto_orientation = None
            active_orientation = orientation

        if active_orientation == '90':
            warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)
        elif active_orientation == '180':
            warped = cv2.rotate(warped, cv2.ROTATE_180)
        elif active_orientation == '270':
            warped = cv2.rotate(warped, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        warped = cv2.GaussianBlur(warped, (15, 15), 0)

        if self.prev_board_img is None:
            self.prev_board_img = warped
            response["no_change"] = True
            return response

        # 3. Brightness match & Diff
        mean_prev = cv2.mean(self.prev_board_img)[0]
        mean_curr = cv2.mean(warped)[0]
        beta = int(mean_prev - mean_curr)
        
        # Safely adjust brightness without absolute value folding
        if beta > 0:
            warped_adj = cv2.add(warped, np.array([beta], dtype=np.uint8))
        elif beta < 0:
            warped_adj = cv2.subtract(warped, np.array([-beta], dtype=np.uint8))
        else:
            warped_adj = warped.copy()

        # Intensity diff (lowered threshold to catch camouflaged pieces)
        diff_intensity = cv2.absdiff(self.prev_board_img, warped_adj)
        _, thresh_intensity = cv2.threshold(diff_intensity, 25, 255, cv2.THRESH_BINARY)
        
        # Structural Edge diff (immune to camouflage and shadows)
        edges_prev = cv2.Canny(self.prev_board_img, 40, 120)
        edges_curr = cv2.Canny(warped_adj, 40, 120)
        diff_edges = cv2.absdiff(edges_prev, edges_curr)
        diff_edges = cv2.dilate(diff_edges, np.ones((5,5), np.uint8))
        
        # Combine intensity and structural changes
        thresh = cv2.bitwise_or(thresh_intensity, diff_edges)
        
        kernel = np.ones((5,5), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        total_changed = cv2.countNonZero(thresh)
        
        # 4. Error handling & Self-healing
        if total_changed > 100000:
            self.error_count += 1
            if self.error_count >= 3:
                # Only reset baseline image, keep manual corners!
                self.prev_board_img = warped
                self.error_count = 0
                response["error"] = "Camera shifted. Baseline reset."
                return response
            
            response["error"] = "Hand or obstacle detected"
            return response
            
        self.error_count = 0

        if total_changed < 1000:
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
        # INCLUDE ALL squares with significant changes, don't cap at 4 (shadows could push real moves down)
        top_squares = [s[1] for s in changes if s[0] > 400]
        
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
