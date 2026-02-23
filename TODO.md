# Voice Trainer — Feature Backlog

## Pending

### IPA Vowel Display
Analyze live F1 and F2 formant positions to identify the vowel being sung and display it using the International Phonetic Alphabet.

- Map (F1, F2) pairs to IPA vowel symbols using a lookup table based on standard vowel formant charts
- Display the nearest matching vowel symbol live in the UI (next to or below the pitch readout)
- Consider confidence thresholding — only display when F1/F2 estimates are stable
- Reference: Peterson & Barney (1952) vowel formant data, or IPA vowel chart Hz positions

### Color Scheme Exploration
Try alternative color schemes for the spectrogram that maintain contrast between quiet and loud sounds while being more visually appealing than the current teal → orange → yellow.

- Candidates to explore: deep navy → violet → white; dark green → cyan → white; black → electric blue → gold
- Constraint: quiet sounds must still be clearly visible (floor at -60 dB must produce a real, distinct color — not near-black)
- Color must remain legible against the Singer's Formant gold band overlay

---

## Completed

- [x] Real-time scrolling spectrogram (80–8000 Hz)
- [x] Fundamental frequency display (Hz + note name)
- [x] Custom colormap with visible floor (teal → orange → yellow, -60 dB floor)
- [x] Singer's Formant highlight band (2,000–3,500 Hz, gold)
- [x] F1/F2 vowel formant rolling dot overlay (blue/green)

---

## Future Ideas (not yet designed)

- Vibrato rate and extent tracking
- Vowel modification recommendations based on F1/F2 + voice type
- Time-scale zoom (narrow/widen the scrolling window)
- Session recording and playback
- Reference overlays (compare against a recording)
