from fastapi import FastAPI, UploadFile, File
import os, tempfile
from detection.detect_chord import detect_midi, identify_chord, get_onset_times, get_voicings
from fastapi.middleware.cors import CORSMiddleware
from detection.data.dataBuilding.DBLookUp import chord_voicings
origins = [
    "http://localhost:5173",
    "http://localhost:5174"
]


note_dictionary = {0: "C", 1: "C#", 2: "D", 3: "D#", 
                   4: "E", 5: "F", 6: "F#", 7: "G", 
                   8: "G#", 9: "A", 10: "A#", 11: "B"}
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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}
@app.get("/lookup")
async def lookup_voicing(root: int, quality: str):
    return {"voicings": get_voicings(root, quality)}
@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    note_set = set()
    contents = await file.read()
    midi_notes = []
    with tempfile.NamedTemporaryFile(delete = False, suffix = ".wav") as tmp:
        tmp.write(contents)
        temp_path = tmp.name
    try:
        note_array, sr = get_onset_times(temp_path)
        for note in note_array:
            midi = detect_midi(note, sr)
            if midi is not None:
                midi_notes.append(midi)
        note_set = {n % 12 for n in midi_notes}
        if midi_notes:
            detected_bass = min(midi_notes) % 12
        else:
            detected_bass = None

    finally:os.remove(temp_path)
    
    candidate, confidence = identify_chord(note_set, chord_type)
    if candidate is not None and confidence >= 0.65:
        root = note_dictionary[candidate[0]]
        root_num = candidate[0]
        quality = candidate[1]
        root_midi = min(m for m in midi_notes if m % 12 == root_num)
        chord_midi = [root_midi + iv for iv in quality_intervals[quality]]
        chord_notes = frozenset((root_num + iv) % 12 for iv in quality_intervals[quality])
        chord = root + quality
        voicing_lookup = get_voicings(root_num, quality, detected_bass)
    else:
        chord = "Unknown Chord Voicing"
        voicing_lookup = []
        chord_notes = []
        chord_midi = []
    if candidate is not None:
        res_root, quality = candidate
    res_root = candidate[0] if candidate is not None else None
    confidence = (confidence * 100) if candidate is not None else 0
    return {"chord": chord, 
            "score": round(confidence),
            "chord_notes": sorted(chord_notes),
            "chord_notes_names": [note_dictionary[n] for n in sorted(chord_notes)],
            "chord_notes_names_midi": sorted(chord_midi, key=lambda m: m % 12),
            "notes": sorted(note_set),
            "note_names": [note_dictionary[n] for n in sorted(note_set)],
            "midi_notes": [min(m for m in midi_notes if m % 12 == n) for n in sorted(note_set)],
            "root": res_root, 
            "voicing": voicing_lookup}


