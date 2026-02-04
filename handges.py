import cv2
import mediapipe as mp
import pyautogui
import math
import numpy as np
from mediapipe.python.solutions import hands as mp_hands
from mediapipe.python.solutions import drawing_utils as mp_draw

# --- CONFIG ---
CAM_W, CAM_H = 640, 480
SCREEN_W, SCREEN_H = pyautogui.size()
pyautogui.FAILSAFE = True

hands = mp_hands.Hands(model_complexity=0, max_num_hands=1, min_detection_confidence=0.8)
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

p_locX, p_locY = 0, 0
smooth_factor = 3
dragging = False

# --- MANUAL MODE SELECTION ---
print("Select Mode: 1 for MOUSE, 2 for VOLUME")
choice = input("Enter choice: ")
current_mode = "MOUSE" if choice == '1' else "MEDIA"

while cap.isOpened():
    success, img = cap.read()
    if not success: break
    img = cv2.flip(img, 1)
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    if results.multi_hand_landmarks:
        for hand_lms in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
            lm_list = [[int(lm.x * CAM_W), int(lm.y * CAM_H)] for lm in hand_lms.landmark]

            # Landmarks: Wrist(0), Thumb(4), Index(8), Middle(12), Pinky(20)
            ttip, itip, mtip, ptip = lm_list[4], lm_list[8], lm_list[12], lm_list[20]
            scale = math.hypot(lm_list[5][0] - lm_list[0][0], lm_list[5][1] - lm_list[0][1])

            # Finger States (Strictly Up or Down)
            index_up = itip[1] < lm_list[6][1]
            middle_up = mtip[1] < lm_list[10][1]
            pinky_up = ptip[1] < lm_list[18][1]

            # --- DYNAMIC MODE SWITCH (Via Pinky) ---
            if pinky_up: current_mode = "MEDIA"
            else: current_mode = "MOUSE"

            cv2.putText(img, f"MODE: {current_mode}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            if current_mode == "MEDIA":
                # Volume Logic: Hand position relative to center
                if itip[1] < (CAM_H // 2 - 60):
                    pyautogui.press('volumeup')
                    cv2.putText(img, "VOL UP", (250, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                elif itip[1] > (CAM_H // 2 + 60):
                    pyautogui.press('volumedown')
                    cv2.putText(img, "VOL DOWN", (250, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            elif current_mode == "MOUSE":
                # 1. RIGHT CLICK (Middle touches Thumb AND Index is DOWN)
                dist_right = math.hypot(mtip[0] - ttip[0], mtip[1] - ttip[1])
                if dist_right < (scale * 0.4) and not index_up:
                    pyautogui.rightClick()
                    cv2.circle(img, (mtip[0], mtip[1]), 20, (0, 0, 255), cv2.FILLED)
                    pyautogui.sleep(0.2)
                    continue

                # 2. SCROLL (Index & Middle are both UP)
                if index_up and middle_up:
                    diff = (CAM_H // 2) - mtip[1]
                    if abs(diff) > 40:
                        pyautogui.scroll(int(diff / 2))
                
                # 3. MOUSE & LEFT CLICK/DRAG (Index is UP and Middle is DOWN)
                elif index_up and not middle_up:
                    # Smoothing movement
                    x_m = np.interp(itip[0], (80, CAM_W-80), (0, SCREEN_W))
                    y_m = np.interp(itip[1], (80, CAM_H-80), (0, SCREEN_H))
                    curr_x = p_locX + (x_m - p_locX) / smooth_factor
                    curr_y = p_locY + (y_m - p_locY) / smooth_factor
                    pyautogui.moveTo(curr_x, curr_y, _pause=False)
                    p_locX, p_locY = curr_x, curr_y

                    # Left Click / Drag
                    dist_left = math.hypot(itip[0] - ttip[0], itip[1] - ttip[1])
                    if dist_left < (scale * 0.4):
                        if not dragging:
                            pyautogui.mouseDown()
                            dragging = True
                        cv2.circle(img, (itip[0], itip[1]), 15, (0, 255, 0), cv2.FILLED)
                    else:
                        if dragging:
                            pyautogui.mouseUp()
                            dragging = False

    cv2.imshow("Final Air Mouse Pro", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()