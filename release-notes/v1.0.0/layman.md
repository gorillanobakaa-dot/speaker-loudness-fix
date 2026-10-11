# speaker-loudness-fix v1.0.0, in plain language

## What you get

- Run `python3 speaker_loudness_setup.py`. It tells you what it will do and asks first.
- A new sound output appears, "Speakers + Loudness", and becomes your default.
- Your volume slider still works normally: a small helper copies it to the speakers, so it does not feel dead.
- `--status` looks and changes nothing. `--uninstall` removes everything it added.

## What changed in this release

- **Uninstall puts back the output you had.** If you listened through HDMI, headphones or a USB sound card before
  installing, uninstalling now switches back to that one, instead of the first sound card it found. If that output is
  gone by then, it uses your speakers.
- **It only asks for your password when it really needs it**: to install the compressor package, or to unlock files
  you locked with `--armor`. Run from another program, without a window to type a password in, it stops and prints
  the one command to run yourself, instead of waiting forever.
- **A reinstall no longer forgets your real output**, and uninstalling leaves the default alone when the compressor is
  not the default any more.

## How to check it

- Before: `python3 speaker_loudness_setup.py --status` prints what it sees and changes nothing.
- After installing, play something quiet: it should be clearly louder at the same slider position.
- To undo: `python3 speaker_loudness_setup.py --uninstall`.

## What it cannot do

It does not make the speakers themselves louder than they can go, and it has not been tried on every distribution:
it was tested end to end on Debian 13 with PipeWire 1.4.2.
