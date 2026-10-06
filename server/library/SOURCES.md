# Library sources

These are simplified arrangements of existing MIDI scores, not transcriptions of
the user's video. The vocal track supplies the melody. Accompaniment tracks supply
pitch durations for a simple triad per four-beat practice bar. Short ornaments are
removed, simultaneous vocal notes select the higher voice, pitches are folded into
C3–C6, and rhythm is quantized to half beats. Opening instrumental passages before
the vocal part are omitted. A fixed 4/4 practice meter and initial source tempo are
used; this intentionally simplifies later meter/tempo changes.

Source archive: [dirkncl/midiArchive](https://github.com/dirkncl/midiArchive),
commit `8f4b676e5a584ac60f3d9d02ea2a69976e1aea05`.
Its README describes the Melody Kit collection of public MIDI files gathered in
2015. Public availability is not a claim that every arrangement is public domain.
Original MIDI files are not bundled in this repository; the derived arrangements
retain source links, hashes, track selections and attribution.

## Nightwish — Sleeping Sun

- [Original MIDI](https://github.com/dirkncl/midiArchive/blob/8f4b676e5a584ac60f3d9d02ea2a69976e1aea05/N/N/Nightwish%20-%20Sleeping%20Sun.mid)
- SHA-256: `df317a8c8691af64eebb0e43fd329768be0c961e79fb9f9c09bb0db01e833724`
- Source attribution: “By Nightwish (sequenced by Fio)”; “Copyright © 2001 by Fio”; “All Rights Reserved”.
- Melody: track 3, `Soprano`; accompaniment: tracks 1, 2, 5, 6, 7.
- Starts at source beat 44. Initial tempo: 110 BPM. No key signature is encoded;
  D minor is inferred from written note distributions, not the linked recording.
- Output: 269 monophonic melody events.

## Nightwish — Come Cover Me

- [Original MIDI](https://github.com/dirkncl/midiArchive/blob/8f4b676e5a584ac60f3d9d02ea2a69976e1aea05/N/N/Nightwish%20-%20Come%20Cover%20Me.mid)
- SHA-256: `2862d5bf0a0dd2d985e2e8d865d8464efe39e720d854579968df8cacf299c4b2`
- No sequencer attribution was identified in the MIDI metadata.
- Melody: track 2, `VOIE ET BACKING VOCAL`; accompaniment: tracks 3, 4, 6.
- Starts at source beat 32. Initial tempo: 150 BPM. No key signature is encoded;
  D minor is inferred from written note distributions.
- Output: 250 monophonic melody events.

## Reproduce or add a song

Install the repository requirements, obtain the linked MIDI and verify its hash.
For Sleeping Sun, run from the repository root:

```bash
.venv/bin/python scripts/import-library-midi.py /path/to/sleeping-sun.mid \
  --title 'Sleeping Sun' --artist Nightwish --melody-track 3 \
  --harmony-tracks 1 2 5 6 7 --arranger Fio \
  --output server/library/nightwish-sleeping-sun.json
```

The importer does not identify the lead voice automatically. Inspect MIDI track
names and note content, choose the vocal/lead track, then verify the result in the
player. Register the file and source attribution in `manifest.json`. Chords are a
simple adaptation of the written accompaniment; they are not guaranteed to match
the original recording or a different cover. MusicXML import and automatic online
arrangement discovery are future additions; current external searches open source
pages and do not import arbitrary search results.
