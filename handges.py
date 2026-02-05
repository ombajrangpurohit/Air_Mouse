import cv2
import mediapipe as mp
import pyautogui
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
smooth_factor = 4  # Increased for smoother palm tracking
mouse_pressed = False

while cap.isOpened():
    success, img = cap.read()
    if not success: break
    img = cv2.flip(img, 1)
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    if results.multi_hand_landmarks:
        for hand_lms, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            if handedness.classification[0].label == "Right":
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
                lm = [[int(l.x * CAM_W), int(l.y * CAM_H)] for l in hand_lms.landmark]

                # --- GESTURE DETECTION ---
                # Compare Tips to Knuckles/PIP joints
                index_bent = lm[8][1] > lm[6][1]
                middle_bent = lm[12][1] > lm[10][1]
                ring_bent = lm[16][1] > lm[14][1]
                pinky_bent = lm[20][1] > lm[18][1]
                
                is_fist = index_bent and middle_bent and ring_bent and pinky_bent
                
                # --- STABLE ANCHOR: Palm Center (MCP of Middle Finger) ---
                # Using Landmark 9 (Middle Finger MCP) as the anchor for the cursor
                anchor_x, anchor_y = lm[9][0], lm[9][1]

                # --- LOGIC GATE: Priority System ---
                
                # 1. DRAG/FIST LOGIC
                if is_fist:
                    if not mouse_pressed:
                        pyautogui.mouseDown()
                        mouse_pressed = True
                    cv2.putText(img, "DRAGGING", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # 2. RIGHT CLICK (Middle bent, Index straight)
                elif middle_bent and not index_bent:
                    pyautogui.rightClick()
                    cv2.putText(img, "RIGHT CLICK", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    pyautogui.sleep(0.2)
                
                # 3. LEFT CLICK (Index bent, Middle straight)
                elif index_bent and not middle_bent:
                    if mouse_pressed: # Release drag if we were dragging
                        pyautogui.mouseUp()
                        mouse_pressed = False
                    pyautogui.click()
                    cv2.putText(img, "LEFT CLICK", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    pyautogui.sleep(0.2)

                # 4. SCROLL LOGIC (Ring finger bent, others straight)
                elif ring_bent and not index_bent and not middle_bent:
                    diff = (CAM_H // 2) - anchor_y
                    if abs(diff) > 40:
                        pyautogui.scroll(int(diff / 2))
                
                # 5. MOUSE MOVEMENT (Only if no click is happening)
                else:
                    if mouse_pressed: # If fist opened, release mouse
                        pyautogui.mouseUp()
                        mouse_pressed = False
                        
                    # Map the Palm Anchor (9) to the screen
                    x_m = np.interp(anchor_x, (100, CAM_W-100), (0, SCREEN_W))
                    y_m = np.interp(anchor_y, (100, CAM_H-100), (0, SCREEN_H))
                    
                    curr_x = p_locX + (x_m - p_locX) / smooth_factor
                    curr_y = p_locY + (y_m - p_locY) / smooth_factor
                    
                    pyautogui.moveTo(curr_x, curr_y, _pause=False)
                    p_locX, p_locY = curr_x, curr_y

    cv2.imshow("Palm-Anchored Air Mouse", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()