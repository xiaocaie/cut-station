# Source and timeline data contract

This public specification is independent of private company documents. It describes internal bookkeeping, not an undocumented interchange API for a renderer.

## Inspect before adapting

Check current project/protected edits, engine/runtime versions and actual media streams. `scripts/preflight_video.py --help` documents the read-only checker. Its readiness result permits a real small test; it does not prove a composition rendered. No credentials are read.

Run speech recognition only when real speech needs transcription. Reuse approved cues; silent recordings need no ASR. Explain data upload/cost dependencies before using external services under actual authorization.

## Records

Asset index: `asset_id`, project-local path, source/rights, hash, duration/dimensions/fps/audio, factual identity and sensitive regions. Label real, illustrative or pending. Private sources stay in the project and never become bundled examples.

Shot record: `shot_id`, `asset_id`, `source_in/out`, `output_in/out`, `playback_rate`, semantic object/action/result, cue IDs, crop/focus, selected implementation, settled reading interval and evidence. Narration/music/SFX have independent source ranges, placement and gain.

Before calling Video Use, Remotion or HyperFrames, inspect its actual installed CLI/schema and write the necessary adapter. Invented crop/speed/overlay/mixing fields do not become effective merely because an internal JSON includes them.

## Two clocks

Use seconds and half-open intervals `[start,end)`. For constant speed r, `output_time = output_in + (source_time-source_in)/r`. Recordings default to r=1; the guard rejects slow playback and intervals implying a slower source. Loops/frozen frames and semantic truthfulness still require actual viewing.

Measured speech timing requires real final audio, `timing_source=measured`, `audio_source` and non-overlapping cues inside that audio. Without narration use a visual clock or explicitly provisional captions; never invent an audio path for the schema.

Changing cuts/transitions updates captions, overlays and SFX together. Deleting speech also updates related images/events and later timings. Pure font/color edits preserve approved audio/timing.

## Real sample

Check fonts, streams, caption language, one motion event and output container using a representative project segment. Validate actual decoding, clock mapping and playback. Silent sources require audio-optional mapping; do not assume a helper with mandatory audio accepts them.

Check privacy/rights on ingest and delivery. Technical checks do not establish ownership, editorial truthfulness or comprehension.
