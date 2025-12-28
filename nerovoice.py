import pyttsx3
import datetime
import speech_recognition as sr
import wikipedia
import webbrowser
import os
import random
import time
import requests
import json
import tkinter as tk
from tkinter import scrolledtext, ttk
from threading import Thread
from PIL import Image, ImageTk
import sounddevice as sd
import numpy as np
import speech_recognition as sr


# ---------------- CONFIG ----------------
OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_URL = "http://localhost:11434"
LISTENING_DURATION = 5 
LISTENING_COOLDOWN = 2  

# Global variables for GUI elements
root = None
conversation_area = None
status_label = None
toggle_listen_button = None
ollama_available = False
listener = None
update_gui = True

# ---------------- SPEECH ----------------
def speak(text):
    try:
        if update_gui:
            update_conversation(f"DingDongShop: {text}\n")
        print(f"Speaking: {text}")
        engine = pyttsx3.init('sapi5')
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[1].id)
        engine.setProperty('rate', 175)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        time.sleep(0.5)
    except Exception as e:
        error_msg = f"[ERROR] Speaking failed: {e}"
        print(error_msg)
        if update_gui:
            update_conversation(f"{error_msg}\n")

def wishMe():
    hour = int(datetime.datetime.now().hour)
    greeting = "Good Morning!" if 0 <= hour < 12 else "Good Afternoon!" if 12 <= hour < 18 else "Good Evening!"
    speak(greeting)
    speak("I am DingDongshop. Please tell me how may I help you.")


SAMPLE_RATE = 16000 
SAMPLE_WIDTH = 2     

def takeCommand():
    r = sr.Recognizer()
    try:
        update_conversation("Listening...\n")
        print("Listening...")
       
        recording = sd.rec(int(LISTENING_DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
        sd.wait()  
        audio_bytes = recording.flatten().tobytes()
        audio = sr.AudioData(audio_bytes, SAMPLE_RATE, SAMPLE_WIDTH)

        update_conversation("Processing...\n")
        print("Processing...")
        query = r.recognize_google(audio, language='en-in')
        update_conversation(f"You said: {query}\n")
        print(f"You said: {query}")
        return query.lower()
    except sr.WaitTimeoutError:
        update_conversation("No speech detected.\n")
        print("No speech detected.")
        return "none"
    except sr.UnknownValueError:
        update_conversation("Could not understand audio.\n")
        print("Could not understand audio.")
        return "none"
    except sr.RequestError as e:
        error_msg = f"Request error: {e}"
        update_conversation(f"{error_msg}\n")
        print(error_msg)
        return "none"
    except Exception as e:
        error_msg = f"Recording error: {e}"
        update_conversation(f"{error_msg}\n")
        print(error_msg)
        return "none"

def normalize_query(query):
    prefixes_to_remove = ["what is", "who is", "tell me", "please", "could you", "DingDongShop"]
    for prefix in prefixes_to_remove:
        if query.startswith(prefix):
            query = query.replace(prefix, "").strip()
    return query

# ---------------- MUSIC ----------------
def play_music():
    music_dir = "P:\\music(p)\\Facourite"
    if os.path.exists(music_dir):
        songs = [f for f in os.listdir(music_dir) if f.endswith(('.mp3', '.mp4', '.wav', '.m4a'))]
        if songs:
            song = random.choice(songs)
            os.startfile(os.path.join(music_dir, song))
            speak(f"Playing {song.replace('.mp3', '').replace('.mp4', '')}")
        else:
            speak("No music files found.")
    else:
        speak("Music folder not found.")

# ---------------- SYSTEM ----------------
def system_control(command):
    if command == "shutdown":
        speak("Shutting down the system.")
        os.system("shutdown /s /t 5")
    elif command == "restart":
        speak("Restarting the system.")
        os.system("shutdown /r /t 5")
    elif command == "sleep":
        speak("Putting system to sleep.")
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

# ---------------- OLLAMA CHAT ----------------
def check_ollama_status():
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        if response.status_code != 200:
            return False, "Ollama service not running"
        models = response.json().get('models', [])
        model_names = [model['name'] for model in models]
        if OLLAMA_MODEL not in model_names:
            return False, f"Model {OLLAMA_MODEL} not found. Available models: {', '.join(model_names)}"
        return True, "Ollama ready"
    except requests.exceptions.RequestException:
        return False, "Cannot connect to Ollama"

def generate_ollama_response(prompt):
    try:
        system_prompt = """You are DingDongShop, an intelligent voice assistant. Give concise, helpful responses (1-2 sentences max). 
Be friendly but professional. If you don't know something, say so briefly."""
        full_prompt = f"{system_prompt}\n\nUser: {prompt}\nDingDongShop:"
        response = requests.post(f"{OLLAMA_URL}/api/generate", 
            json={
                'model': OLLAMA_MODEL,
                'prompt': full_prompt,
                'stream': False,
                'options': {
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'max_tokens': 150,
                    'stop': ['\nUser:', '\nHuman:']
                }
            }, 
            timeout=15
        )
        if response.status_code == 200:
            result = response.json()['response'].strip()
            result = result.replace('DingDongShop:', '').strip()
            return result if result else "I'm not sure how to respond to that."
        else:
            return "I'm having trouble generating a response right now."
    except requests.exceptions.Timeout:
        return "I'm thinking too hard about that. Could you ask something else?"
    except Exception as e:
        print(f"Ollama error: {e}")
        return "I encountered an error processing your request."

def generate_fallback_response(query):
    responses_map = {
        'how are you': "I'm functioning well, thank you for asking!",
        'what is your purpose': "I'm here to assist you with tasks and answer questions.",
        'tell me a joke': "Why don't scientists trust atoms? Because they make up everything!",
        'what is the weather': "I don't have access to weather data, but you can check your weather app or ask me to open a weather website.",
        'hello': "Hello! How can I help you today?",
        'good morning': "Good morning! What can I do for you?",
        'good evening': "Good evening! How may I assist you?",
        'thank you': "You're welcome! I'm here whenever you need help.",
        'what is ai': "AI stands for Artificial Intelligence - technology that enables machines to learn and make decisions.",
        'how old are you': "I don't have an age in the traditional sense, but I'm here to serve as your assistant.",
        'who created you': "I was created to be your personal voice assistant.",
        'what can you do': "I can search Wikipedia, open websites, play music, tell time, control system functions, and chat with you."
    }
    query_lower = query.lower()
    for key, response in responses_map.items():
        if key in query_lower:
            return response
    fallbacks = [
        "That's an interesting question. I can help you search for that information if you'd like.",
        "I'm not sure about that specific topic, but I can help with other tasks like opening websites or playing music.",
        "Could you try rephrasing that? I want to make sure I understand what you're looking for.",
        "I don't have information about that right now, but I can search Wikipedia or open a browser for you.",
        "That's beyond my current knowledge, but I'm here to help with system controls, music, or web searches."
    ]
    return random.choice(fallbacks)

# ---------------- CONTINUOUS LISTENING ----------------
class ContinuousListener:
    def __init__(self):
        self.listening = False
        self.thread = None
    
    def start_listening(self):
        if not self.listening:
            self.listening = True
            self.thread = Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            update_status("Listening continuously...", "green")
            toggle_listen_button.config(text="Stop Listening", bg="#d13438")
            speak("I'm now listening continuously. Say 'stop listening' to pause.")
    
    def stop_listening(self):
        if self.listening:
            self.listening = False
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=1)
            update_status("Ready", "green")
            toggle_listen_button.config(text="Start Listening", bg="#0078d4")
            speak("I've stopped listening continuously.")
    
    def toggle_listening(self):
        if self.listening:
            self.stop_listening()
        else:
            self.start_listening()
    
    def _listen_loop(self):
        while self.listening:
            query = takeCommand()
            if query != "none":
                if "stop listening" in query.lower():
                    self.stop_listening()
                    break
                process_command(query)
            time.sleep(LISTENING_COOLDOWN)

# ---------------- GUI FUNCTIONS ----------------
def update_conversation(text):
    conversation_area.config(state='normal')
    conversation_area.insert(tk.END, text)
    conversation_area.see(tk.END)
    conversation_area.config(state='disabled')

def update_status(text, color="green"):
    status_label.config(text=text, foreground=color)
    root.update()

def process_command(query):
    original_query = query
    query = normalize_query(query)
    update_conversation(f"Processing: {query}\n")
    print(f"Processing: {query}")

    if 'wikipedia' in query:
        speak("Searching Wikipedia...")
        search_term = query.replace("wikipedia", "").strip()
        try:
            results = wikipedia.summary(search_term, sentences=2)
            speak("According to Wikipedia")
            speak(results)
        except wikipedia.exceptions.DisambiguationError as e:
            speak(f"Multiple results found. Searching for {e.options[0]}")
            try:
                results = wikipedia.summary(e.options[0], sentences=2)
                speak(results)
            except:
                speak("Sorry, couldn't get Wikipedia results.")
        except:
            speak("Sorry, no Wikipedia results found for that topic.")

    elif any(phrase in query for phrase in ["your name", "what is your name", "who are you"]):
        speak("My name is DingDongShop, your personal voice assistant.")

    elif "about yourself" in query:
        speak("I am DingDongShop, an AI-powered voice assistant designed to help you with various tasks, answer questions, and make your digital life easier.")

    elif any(phrase in query for phrase in ["what can you do", "your capabilities", "help me"]):
        speak("I can search Wikipedia, open websites like YouTube and Google, play music, tell you the time and date, open applications like VS Code, control system functions, and have conversations with you.")

    elif "open youtube" in query:
        speak("Opening YouTube.")
        webbrowser.open("https://www.youtube.com")

    elif "open google" in query:
        speak("Opening Google.")
        webbrowser.open("https://www.google.com")

    elif "open facebook" in query:
        speak("Opening Facebook.")
        webbrowser.open("https://www.facebook.com")

    elif "open instagram" in query:
        speak("Opening Instagram.")
        webbrowser.open("https://www.instagram.com")

    elif "open twitter" in query or "open x" in query:
        speak("Opening Twitter.")
        webbrowser.open("https://www.twitter.com")

    elif "play music" in query:
        play_music()

    elif "time" in query and "what" in original_query:
        strTime = datetime.datetime.now().strftime("%I:%M %p")
        speak(f"The time is {strTime}")

    elif "date" in query and ("what" in original_query or "today" in query):
        strDate = datetime.datetime.now().strftime("%B %d, %Y")
        speak(f"Today's date is {strDate}")

    elif "open code" in query or "open vs code" in query:
        code_paths = [
            "C:\\Users\\ASUS\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
            "C:\\Program Files\\Microsoft VS Code\\Code.exe",
            "C:\\Program Files (x86)\\Microsoft VS Code\\Code.exe"
        ]
        opened = False
        for path in code_paths:
            if os.path.exists(path):
                speak("Opening Visual Studio Code.")
                os.startfile(path)
                opened = True
                break
        if not opened:
            speak("Visual Studio Code not found. Please check the installation path.")

    elif "shutdown" in query and ("system" in query or "computer" in query):
        speak("Are you sure you want to shutdown?")
        confirm = takeCommand()
        if "yes" in confirm or "confirm" in confirm:
            system_control("shutdown")
        else:
            speak("Shutdown cancelled.")

    elif "restart" in query and ("system" in query or "computer" in query):
        speak("Are you sure you want to restart?")
        confirm = takeCommand()
        if "yes" in confirm or "confirm" in confirm:
            system_control("restart")
        else:
            speak("Restart cancelled.")

    elif "sleep" in query and ("system" in query or "computer" in query):
        system_control("sleep")

    elif "my name" in query or "who am i" in query:
        speak("Your name is Arpoon Pramanik, and you are a student of the Neotia University, currently in your third year of B.Tech in Computer Science and Engineering.")

    elif any(word in query for word in ["exit", "quit", "bye", "goodbye", "stop"]):
        speak("Goodbye! Have a great day!")
        if listener:
            listener.stop_listening()
        root.quit()

    else:
        speak("Let me think about that...")
        if ollama_available:
            response = generate_ollama_response(query)
        else:
            response = generate_fallback_response(query)
        speak(response)

def single_listen():
    """Function for single listen button"""
    def listen_thread():
        query = takeCommand()
        if query != "none":
            process_command(query)
    Thread(target=listen_thread).start()

# ---------------- MAIN ----------------
def main():
    global root, conversation_area, status_label, ollama_available, toggle_listen_button, listener
    
    # Create main window
    root = tk.Tk()
    root.title("DingDongShop Voice Assistant")
    root.geometry("800x600")
    root.resizable(True, True)
    root.configure(bg="#1e1e1e")  # Dark background
    
    # Set window icon
    try:
        root.iconbitmap("DingDongShop_icon.ico")  # Replace with your icon file
    except:
        pass
    
    # Custom style
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('TFrame', background="#33c131")
    style.configure('TLabel', background="#d25a5a", foreground='white')
    style.configure('TButton', background='#0078d4', foreground='white')
    style.map('TButton', background=[('active', '#005ea2')])
    
    # Header with logo
    header_frame = ttk.Frame(root)
    header_frame.pack(fill=tk.X, padx=20, pady=10)
    
    try:
        img = Image.open("DingDongShop_logo.png")  # Replace with your logo
        img = img.resize((50, 50), Image.Resampling.LANCZOS)
        logo = ImageTk.PhotoImage(img)
        logo_label = ttk.Label(header_frame, image=logo)
        logo_label.image = logo
        logo_label.pack(side=tk.LEFT)
    except:
        pass
    
    ttk.Label(header_frame, text="DingDongShop AI Assistant", font=("Helvetica", 20, "bold")).pack(side=tk.LEFT, padx=10)
    
    # Conversation area
    conversation_frame = ttk.Frame(root)
    conversation_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
    
    scrollbar = ttk.Scrollbar(conversation_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    conversation_area = tk.Text(
        conversation_frame, 
        wrap=tk.WORD, 
        yscrollcommand=scrollbar.set,
        font=("Segoe UI", 10),
        bg="#2b2b2b",
        fg="#ffffff",
        insertbackground="white",
        padx=10,
        pady=10,
        selectbackground="#0078d4"
    )
    conversation_area.pack(fill=tk.BOTH, expand=True)
    scrollbar.config(command=conversation_area.yview)
    
    # Button frame
    button_frame = ttk.Frame(root)
    button_frame.pack(pady=10)
    
    # Create buttons with icons
    button_data = [
        ("Single Listen", "#0078d4", single_listen),
        ("Play Music", "#0078d4", play_music),
        ("YouTube", "#0078d4", lambda: webbrowser.open("https://www.youtube.com")),
        ("Google", "#0078d4", lambda: webbrowser.open("https://www.google.com")),
        ("Exit", "#d13438", lambda: [listener.stop_listening() if listener else None, root.quit()])
    ]
    
    for text, color, command in button_data:
        btn = tk.Button(
            button_frame,
            text=text,
            font=("Segoe UI", 10),
            bg=color,
            fg="white",
            activebackground="#005ea2" if color == "#0078d4" else "#a1282c",
            activeforeground="white",
            relief=tk.FLAT,
            width=15,
            height=1,
            command=command
        )
        btn.pack(side=tk.LEFT, padx=5, ipady=5)
    
    # Toggle listening button (special style)
    toggle_listen_button = tk.Button(
        button_frame,
        text="Start Continuous Listening",
        font=("Segoe UI", 10, "bold"),
        bg="#0078d4",
        fg="white",
        activebackground="#005ea2",
        activeforeground="white",
        relief=tk.FLAT,
        width=25,
        height=1,
        command=lambda: listener.toggle_listening()
    )
    toggle_listen_button.pack(side=tk.LEFT, padx=5, ipady=5)
    
    # Status frame
    status_frame = ttk.Frame(root)
    status_frame.pack(fill=tk.X, padx=20, pady=10)
    
    status_label = ttk.Label(
        status_frame,
        text="Initializing...",
        font=("Segoe UI", 10),
        anchor=tk.W
    )
    status_label.pack(fill=tk.X)
    
    # Initialize continuous listener
    listener = ContinuousListener()
    
    # Check Ollama status
    ollama_available, status_msg = check_ollama_status()
    update_conversation(f"Ollama Status: {status_msg}\n")
    print(f"Ollama Status: {status_msg}")
    update_status(status_msg, "green" if ollama_available else "red")

    if not ollama_available:
        update_conversation(f"To enable advanced AI chat, install Ollama and run: ollama pull {OLLAMA_MODEL}\n")
        speak("Starting in basic mode. For advanced AI chat, please install Ollama.")
    else:
        speak("Advanced AI mode activated.")

    wishMe()
    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
        speak("Goodbye!")
    except Exception as e:
        print(f"An error occurred: {e}")
        speak("I encountered an error. Please restart me.")
