import cv2, pyautogui, numpy as np, os, pygame, asyncio, edge_tts, webbrowser, threading
import speech_recognition as sr
import google.genai as ai  # Your preferred library
from google.genai import types
from mediapipe.python.solutions import hands as mp_hands
from mediapipe.python.solutions import drawing_utils as mp_draw
import time as t

# --- 1. SETTINGS ---
API_KEY = "API_KEY" # 1. Get a fresh key from AI Studio
client = ai.Client(api_key=API_KEY)
MODEL_ID = "gemini-flash-latest" # 2. Use just the name, no 'models/' prefix

CAM_W, CAM_H = 640, 480
SCREEN_W, SCREEN_H = pyautogui.size()
pyautogui.FAILSAFE = False 
is_system_active = True

# --- 2. VOICE TOOLS (FULL RESTORATION) ---
def open_app(app_name: str):
    pyautogui.press('win'); t.sleep(0.5)
    pyautogui.write(app_name); t.sleep(0.8); pyautogui.press('enter')
    return f"Opening {app_name}, Sir."

def play_youtube(topic: str):
    url = f"https://www.youtube.com/results?search_query={topic.replace(' ', '+')}"
    webbrowser.open(url); t.sleep(6) 
    pyautogui.click(x=640, y=420) 
    return f"Playing top result for {topic}."

def type_content(text_to_type: str):
    t.sleep(2) 
    pyautogui.write(text_to_type, interval=0.02)
    return "Content written."

def start_attendance_system():
    # os.system('python attendance.py')
    return "Smart Attendance face recognition is now online."

def check_soil_moisture():
    return "The moisture level is perfect for your plants."

# --- 3. THE BACKGROUND VOICE THREAD ---
class AxiomVoice(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.tools = [open_app, play_youtube, type_content, start_attendance_system, check_soil_moisture]

    async def generate_voice(self, text):
        comm = edge_tts.Communicate(text, "en-US-GuyNeural", rate="+10%")
        await comm.save("temp.mp3")

    def speak(self, text):
        print(f"axiom: {text}")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.generate_voice(text))
            pygame.mixer.init()
            pygame.mixer.music.load("temp.mp3")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy(): t.sleep(0.1)
            pygame.mixer.music.unload()
            os.remove("temp.mp3")
        except: pass

    def listen(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("\nListening...")
            try:
                audio = r.listen(source, phrase_time_limit=5)
                return r.recognize_google(audio)
            except: return ""

    def run(self):
        chat = client.chats.create(
            model=MODEL_ID, 
            config=types.GenerateContentConfig(
                tools=self.tools, 
                system_instruction="You are axiom. Use tools for PC control and project automation."
            )
        )
        self.speak("Axiom is online. Gesture and Voice ready.")
        global is_system_active
        while is_system_active:
            query = self.listen()
            if not query: continue
            if any(x in query.lower() for x in ["exit", "shutdown"]):
                self.speak("Powering down.")
                is_system_active = False; break
            try:
                response = chat.send_message(query)
                self.speak(response.text)
            except Exception as e: print(f"AI Error: {e}")

# --- 4. THE GESTURE MAIN LOOP ---
def run_gestures():
    hands = mp_hands.Hands(model_complexity=0, max_num_hands=1, min_detection_confidence=0.8)
    cap = cv2.VideoCapture(0)
    p_locX, p_locY = 0, 0
    is_dragging = False

    while cap.isOpened() and is_system_active:
        success, img = cap.read()
        if not success: break
        img = cv2.flip(img, 1)
        results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        if results.multi_hand_landmarks:
            for hand_lms in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
                lm = [[int(l.x * CAM_W), int(l.y * CAM_H)] for l in hand_lms.landmark]

                # Finger states
                index_bent = lm[8][1] > lm[6][1]
                middle_bent = lm[12][1] > lm[10][1]
                ring_bent = lm[16][1] > lm[14][1]
                pinky_bent = lm[20][1] > lm[18][1]
                anchor_x, anchor_y = lm[9][0], lm[9][1]

                # --- 1. DRAG (Fist) ---
                if index_bent and middle_bent and ring_bent and pinky_bent:
                    if not is_dragging:
                        pyautogui.mouseDown(); is_dragging = True
                elif not index_bent and not middle_bent and is_dragging:
                    pyautogui.mouseUp(); is_dragging = False

                # --- 2. SCROLL (Ring bent only) ---
                elif ring_bent and not index_bent and not middle_bent:
                    diff = (CAM_H // 2) - anchor_y
                    if abs(diff) > 40: pyautogui.scroll(int(diff / 2))

                # --- 3. CLICK (Left=Index, Right=Middle) ---
                elif not is_dragging:
                    if index_bent and not middle_bent:
                        pyautogui.click(); t.sleep(0.2)
                    elif middle_bent and not index_bent:
                        pyautogui.rightClick(); t.sleep(0.2)

                # --- 4. STABLE MOVEMENT ---
                x_m = np.interp(anchor_x, (110, CAM_W-110), (0, SCREEN_W))
                y_m = np.interp(anchor_y, (110, CAM_H-110), (0, SCREEN_H))
                p_locX = p_locX + (x_m - p_locX) / 4
                p_locY = p_locY + (y_m - p_locY) / 4
                pyautogui.moveTo(p_locX, p_locY, _pause=False)

        cv2.imshow("Axiom Interface", img)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    va = AxiomVoice()
    va.start()
    run_gestures()