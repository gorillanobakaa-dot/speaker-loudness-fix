# speaker-loudness-fix v1.0.0, for developers

## What it installs

PipeWire: `~/.config/pipewire/filter-chain.conf.d/60-loudness.conf` (a `libpipewire-module-filter-chain` graph hosting
LADSPA SC4 mono from swh-plugins, RMS, attack 3 ms, release 150 ms, threshold -20 dB, ratio 4:1, knee 8 dB, makeup
+12 dB), a user service running `pipewire -c filter-chain.conf`, and `loudness-volume-mirror` (the slider mirrored onto
the hardware sink through a 0.75-power map). PulseAudio: `module-ladspa-sink` plus persistence lines in
`~/.config/pulse/default.pa` (created with `.include /etc/pulse/default.pa` first).

## Changes in this release (commit f5e61b3, PR #1)

- `remember_default()` records the default sink before `set-default-sink loudness_sink` (both paths) in
  `~/.config/speaker-loudness/previous-default-sink`, never the compressor itself; `restore_default()` goes back to it,
  else to the first `alsa_output`; uninstall restores only when the compressor is still the default, and deletes the
  record.
- `sudo(cmd)` adds `-n` when stdin is not a tty; `install_sc4` fails with the exact command when a password is needed.
- `unarmor()` runs only on files `lsattr` reports immutable; `systemctl --user` calls are guarded by `shutil.which`.

## Tests

Tested from Gorilla Fieldkit (`tests/test_speaker_loudness.py`, a fake `pactl`): 12 tests pass on this version and 7 of
them fail on the previous one (they cover the restored output, the reinstall, the fallback, the untouched default, no
sudo or systemctl when not needed, and `sudo -n` without a tty). Source:
https://github.com/gorillanobakaa-dot/Gorilla.Fieldkit/blob/main/tests/test_speaker_loudness.py

## Known limits

End-to-end on Debian 13 / PipeWire 1.4.2 / WirePlumber 1.4.2 only; other distributions run the same code paths but
have not been tried on hardware.
