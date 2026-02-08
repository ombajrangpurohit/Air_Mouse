import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math
import speech_recognition as sr
import threading
import asyncio
import edge_tts
import pygame
from textblob import TextBlob
from deep_translator import GoogleTranslator
from google import genai 
from mediapipe.python.solutions import hands as mp_hands
from mediapipe.python.solutions import drawing_utils as mp_draw

# --- FAFNIR VOICE & AI CONFIG ---
pygame.mixer.init()
client = genai.Client(api_key="AIzaSyDBSMeCSnzT_A0JV1a00vyKLfbaOuBT7xg")
MODEL_ID = "gemini-1.5-flash"

async def generate_human_voice(text, emotion):
    voice = "en-IN-NeerjaNeural"
    rate = "+15%" if emotion == "happy" else "-10%" if emotion == "sad" else "+0%"
    pitch = "+5Hz" if emotion == "happy" else "-5Hz" if emotion == "sad" else "+0Hz"
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save("temp_voice.mp3")

def speak(text, emotion="neutral"):
    print(f"Fafnir: {text}")
    try:
        asyncio.run(generate_human_voice(text, emotion))
        pygame.mixer.music.load("temp_voice.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
    except Exception as e: print(f"Audio Error: {e}")

def listen_and_process():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        # VISUAL LOGGING
        print(">>> STARTING MICROPHONE: Fafnir is listening...")
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            raw_query = recognizer.recognize_google(audio, language="hi-IN")
            query = GoogleTranslator(source='auto', target='en').translate(raw_query).lower()
            analysis = TextBlob(query)
            emotion = "happy" if analysis.sentiment.polarity > 0.3 else "neutral"
            response = client.models.generate_content(model=MODEL_ID, contents=query)
            clean_text = response.text.replace("*", "").replace("#", "")
            speak(clean_text, emotion)
        except Exception as e:
            print(f"Fafnir Recognition Error: {e}")

# --- AIR MOUSE CONFIG ---
CAM_W, CAM_H = 640, 480
SCREEN_W, SCREEN_H = pyautogui.size()
pyautogui.FAILSAFE = True

mp_hands_sol = mp.solutions.hands
hands = mp_hands_sol.Hands(model_complexity=0, max_num_hands=2, min_detection_confidence=0.7)

cap = cv2.VideoCapture(0)
p_locX, p_locY = 0, 0
smooth_factor, is_dragging = 4, False
box_points = []
voice_active = False

while cap.isOpened():
    success, img = cap.read()
    if not success: break
    img = cv2.flip(img, 1)
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    # --- STATUS HUD ---
    status_color = (0, 0, 255) if not voice_active else (0, 255, 0)
    cv2.circle(img, (30, 30), 15, status_color, cv2.FILLED)
    cv2.putText(img, "ASSISTANT READY" if not voice_active else "LISTENING", (60, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    if results.multi_hand_landmarks:
        for hand_lms, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            label = handedness.classification[0].label
            lm = [[int(l.x * CAM_W), int(l.y * CAM_H)] for l in hand_lms.landmark]
            
            # Use distance between thumb base and index base for dynamic scaling
            scale = math.hypot(lm[5][0] - lm[2][0], lm[5][1] - lm[2][1])

            # --- LEFT HAND: RE-ENGINEERED TRIGGER ---
            if label == "Left":
                dist_voice = math.hypot(lm[8][0] - lm[4][0], lm[8][1] - lm[4][1])
                # INCREASED THRESHOLD: scale * 0.6 makes it easier to trigger
                if dist_voice < (scale * 0.6) and not voice_active:
                    voice_active = True
                    print("--- GESTURE DETECTED: TRIGGERING THREAD ---")
                    threading.Thread(target=listen_and_process).start()
                    # Timer ensures it resets even if recognition fails
                    threading.Timer(8.0, lambda: globals().update(voice_active=False)).start()
                
                mp_draw.draw_landmarks(img, hand_lms, mp_hands_sol.HAND_CONNECTIONS)

            # --- RIGHT HAND: MOUSE & HOLOGRAPHIC ---
            elif label == "Right":
                # Cursor/Click logic remains same to avoid changing existing functionality
                index_bent = lm[8][1] > lm[6][1]
                middle_bent = lm[12][1] > lm[10][1]
                anchor_x, anchor_y = lm[9][0], lm[9][1]

                # Holographic Trail
                dist_holograph = math.hypot(lm[8][0] - lm[4][0], lm[8][1] - lm[4][1])
                if dist_holograph < 35:
                    box_points.append((lm[8][0], lm[8][1]))
                else: box_points = []

                # Smooth Movement
                x_m = np.interp(anchor_x, (110, CAM_W-110), (0, SCREEN_W))
                y_m = np.interp(anchor_y, (110, CAM_H-110), (0, SCREEN_H))
                curr_x = p_locX + (x_m - p_locX) / smooth_factor
                curr_y = p_locY + (y_m - p_locY) / smooth_factor
                pyautogui.moveTo(curr_x, curr_y, _pause=False)
                p_locX, p_locY = curr_x, curr_y
                mp_draw.draw_landmarks(img, hand_lms, mp_hands_sol.HAND_CONNECTIONS)

    # Render Holographic Trail
    for pt in box_points:
        cv2.rectangle(img, (pt[0]-10, pt[1]-10), (pt[0]+10, pt[1]+10), (255, 255, 0), 2)

    cv2.imshow("Fafnir Air Mouse Debug Mode", img)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()