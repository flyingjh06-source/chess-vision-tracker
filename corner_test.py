import cv2
import numpy as np

img = cv2.imread('test_board.png')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

blur = cv2.GaussianBlur(gray, (5, 5), 0)
edges = cv2.Canny(blur, 30, 100)
edges = cv2.dilate(edges, np.ones((5,5), np.uint8), iterations=2)

contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contours = sorted(contours, key=cv2.contourArea, reverse=True)

out = img.copy()
found = False
for c in contours[:5]:
    hull = cv2.convexHull(c)
    peri = cv2.arcLength(hull, True)
    approx = cv2.approxPolyDP(hull, 0.05 * peri, True)
    
    if len(approx) == 4 and cv2.contourArea(approx) > 50000:
        cv2.drawContours(out, [approx], 0, (0, 255, 0), 3)
        print("Found 4 points!")
        found = True
        break

if not found:
    print("Not found")

cv2.imwrite('hull_test.png', out)
