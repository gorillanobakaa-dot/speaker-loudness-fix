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
---
# In plain language: everything in this release

This is the complete explanation, not a summary of one. Nothing below is behind a link.

<!-- plain-language track: in full, on this page -->

### What you get

- Run `python3 speaker_loudness_setup.py`. It tells you what it will do and asks first.
- A new sound output appears, "Speakers + Loudness", and becomes your default.
- Your volume slider still works normally: a small helper copies it to the speakers, so it does not feel dead.
- `--status` looks and changes nothing. `--uninstall` removes everything it added.

### What changed in this release

- **Uninstall puts back the output you had.** If you listened through HDMI, headphones or a USB sound card before
  installing, uninstalling now switches back to that one, instead of the first sound card it found. If that output is
  gone by then, it uses your speakers.
- **It only asks for your password when it really needs it**: to install the compressor package, or to unlock files
  you locked with `--armor`. Run from another program, without a window to type a password in, it stops and prints
  the one command to run yourself, instead of waiting forever.
- **A reinstall no longer forgets your real output**, and uninstalling leaves the default alone when the compressor is
  not the default any more.

### How to check it

- Before: `python3 speaker_loudness_setup.py --status` prints what it sees and changes nothing.
- After installing, play something quiet: it should be clearly louder at the same slider position.
- To undo: `python3 speaker_loudness_setup.py --uninstall`.

### What it cannot do

It does not make the speakers themselves louder than they can go, and it has not been tried on every distribution:
it was tested end to end on Debian 13 with PipeWire 1.4.2.

---

# For developers: how it works, and how to check it

Written for someone who will audit, fork or change the code. It covers the same release as the plain-language part above; neither is a summary of the other.

<!-- developer track: in full, on this page -->

### What it installs

PipeWire: `~/.config/pipewire/filter-chain.conf.d/60-loudness.conf` (a `libpipewire-module-filter-chain` graph hosting
LADSPA SC4 mono from swh-plugins, RMS, attack 3 ms, release 150 ms, threshold -20 dB, ratio 4:1, knee 8 dB, makeup
+12 dB), a user service running `pipewire -c filter-chain.conf`, and `loudness-volume-mirror` (the slider mirrored onto
the hardware sink through a 0.75-power map). PulseAudio: `module-ladspa-sink` plus persistence lines in
`~/.config/pulse/default.pa` (created with `.include /etc/pulse/default.pa` first).

### Changes in this release (commit f5e61b3, PR #1)

- `remember_default()` records the default sink before `set-default-sink loudness_sink` (both paths) in
  `~/.config/speaker-loudness/previous-default-sink`, never the compressor itself; `restore_default()` goes back to it,
  else to the first `alsa_output`; uninstall restores only when the compressor is still the default, and deletes the
  record.
- `sudo(cmd)` adds `-n` when stdin is not a tty; `install_sc4` fails with the exact command when a password is needed.
- `unarmor()` runs only on files `lsattr` reports immutable; `systemctl --user` calls are guarded by `shutil.which`.

### Tests

Tested from Gorilla Fieldkit (`tests/test_speaker_loudness.py`, a fake `pactl`): 12 tests pass on this version and 7 of
them fail on the previous one (they cover the restored output, the reinstall, the fallback, the untouched default, no
sudo or systemctl when not needed, and `sudo -n` without a tty). Source:
https://github.com/gorillanobakaa-dot/Gorilla.Fieldkit/blob/main/tests/test_speaker_loudness.py

### Known limits

End-to-end on Debian 13 / PipeWire 1.4.2 / WirePlumber 1.4.2 only; other distributions run the same code paths but
have not been tried on hardware.
