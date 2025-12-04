# nemo_diarize.py
from nemo.collections.asr.models import SortformerEncLabelModel
import json
import os
from pathlib import Path

diar_model = SortformerEncLabelModel.from_pretrained("nvidia/diar_sortformer_4spk-v1")
diar_model.eval()

def diarizer(audio_input):
    predicted_segments = diar_model.diarize(audio=audio_input, batch_size=1, include_tensor_outputs=False)
    print(f"predicted segments : {predicted_segments[0]}")
    return predicted_segments[0]


def parse_segments(predicted_segments):
    """Parse RTTM segments from model output into a list of dicts."""
    segments = []
    for segment in predicted_segments:
        parts = segment.strip().split()
        start, end, speaker = parts
        segments.append({'start': start, 'end': end, 'speaker': speaker})
    return segments
def merge_segments(segments, max_gap=3.0):
    merged = []
    prev = segments[0]

    for current in segments[1:]:
        same_speaker = current['speaker'] == prev['speaker']
        gap = float(current['start']) - float(prev['end'])
        if same_speaker and gap < max_gap:
            # Extend the previous segment
            prev['end'] = current['end']
        else:
            # Push previous and move to current
            merged.append(prev)
            prev = current
    merged.append(prev)  # Don't forget the last one
    return merged

def save_as_json(segments, file_name):
    with open(file_name, "w") as f:
        json.dump(segments, f, indent=4)

def process_audio_diarize(audio_file):
    print(f"[Debug] diarizing {audio_file} ...")
    filename = Path(audio_file).stem

    diarized_segments = diarizer(str(audio_file))
    if not os.path.exists("output_diarize"):
        os.makedirs("output_diarize")
    output_path_json = f"output_diarize/{filename}_raw_diarized.json"
    with open(output_path_json, "w") as f:
        json.dump(diarized_segments, f, indent=4)

    parsed_segments = parse_segments(diarized_segments)
    if not os.path.exists("output_parsed"):
        os.makedirs("output_parsed")
    output_path_json = f"output_parsed/{filename}_parsed.json"
    save_as_json(parsed_segments, file_name=output_path_json)

    sorted_segments=sorted(parsed_segments, key=lambda x: float(x['start']))
    if not os.path.exists("output_sorted"):
        os.makedirs("output_sorted")
    output_path_json = f"output_sorted/{filename}_sorted.json"
    save_as_json(sorted_segments, file_name=output_path_json)

    merged_segments = merge_segments(sorted_segments, max_gap=3.0)
    if not os.path.exists("output_merged"):
        os.makedirs("output_merged")
    output_path_json = f"output_merged/{filename}_merged_segments.json"
    save_as_json(merged_segments, file_name=output_path_json)

    return merged_segments


