import json
from pathlib import Path
import re
import os
# def parse_word_timestamps(word_transcription):
#     """
#     Parse the word-level timestamp file (as produced by your ASR) into a list of dicts:
#     [{"start": float, "word": str}, ...]
#     """
#     # Read the file as a single string
#     content = word_transcription
#     # Find all matches of the pattern: start - end : word
#     pattern = r'([\d.]+)s - ([\d.]+)s : ([^\"]+?)"'
#     matches = re.findall(pattern, content)
#     # If the above doesn't work, try splitting by '"' and parsing each
#     if not matches:
#         items = content.split('"')
#         matches = []
#         for item in items:
#             m = re.match(r'([\d.]+)s - ([\d.]+)s : (.+)', item.strip())
#             if m:
#                 matches.append((m.group(1), m.group(2), m.group(3)))
#     # Convert to list of dicts
#     word_timestamps = [
#         {"start": float(start), "end": float(end), "word": word.strip()} for start, end, word in matches
#     ]
#     return word_timestamps

def parse_word_timestamps(word_transcription):
    """
    Ensure we always return a list of dicts:
    [{"start": float, "end": float, "word": str}, ...]
    """

    # Case 1: Already in correct format
    if isinstance(word_transcription, list) and all(isinstance(x, dict) for x in word_transcription):
        return word_transcription

    # Case 2: It's a string (raw content from file)
    if isinstance(word_transcription, str):
        pattern = r'([\d.]+)s - ([\d.]+)s : (.+)'
        matches = re.findall(pattern, word_transcription)

        word_timestamps = [
            {"start": float(start), "end": float(end), "word": word.strip()}
            for start, end, word in matches
        ]
        return word_timestamps

    raise TypeError(f"Unsupported word_transcription type: {type(word_transcription)}")


def combine_transcript_with_diarization(diarized_segments, word_transcription, output_path):
    """
    For each diarization segment, add a 'text' field containing all words whose start time is within the segment.
    """
    word_timestamps = parse_word_timestamps(word_transcription)
    for segment in diarized_segments:
        seg_start = float(segment['start'])
        seg_end = float(segment['end'])
        words = [
            w['word']
            for w in word_timestamps
            if (seg_start <= w['start'] <= seg_end) or (seg_start <= w['end'] <= seg_end)
        ]
        segment['text'] = ' '.join(words)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(diarized_segments, f, indent=2, ensure_ascii=False)
    print(f"Combined diarization and transcription saved to {output_path}")

    return diarized_segments
