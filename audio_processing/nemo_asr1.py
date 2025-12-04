import json
import nemo.collections.asr as nemo_asr
import os
from pathlib import Path
# asr_model = nemo_asr.models.ASRModel.from_pretrained("stt_en_fastconformer_transducer_large")
# asr_model = nemo_asr.models.ASRModel.from_pretrained("nvidia/parakeet-tdt_ctc-110m")
asr_model = nemo_asr.models.ASRModel.from_pretrained("nvidia/parakeet-tdt-0.6b-v2")

def audio_transcribe(audio_path):
    filename_stem = Path(audio_path).stem
    hypotheses = asr_model.transcribe(str(audio_path), timestamps=True)

    # word-level timestamps
    word_timestamps = hypotheses[0].timestamp['word']

    # convert to proper JSON structure
    words_json = [
        {
            "start": round(float(stamp["start"]), 3),
            "end": round(float(stamp["end"]), 3),
            "word": stamp["word"].strip()
        }
        for stamp in word_timestamps
    ]

    # ensure output folder exists
    os.makedirs("output_nemo_asr", exist_ok=True)

    # save the list once (not inside loop!)
    with open(f"output_nemo_asr/{filename_stem}_word.json", "w", encoding="utf-8") as f:
        json.dump(words_json, f, indent=2, ensure_ascii=False)

    print(words_json)
    return word_timestamps


