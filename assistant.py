import speech_recognition as sr
import google.genai as ai
from google.genai import types
import os, pygame, asyncio, edge_tts, webbrowser, pyautogui
import time as t

# --- CONFIG ---
# Get your key from https://aistudio.google.com/
API_KEY = "API_KEY" # 1. Get a fresh key from AI Studio
client = ai.Client(api_key=API_KEY)

# --- AUTOMATION TOOLS ---
def open_app(app_name: str):
    """Opens VS Code, WhatsApp, or any app via Windows search."""
    pyautogui.press('win')
    t.sleep(0.5)
    pyautogui.write(app_name)
    t.sleep(0.8)
    pyautogui.press('enter')
    return f"Opening {app_name}, Sir."

def play_youtube(topic: str):
    """Searches and automatically plays the first result."""
    url = f"https://www.youtube.com/results?search_query={topic.replace(' ', '+')}"
    webbrowser.open(url)
    
    # Wait for the search results to load fully
    t.sleep(6) 
    
    # Click the first video (coordinates calibrated for standard 1080p layout)
    # If this misses, try pyautogui.press('enter') as a fallback
    pyautogui.click(x=640, y=420) 
    return f"Playing the top result for {topic} on YouTube."

def type_content(text_to_type: str):
    """Types text directly into the active window (like VS Code)."""
    t.sleep(2) # Time for you to click the right window
    pyautogui.write(text_to_type, interval=0.02)
    return "The content has been written as requested."

# --- INTEGRATED PROJECT TOOLS ---
def start_attendance_system():
    """Triggers your Smart Attendance face recognition logic."""
    # Add your script execution here (e.g., os.system('python attendance.py'))
    return "Face recognition initialized. Attendance system is active."

def check_soil_moisture():
    """Reads data from your Arduino project."""
    # Add your Serial communication logic here
    return "Sensors checked. The moisture level is perfect for your plants."

# --- AI CORE SETUP ---
my_tools = [open_app, play_youtube, type_content, start_attendance_system, check_soil_moisture]

async def generate_voice(text):
    """Generates audio with a dynamic filename to avoid OneDrive locks."""
    # Try a different voice to see if the server for Sonia is the issue
    communicate = edge_tts.Communicate(text, "en-US-GuyNeural", rate="+10%")
    await communicate.save("temp_voice_test.mp3")

def speak(text):
    if not text.strip(): # Don't try to speak empty text
        return
        
    print(f"axiom: {text}")
    try:
        # Using a fresh event loop for every speak call to prevent 'No audio' errors
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(generate_voice(text))
        loop.close()

        # Small delay to let the file system catch up
        t.sleep(0.3)

        if os.path.exists("temp_voice_test.mp3"):
            pygame.mixer.init()
            pygame.mixer.music.load("temp_voice_test.mp3")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                t.sleep(0.1)
            pygame.mixer.music.unload()
            
            # Clean up carefully
            try:
                os.remove("temp_voice_test.mp3")
            except:
                pass 
        else:
            print("(!) Audio file was never created.")

    except Exception as e:
        print(f"Voice Error: {e}")

def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("\n Listening...")
        try:
            # We use a short phrase limit to keep axiom snappy
            audio = recognizer.listen(source, phrase_time_limit=5)
            query = recognizer.recognize_google(audio)
            print(f"User: {query}")
            return query
        except: return ""

def run_axiom():
    chat = client.chats.create(
        model="gemini-2.0-flash-lite", 
        config=types.GenerateContentConfig(
            tools=my_tools,
            system_instruction="You are axiom. Sleek and professional. Use tools for PC control."
        )
    )
    
    speak("axiom is online. Standing by, Sir.")
    
    while True:
        query = listen()
        if not query: continue
        
        if any(x in query.lower() for x in ["exit", "shutdown", "sleep"]):
            speak("Understood. Powering down.")
            break

        # --- SMART RETRY LOGIC FOR 429 ERRORS ---
        success = False
        attempts = 0
        while not success and attempts < 3:
            try:
                response = chat.send_message(query)
                speak(response.text)
                success = True
            except Exception as e:
                if "429" in str(e):
                    attempts += 1
                    print(f"(!) Quota hit. Retrying in 10s... (Attempt {attempts}/3)")
                    t.sleep(10) # Wait for the quota to reset
                else:
                    print(f"Error: {e}")
                    speak("I encountered a system error.")
                    break # Stop retrying for non-quota errors

if __name__ == "__main__":
 run_axiom()