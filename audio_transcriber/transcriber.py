import os
import sys
import gc
from pathlib import Path

import torch
import torchaudio
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from collections import defaultdict

# Add parent directory to path to import from audio_processing
sys.path.append(str(Path(__file__).parent.parent))

# Lazy import for NeMo diarization to avoid import errors at startup
_diarizer = None
_parse_segments = None
_merge_segments = None

def _lazy_import_nemo():
    """Lazy import NeMo diarization functions to avoid import errors at startup"""
    global _diarizer, _parse_segments, _merge_segments
    if _diarizer is None:
        from audio_processing.nemo_diarize import diarizer, parse_segments, merge_segments
        _diarizer = diarizer
        _parse_segments = parse_segments
        _merge_segments = merge_segments
    return _diarizer, _parse_segments, _merge_segments


class AudioTranscriber:
    def __init__(self, hf_token=None):
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        env_token = os.getenv("HF_TOKEN") 
        token = hf_token or env_token
        self.hf_token = token.strip() if token else None
        if not self.hf_token:
            print("Warning: Hugging Face token not provided. Ensure the model is public or set HF_TOKEN.")
        
        print(f"Initializing on device: {self.device}")
        
        self._load_diarization()
        self._load_asr()
        
    def _load_diarization(self):
        print("Loading NeMo diarization model...")
        # Lazy load the diarization functions (model loads on first import)
        try:
            _lazy_import_nemo()
            print("NeMo diarization model ready")
        except ImportError as e:
            print(f"Warning: Could not load NeMo diarization model: {e}")
            print("Please ensure NumPy version is 2.2 or less (current: check with 'pip show numpy')")
            raise
        
    def _load_asr(self):
        print("Loading Whisper model...")
        auth_kwargs = {"use_auth_token": self.hf_token} if self.hf_token else {}
        self.asr_model = AutoModelForSpeechSeq2Seq.from_pretrained(
            "Oriserve/Whisper-Hindi2Hinglish-Prime",
            torch_dtype=torch.float32,
            **auth_kwargs,
        ).to(self.device)
        
        if hasattr(self.asr_model.generation_config, 'forced_decoder_ids'):
            self.asr_model.generation_config.forced_decoder_ids = None
        if hasattr(self.asr_model.config, 'forced_decoder_ids'):
            self.asr_model.config.forced_decoder_ids = None
            
        self.asr_processor = AutoProcessor.from_pretrained(
            "Oriserve/Whisper-Hindi2Hinglish-Prime", **auth_kwargs
        )
        
    def run_diarization(self, audio_path):
        print("Running NeMo diarization...")
        # Lazy import diarization functions
        diarizer_func, parse_segments_func, merge_segments_func = _lazy_import_nemo()
        
        # Run diarization
        predicted_segments = diarizer_func(str(audio_path))
        
        # Parse segments
        parsed_segments = parse_segments_func(predicted_segments)
        
        # Sort by start time
        sorted_segments = sorted(parsed_segments, key=lambda x: float(x['start']))
        
        # Merge segments with small gaps
        merged_segments = merge_segments_func(sorted_segments, max_gap=3.0)
        
        # Convert to format expected by transcribe_segments
        # Convert string values to float for start/end
        for segment in merged_segments:
            segment['start'] = float(segment['start'])
            segment['end'] = float(segment['end'])
        
        return merged_segments
    
    def _transcribe_segment_from_waveform(self, waveform, sr, start, end):
        """Internal helper that works on a pre-loaded waveform to avoid re-loading audio."""
        segment = waveform[:, int(start * sr): int(end * sr)]
        
        if sr != 16000:
            segment = torchaudio.functional.resample(segment, sr, 16000)
            
        segment = segment.squeeze().numpy()
        if segment.size == 0:
            return ""
            
        inputs = self.asr_processor(
            segment, 
            sampling_rate=16000, 
            return_tensors="pt"
        ).to(self.device)
        
        with torch.no_grad():
            predicted_ids = self.asr_model.generate(
                inputs["input_features"],
                suppress_tokens=None
            )
            
        text = self.asr_processor.batch_decode(
            predicted_ids, 
            skip_special_tokens=True
        )[0]
        return text
    
    def transcribe_segment(self, audio_path, start, end):
        """
        Public API kept for backwards compatibility.
        For efficiency, prefer using `transcribe_segments` which loads the audio only once.
        """
        waveform, sr = torchaudio.load(audio_path)
        try:
            return self._transcribe_segment_from_waveform(waveform, sr, start, end)
        finally:
            # Explicitly release large tensors
            del waveform
            self._clear_inference_memory()
        
    def transcribe_segments(self, audio_path, diarization_segments, progress_callback=None):
        results = []
        total = len(diarization_segments)
        
        # Load the audio once per job to avoid repeated I/O and fragmented memory
        waveform, sr = torchaudio.load(audio_path)
        
        try:
            for i, segment in enumerate(diarization_segments):
                start = segment['start']
                end = segment['end']
                speaker = segment['speaker']
                
                text = self._transcribe_segment_from_waveform(waveform, sr, start, end)
                
                results.append({
                    "speaker": speaker,
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "text": text
                })
                
                if progress_callback:
                    progress_callback((i + 1) / total)
                    
                print(f"[{start:.2f} - {end:.2f}] {speaker}: {text}")
        finally:
            # Release waveform and aggressively clear inference-time memory
            del waveform
            self._clear_inference_memory()
        
        return results
        
    def summarize(self, transcript_data):
        conversation = "\n".join([
            f"[{item['start']:.2f}s - {item['end']:.2f}s] {item['speaker']}: {item['text']}"
            for item in transcript_data if item['text'].strip()
        ])
        
        llm = ChatOllama(
            model="gpt-oss:20b-cloud",
            temperature=0.3
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert call analyst. Analyze the following call transcript and provide:
1. **Call Summary** (2-3 sentences)
2. **Key Points** (bullet points)
3. **Action Items** (if any)
4. **Speakers Overview** (brief description of each speaker's role)
5. **Sentiment** (overall tone of the conversation)

Be concise and professional."""),
            ("human", "Here is the call transcript:\n\n{transcript}")
        ])
        
        chain = prompt | llm | StrOutputParser()
        summary = chain.invoke({"transcript": conversation})
        
        return summary, conversation
        
    def _clear_inference_memory(self):
        """
        Clear temporary tensors and let the runtime reclaim as much memory as possible,
        while keeping the models themselves loaded.
        """
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            try:
                torch.mps.empty_cache()
            except Exception:
                # Some PyTorch versions may not expose empty_cache for MPS
                pass
        
    def get_speaker_stats(self, transcript):
        stats = defaultdict(lambda: {"segments": 0, "duration": 0, "words": 0})
        
        for item in transcript:
            speaker = item["speaker"]
            duration = item["end"] - item["start"]
            words = len(item["text"].split())
            
            stats[speaker]["segments"] += 1
            stats[speaker]["duration"] += duration
            stats[speaker]["words"] += words
            
        result = []
        for speaker, data in stats.items():
            result.append({
                "speaker": speaker,
                "segments": data["segments"],
                "duration": round(data["duration"], 2),
                "words": data["words"]
            })
            
        return result