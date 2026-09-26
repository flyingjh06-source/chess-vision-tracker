import cv2
import numpy as np

# Create fragmented edges (random dots along a circle)
edges = np.zeros((800, 800), dtype=np.uint8)
for angle in range(0, 360, 15):
    x = int(450 + 30 * np.cos(np.radians(angle)))
    y = int(450 + 30 * np.sin(np.radians(angle)))
    edges[y, x] = 255 # Only 1 pixel dots!

diff_edges = cv2.dilate(edges, np.ones((5,5), np.uint8))
before = cv2.countNonZero(diff_edges)

thresh = cv2.morphologyEx(diff_edges, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))
after = cv2.countNonZero(thresh)

print(f"Before OPEN: {before}")
print(f"After OPEN: {after}")
