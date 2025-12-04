import torchaudio
import torch
from pathlib import Path

def resample_audio(audio_path, output_path):
    """Resample audio to 16kHz and save to output_path."""
    print(f"[DEBUG] Resampling audio: {audio_path} to {output_path}")
    # Convert paths to Path objects
    audio_path = Path(audio_path)
    output_path = Path(output_path)
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load audio
    signal, sr = torchaudio.load(str(audio_path))
    print(f"[DEBUG] Loaded audio: signal.shape={signal.shape}, sr={sr}")

    # Convert to mono if needed
    if signal.shape[0] > 1:
        print("[DEBUG] Converting to mono")
        signal = torch.mean(signal, dim=0, keepdim=True)

    # Resample if needed
    if sr != 16000:
        print(f"[DEBUG] Resampling from {sr} to 16000")
        transform = torchaudio.transforms.Resample(orig_freq=sr, new_freq=16000)
        signal = transform(signal)

    torchaudio.save(str(output_path), signal, 16000)
    print(f"[DEBUG] Saved temp file: {output_path}")
    return output_path
