import cv2
import numpy as np

# Create two fake boards with SAME intensity
prev = np.zeros((800, 800), dtype=np.uint8)
curr = np.zeros((800, 800), dtype=np.uint8)

# Instead of filled circle, let's just make edges
edges = np.zeros((800, 800), dtype=np.uint8)
cv2.circle(edges, (450, 450), 30, 255, 1)

diff_edges = cv2.dilate(edges, np.ones((5,5), np.uint8))
before = cv2.countNonZero(diff_edges)

thresh = cv2.morphologyEx(diff_edges, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))
after = cv2.countNonZero(thresh)

print(f"Edges before open: {before}, After open: {after}")
