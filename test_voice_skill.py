import os
import subprocess

def simulate_llm_token():
    # Symulacja odczytu tokena z .env
    token = os.getenv("LLM_API_KEY_TEST")
    if not token:
        print("[ERROR] Brak testowego tokena LLM. Dodaj LLM_API_KEY_TEST do .env.")
        return False
    print(f"[INFO] Odczytano testowy token LLM: {token}")
    return True

def install_voice_deps():
    print("[INFO] Instaluję zależności: vosk, sounddevice, TTS, espeak-ng...")
    subprocess.run("pip install vosk sounddevice TTS", shell=True, check=True)
    subprocess.run("sudo dnf install -y espeak-ng", shell=True, check=True)

def test_asr():
    from vosk import Model, KaldiRecognizer
    import sounddevice as sd
    import json

    print("[INFO] Testuję rozpoznawanie mowy (ASR)...")
    model = Model(lang="pl")
    rec = KaldiRecognizer(model, 16000)
    duration = 3  # sekundy
    print("Powiedz coś po polsku do mikrofonu (3 sekundy)...")
    audio = sd.rec(int(16000 * duration), samplerate=16000, channels=1, dtype='int16')
    sd.wait()
    if rec.AcceptWaveform(audio):
        result = json.loads(rec.Result())
        print("[INFO] Rozpoznany tekst:", result.get("text"))
        return True
    else:
        print("[WARN] Nie udało się rozpoznać mowy.")
        return False

def test_tts():
    print("[INFO] Testuję syntezę mowy (TTS)...")
    subprocess.run('echo "To jest test głosowy." | espeak-ng -v pl', shell=True)
    print("[INFO] Jeśli usłyszałeś komunikat, TTS działa poprawnie.")

if __name__ == "__main__":
    if not simulate_llm_token():
        exit(1)
    install_voice_deps()
    asr_ok = test_asr()
    test_tts()
    if asr_ok:
        print("[SUCCESS] System gotowy do obsługi voice-chatbota!")
    else:
        print("[WARN] ASR nie działa poprawnie – sprawdź mikrofon lub model.")
