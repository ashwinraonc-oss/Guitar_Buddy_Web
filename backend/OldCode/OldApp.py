from fastapi import FastAPI, UploadFile, File
import os, tempfile
from backend.OldCode.IdentifyChord import detect_pitch_class, identify_chord
from fastapi.middleware.cors import CORSMiddleware
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
              frozenset([0,5,7]): "sus4"}

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

@app.post("/detect")
async def detect(files: list[UploadFile] = File(...)):
    note_set = set()
    for upload in files:
        contents = await upload.read()
        with tempfile.NamedTemporaryFile(delete = False, suffix = ".wav") as tmp:
            tmp.write(contents)
            temp_path = tmp.name

        try: 
            pitch_class = detect_pitch_class(temp_path)
            if pitch_class is not None:
                note_set.add(pitch_class)

        finally:os.remove(temp_path)

    candidate, score = identify_chord(note_set, chord_type)
    if candidate is not None and score >= 2:
        root = note_dictionary[candidate[0]]
        quality = candidate[1]
        chord = root + " " + quality
    else:
        chord = "Unknown Chord Voicing"
    if candidate is not None:
        res_root = candidate[0]
    return {"chord": chord, "score": score, "notes": sorted(note_set), "root": res_root}


