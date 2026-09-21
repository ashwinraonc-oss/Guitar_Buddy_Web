"""
Converts tombatossals/chords-db's guitar chord data (lib/guitar.json) into a
lookup table in the same spirit as chord_voicings_complete.py from earlier in
this chat: fret lists in [Low E, A, D, G, B, High E] order (-1 = muted), plus
a chord_voicings dict keyed by frozenset(pitch classes) -> voicings.

Run: python3 build_from_chords_db.py path/to/guitar.json
"""
import json, sys
from collections import defaultdict

NOTE_TO_PC = {  # pitch class 0-11, C=0
    'C':0, 'C#':1, 'Db':1, 'D':2, 'D#':3, 'Eb':3, 'E':4, 'F':5, 'F#':6, 'Gb':6,
    'G':7, 'G#':8, 'Ab':8, 'A':9, 'A#':10, 'Bb':10, 'B':11,
}
STRING_OPEN_MIDI = [40, 45, 50, 55, 59, 64]  # standard tuning E2 A2 D3 G3 B3 E4

def convert_frets(frets, base_fret):
    """chords-db stores frets relative to base_fret, with 0 ALWAYS meaning
    'play this string open' regardless of base_fret (verified against the
    dataset's own midi field for all 3283 positions -- 0 mismatches)."""
    out = []
    for v in frets:
        if v == -1:
            out.append(-1)
        elif v == 0:
            out.append(0)
        else:
            out.append(base_fret - 1 + v)
    return out

def sanitize(s):
    """Turn a chords-db suffix or key into a valid Python identifier fragment."""
    s = s.replace('#', 'sharp')
    s = s.replace('/', '_over_')
    s = s.replace('.', '_')
    return s

def build(json_path):
    data = json.load(open(json_path))
    guitar_chords = {}          # (root_name, suffix) -> [voicing, ...]
    chord_voicings = defaultdict(list)
    contributors = defaultdict(list)

    for root_name, entries in data['chords'].items():
        for entry in entries:
            suffix = entry['suffix']
            voicings = []
            for pos in entry['positions']:
                abs_frets = convert_frets(pos['frets'], pos['baseFret'])
                voicings.append(abs_frets)

                pcs = set()
                played = []
                for i, f in enumerate(abs_frets):
                    if f != -1:
                        pcs.add((STRING_OPEN_MIDI[i] + f) % 12)
                        played.append((STRING_OPEN_MIDI[i] + f))
                bass_note = min(played) % 12
                tones = frozenset(pcs)

                chord_voicings[tones].append((bass_note, abs_frets))
                contributors[tones].append((root_name, suffix))

            guitar_chords[(root_name, suffix)] = voicings

    return guitar_chords, dict(chord_voicings), dict(contributors)


if __name__ == '__main__':
    json_path = sys.argv[1] if len(sys.argv) > 1 else 'guitar.json'
    guitar_chords, chord_voicings, contributors = build(json_path)
    print('(root,suffix) pairs:', len(guitar_chords))
    print('total voicings:', sum(len(v) for v in guitar_chords.values()))
    print('distinct frozenset keys:', len(chord_voicings))
    collisions = {k:v for k,v in contributors.items() if len(v) > 1}
    print('collision groups:', len(collisions))