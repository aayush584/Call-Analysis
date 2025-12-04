import torchaudio
from pathlib import Path

audio_path=input(r"enter the path of audio file: ")

filename_stem = Path(audio_path).stem

start_sec =float(input("enter the start time in seconds: "))    
end_sec = float(input("enter the end time in seconds: "))

audio, sr = torchaudio.load(audio_path)
start_sample = int(start_sec * sr)
end_sample = int(end_sec * sr)
segment_audio = audio[:, start_sample:end_sample]
output_path = f"./{filename_stem}_trimmed.wav"
torchaudio.save(output_path, segment_audio, sr)
