# speaker-loudness-fix v1.0.0

## What this is

One Python file that makes quiet laptop speakers on Linux audible again. It puts a small, well-known audio tool (a
compressor) between your programs and your sound card: the quiet parts come up, the loud peaks stay where they are.
It asks before changing anything, backs up any file it changes, checks its own work, and `--uninstall` puts
everything back.

## Should you download it?

Yes, if your laptop's speakers are too quiet on Linux even with every volume slider at 100%. It works with PipeWire
(any modern distribution) and with plain PulseAudio (older machines). No, if your sound is loud enough: it changes
how loud things sound, nothing else.

## Why this matters

Most music and videos online are mastered quiet, and on small speakers a volume slider cannot fix that: the loud
peaks already touch the top. A compressor can. On the laptop this was built for, quiet music came out 10.5 dB louder,
measured with a microphone, using 0.2% of one processor core. It is free, and stays free.
