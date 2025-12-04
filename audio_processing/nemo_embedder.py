from pathlib import Path
import json
import torchaudio
import nemo.collections.asr as nemo_asr
from audio_processing.utils_resample import resample_audio
import torch.nn.functional as F
# Load model
speaker_model = nemo_asr.models.EncDecSpeakerLabelModel.from_pretrained("nvidia/speakerverification_en_titanet_large")
speaker_model.eval()

def get_embedding(audio_file):
    temp_path = audio_file
    """Load audio, resample to 16kHz if needed, return L2-normalized embedding tensor."""
    print(f"[DEBUG] get_embedding called with audio_file: {audio_file}")
   
    # Get embedding from the model
    print(f"[DEBUG] speaker_model type: {type(speaker_model)}")
    embedding = speaker_model.get_embedding(temp_path)
    print(f"[DEBUG] Got embedding: {embedding.shape}")

    # Normalize (L2)
    embedding = F.normalize(embedding, p=2, dim=1)
    print(f"[DEBUG] Normalized embedding: {embedding.shape}")
    return embedding.squeeze().cpu()

def compare_speakers(agent_folder, full_audio_path, diarization_data, threshold=0.75):
    """Compare diarized segments with agents using cosine similarity on embeddings."""
    agent_folder = Path(agent_folder)
    if not agent_folder.exists():
        raise FileNotFoundError(f"Agent folder not found: {agent_folder}")


    print(f"[DEBUG] compare_speakers called with agent_folder: {agent_folder}, full_audio_path: {full_audio_path}, threshold: {threshold}")
    # Preload embeddings for agents
    agents = {}
    for file in Path(agent_folder).glob("*.wav"):
        print(f"[DEBUG] Loading agent embedding for: {file}")

        agent_name = file.stem
        # Save to a temporary file since NeMo expects a path
        output_path = f"{agent_folder}/temp/{agent_name}.wav"
        file = resample_audio(file, output_path)
        print(f"[DEBUG] Resampled agent audio to: {output_path}")
        # Get embedding for the agent
        print(f"[DEBUG] Getting embedding for agent: {agent_name}")
        agents[agent_name] = get_embedding(str(file))
        print(f"[DEBUG] Loaded agent embedding for {agent_name}: shape={agents[agent_name].shape}")


    # Load full audio once
    print(f"[DEBUG] Loading full audio: {full_audio_path}")
    full_waveform, sr = torchaudio.load(str(full_audio_path))
    print(f"[DEBUG] full_waveform.shape={full_waveform.shape}, sr={sr}")
    filename_stem = Path(full_audio_path).stem

    # Ensure temp directory exists
    seg_dir = Path(f"temp/{filename_stem}")
    seg_dir.mkdir(parents=True, exist_ok=True)


    for i, segment in enumerate(diarization_data, start=1):
        print(f"[DEBUG] Processing diarization segment {i}: {segment}")
        start = int(float(segment["start"]) * sr)
        end = int(float(segment["end"]) * sr)
        segment_waveform = full_waveform[:, start:end]

        # Save temp segment
        seg_filename = f"{filename_stem}_segment{i}.wav"
        seg_path = seg_dir / seg_filename
        torchaudio.save(str(seg_path), segment_waveform, sr)
        print(f"[DEBUG] Saved segment to {seg_path}")

        # Add segment audio filename to the segment dict
        segment["segment_audio"] = str(seg_path)

        # Get embedding for the segment
        seg_embedding = get_embedding(str(seg_path))
        print(f"[DEBUG] Segment embedding shape: {seg_embedding.shape}")

        # Compare with each agent using cosine similarity
        best_match, best_score = None, -1.0
        for agent_name, agent_emb in agents.items():
            score = F.cosine_similarity(seg_embedding.unsqueeze(0), agent_emb.unsqueeze(0)).item()
            print(f"[DEBUG] Comparing with agent {agent_name}: score={score}")
            if score > best_score:
                best_score, best_match = score, agent_name

        # Assign speaker if above threshold
        print(f"[DEBUG] Best match: {best_match}, score: {best_score}")
        if best_score >= threshold:
            segment["speaker"] = best_match
            segment["match_score"] = best_score  # Keep score for reference

    # Save updated diarization data
    Path("output_embed").mkdir(exist_ok=True)
    output_json = f"output_embed/{filename_stem}_final.json"
    with open(output_json, "w") as f:
        json.dump(diarization_data, f, indent=2)

    print(f"[DEBUG] Updated diarization JSON saved to {output_json}")




