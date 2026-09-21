# %%
import librosa
import glob
import numpy as np

def frequency_to_pitch(freq) -> int:
    midi = 12 * np.log2((freq / 440)) + 69
    return midi
def detect_pitch_class(filepath) -> int | None:
    raw, sr = librosa.load(filepath)
    f0, voiced_flag, voiced_probs = librosa.pyin(raw, 
                                                sr=sr, 
                                                fmin=librosa.note_to_hz('C2'),
                                                fmax=librosa.note_to_hz('C7'))
    mask = voiced_flag & (voiced_probs > 0.8)

    if not mask.any():
        mask = voiced_flag & (voiced_probs > 0.5)
    if not mask.any(): return None

    masked_notes = f0[mask]
    note_frequency = np.nanmedian(masked_notes)
    note_number = frequency_to_pitch(note_frequency)
    pitch_class = (round(note_number)%12)

    return pitch_class
def identify_chord(pitch_classes, chord_type):
    best_confidence = float("-inf")
    best_candidate = None
    for root in pitch_classes:
        for template, name in chord_type.items():
            rel = {(item - root)%12 for item in pitch_classes}
            matched_notes = template.intersection(rel)
            confidence = 2 * len(matched_notes) / (len(rel) + len(template))
            if confidence > best_confidence:
                best_confidence = confidence
                best_candidate = (root, name)
    return (best_candidate, best_confidence)
# def identify_chord(pitch_classes, chord_type):
#     best_score = float("-inf")
#     best_candidate = None
#     for root in pitch_classes:
#         for template, name in chord_type.items():
#             rel = {(item - root)%12 for item in pitch_classes}
#             matched_notes = template.intersection(rel)
#             missing_notes = template - rel
#             extra_notes = rel - template
#             score = len(matched_notes) - len(missing_notes) - len(extra_notes)
#             if score > best_score:
#                 best_score = score
#                 best_candidate = (root, name)
#     return (best_candidate, best_score)




    











