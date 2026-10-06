"""Rebuild a library arrangement from a supplied symbolic MIDI source."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from server.midi_arrangement import convert_midi

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('midi', type=Path)
parser.add_argument('--title', required=True)
parser.add_argument('--artist', required=True)
parser.add_argument('--melody-track', type=int, required=True)
parser.add_argument('--harmony-tracks', type=int, nargs='+', required=True)
parser.add_argument('--arranger', default='')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
song = convert_midi(args.midi, title=args.title, artist=args.artist,
                    melody_track=args.melody_track, harmony_tracks=args.harmony_tracks, arranger=args.arranger)
args.output.write_text(json.dumps(song, ensure_ascii=False, indent=2) + '\n')
print(f'Imported {len(song["right_hand"])} melody events and {len(song["harmony"])} chord changes.')
