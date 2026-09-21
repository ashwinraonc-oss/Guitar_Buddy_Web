# %%
import librosa
import glob
import numpy as np
import os
from detection.data.dataBuilding.DBLookUp import chord_voicings

# %%

file_path = "./Unused Audio/E Major Chord.wav"

#pitch class to note matching dictionary
note_dictionary = {0: "C", 1: "C#", 2: "D", 3: "D#", 
                   4: "E", 5: "F", 6: "F#", 7: "G", 
                   8: "G#", 9: "A", 10: "A#", 11: "B"}
#Set of pitch classes to chord quality matching dictionary
chord_type = {frozenset([0,4,7]): "Major",
                frozenset([0,3,7]): "Minor",
                frozenset([0,3,6]): "Dim",
                frozenset([0,4,8]): "Aug",
                frozenset([0,4,7,10]): "7",
                frozenset([0,4,7,11]): "Maj7",
                frozenset([0,3,7,10]): "m7",
                frozenset([0,3,6,10]): "m7♭5",
                frozenset([0,3,6,9]): "Dim7",
                frozenset([0,2,7]): "sus2",
                frozenset([0,5,7]): "sus4",
                frozenset([0,4,7,9]): "6",
                frozenset([0,3,7,9]): "m6",
                frozenset([0,2,4,7]): "add9",
                frozenset([0,2,3,7]): "m(add9)",
                frozenset([0,2,4,7,10]): "9",
                frozenset([0,2,4,7,11]): "Maj9",
                frozenset([0,2,3,7,10]): "m9",
                frozenset([0,4,8,10]): "7#5",
                frozenset([0,1,4,7,10]): "7b9",
                frozenset([0,3,4,7,10]): "7#9",
                frozenset([0,5,7,10]): "7sus4",
                frozenset([0,2,7,10]): "7sus2",
                frozenset([0,7]): "5",         # power chord
                frozenset([0,4,5,7]): "add11",
                frozenset([0,4,6,10]): "7b5",
                frozenset([0,4,6,11]): "Maj7b5",
                frozenset([0,4,8,11]): "Maj7#5",
                frozenset([0,2,7,11]): "Maj7sus2",
                frozenset([0,2,5,7]): "sus2sus4",  # 2 and 4, no 3rd
                frozenset([0,2,4,7,9]): "6/9",
                frozenset([0,2,4,6,10]): "9b5",
                frozenset([0,2,4,8,10]): "9#5",
                frozenset([0,2,4,6,7,10]): "9#11",
                frozenset([0,2,4,5,7,10]): "11",
                frozenset([0,3,7,11]): "mMaj7",
                frozenset([0,3,6,11]): "mMaj7♭5",
                frozenset([0,2,3,7,9]): "m6/9",
                frozenset([0,2,3,5,7,10]): "m11",
                frozenset([0,2,3,5,7,11]): "mMaj11",
            }
quality_intervals = {name: sorted(intervals) for intervals, name in chord_type.items()}

#takes audio from user, trims the start and end of the file, 
#then finds the points at which the audio file peaks.
#Returns an array of a list of amplitudes of the onsets.
def get_onset_times(file_path):
    sample_array = [] #holds index of each onset start
    note_array = [] #holds the actual audio chunks of the recording
    y, sr = librosa.load(file_path)
    y, _ = librosa.effects.trim(y)
    start_trim = int(0.3*sr)
    end_trim = int(0.3*sr)
    y = y[start_trim:-end_trim]
    onset_times = librosa.onset.onset_detect(y=y, sr=sr, units = 'time', delta = 0.12)
    for time in onset_times:
        sample_idx = int(time * sr)
        sample_array.append(sample_idx)
    for i in range(len(sample_array)-1):
        note_array.append(y[sample_array[i]:sample_array[i+1]])
    note_array.append(y[sample_array[-1]:])

    return (note_array, sr)

#converts frequency of the detected note to a MIDI note using standard MIDI formula
def frequency_to_pitch(freq) -> int:
    midi = 12 * np.log2((freq / 440)) + 69
    return midi

#Takes one audio chunk from the return value of get_onset_times 
#and determines what musical letter note it is if a pitch can be surmised.
def detect_midi(raw, sr) -> int | None:
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
    note_number = round(frequency_to_pitch(note_frequency))
    return note_number

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

#Function to filter voicings by their minimum fret. In other words if 2 voicings both start at the 5th fret, for example, remove one of them.
def filter_voicings(voicings):
    seen = set()
    sorted_voicings = sorted(voicings, key = lambda v: v.count(0), reverse=True)
    filtered_voicings = []
    for voicing in sorted_voicings:
        fretted = [f for f in voicing if f > 0]
        min_fret = min(fretted) if fretted else 0
        if min_fret not in seen:
            seen.add(min_fret)
            filtered_voicings.append(voicing)
    return filtered_voicings

#Sorts the voicings by the number of open strings in the voicing in ascending order.
#Also deduplicates the voicings list in case multiple exact voicings are returned.
def sort_voicings(voicings, detected_bass = None):
    deduped = list({tuple(frets): (bass, frets) for bass, frets in voicings}.values())
    sorted_voicings = sorted(deduped, key=lambda bf: (bf[0] != detected_bass, -bf[1].count(0)))
    return sorted_voicings

#Frontend inputs the root of a chord as its integer value and the type of chord (quality)
#Then returns the list of guitar voicings associated with the input chord
def get_voicings(root_num, quality, detected_bass = None):
    voicing_lookup = []
    intervals = quality_intervals.get(quality)
    if intervals is not None:
        voicing_key = frozenset((root_num + iv) % 12 for iv in intervals)
        voicing_lookup = chord_voicings.get(voicing_key) or []
        if voicing_lookup:
            voicing_lookup = [(b, v) for b, v in voicing_lookup if all(fret <= 16 for fret in v if fret != -1)]
            voicing_lookup = sort_voicings(voicing_lookup, detected_bass)
    return [frets for _, frets in voicing_lookup]
    
            

