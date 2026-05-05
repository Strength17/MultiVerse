from faster_whisper import WhisperModel

# Added 'download_root' to keep things organized in your project
model = WhisperModel("base.en", device="cpu", compute_type="int8")

# Check if file exists first to avoid FileNotFoundError
import os
audio_path = "Tic Raw Anthem.m4a"

if os.path.exists(audio_path):
    print("Transcribing... please wait.")
    segments, info = model.transcribe(audio_path, beam_size=5)
    
    print(f"Detected language '{info.language}' with probability {info.language_probability}")

    for segment in segments:
        print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
else:
    print(f"Error: Could not find the file '{audio_path}'")
