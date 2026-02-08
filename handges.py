import cv2
import pyautogui
import numpy as np
from mediapipe.python.solutions import hands as mp_hands
from mediapipe.python.solutions import drawing_utils as mp_draw

# --- CONFIG ---
CAM_W, CAM_H = 640, 480
SCREEN_W, SCREEN_H = pyautogui.size()
pyautogui.FAILSAFE = True

hands = mp_hands.Hands(model_complexity=0, max_num_hands=2, min_detection_confidence=0.8)
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

p_locX, p_locY = 0, 0
smooth_factor = 4 
is_dragging = False

while cap.isOpened():
    success, img = cap.read()
    if not success: break
    img = cv2.flip(img, 1)
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    if results.multi_hand_landmarks:
        for hand_lms, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            # Locked to Right Hand only
            if handedness.classification[0].label == "Right":
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
                lm = [[int(l.x * CAM_W), int(l.y * CAM_H)] for l in hand_lms.landmark]

                # Finger states (Comparing Tip to Middle Joint)
                index_bent = lm[8][1] > lm[6][1]
                middle_bent = lm[12][1] > lm[10][1]
                ring_bent = lm[16][1] > lm[14][1]
                pinky_bent = lm[20][1] > lm[18][1]
                
                # Anchor Point: Middle Knuckle (Landmark 9)
                anchor_x, anchor_y = lm[9][0], lm[9][1]

                # --- 1. GRAB & DRAG LOGIC (Fist) ---
                is_fist = index_bent and middle_bent and ring_bent and pinky_bent
                is_open = not index_bent and not middle_bent and not ring_bent

                if is_fist:
                    if not is_dragging:
                        pyautogui.mouseDown()
                        is_dragging = True
                    cv2.putText(img, "DRAGGING", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                elif is_open and is_dragging:
                    pyautogui.mouseUp()
                    is_dragging = False

                # --- 2. SCROLL LOGIC (Ring finger bent, Index/Middle Straight) ---
                # Restore: Scrolls based on palm height when only the ring finger is tucked
                elif ring_bent and not index_bent and not middle_bent:
                    diff = (CAM_H // 2) - anchor_y
                    if abs(diff) > 40:
                        scroll_speed = int(diff / 2)
                        pyautogui.scroll(scroll_speed)
                        cv2.putText(img, "SCROLLING", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                # --- 3. CLICKING LOGIC (Only if not dragging/scrolling) ---
                elif not is_dragging:
                    if index_bent and not middle_bent:
                        pyautogui.click()
                        pyautogui.sleep(0.2)
                    elif middle_bent and not index_bent:
                        pyautogui.rightClick()
                        pyautogui.sleep(0.2)

                # --- 4. CONTINUOUS STABLE MOVEMENT ---
                # Move based on Palm Center (Anchor 9)
                x_m = np.interp(anchor_x, (110, CAM_W-110), (0, SCREEN_W))
                y_m = np.interp(anchor_y, (110, CAM_H-110), (0, SCREEN_H))
                
                curr_x = p_locX + (x_m - p_locX) / smooth_factor
                curr_y = p_locY + (y_m - p_locY) / smooth_factor
                
                pyautogui.moveTo(curr_x, curr_y, _pause=False)
                p_locX, p_locY = curr_x, curr_y

    cv2.imshow("The Complete Air Mouse", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()