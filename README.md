# speaker-loudness-fix

**Your laptop speakers whisper even with every volume slider at 100%? This
fixes it. One file, one command, free, undoable.**

```bash
python3 speaker_loudness_setup.py
```

Works on Linux with PipeWire (any modern distro) or plain PulseAudio (older
machines). Standard-library Python only — nothing to pip-install. It asks
before touching anything, backs up any file it changes, verifies its own work,
and `--uninstall` puts everything back.

---

## Track 1 — for everyone (the layman track)

### The problem you probably have

Cheap and old laptops have quiet speakers. On top of that, most music and
videos on YouTube are mastered *quiet* (16–20 dB below maximum), and YouTube's
own volume normalization only ever turns loud videos *down* — it never helps
quiet ones. So you push every slider to 100%, then 117%, and you still lean
into the screen to hear.

Here is the trap nobody tells you about: **your volume sliders cannot fix
this, no matter what.** Sound is quiet valleys with sharp peaks, and on quiet
recordings the peaks are *already* touching the digital ceiling. A volume
slider raises valleys and peaks together — and the peaks have nowhere to go.
You are pressing the accelerator in a car that is already at top speed.

### What this script does

It installs a small, well-known audio tool (a *compressor*) between your apps
and your sound card. A compressor gently squashes the peaks down and lifts
the quiet parts up — same ceiling, much more sound underneath it. Radio
stations have done exactly this for seventy years.

Measured result on the 2012 laptop this was built for: **quiet music got
10 dB louder** (that is roughly *twice* as loud to your ears, twice over)
while peaks stayed safely capped, using **0.2% of one CPU core**. A
comfortable volume that used to be unreachable at "everything maxed" now
sits at 44% of the slider.

### Is it safe?

- It never overwrites your files without a timestamped backup.
- It checks its own result and undoes itself if the check fails.
- `--uninstall` removes everything it added.
- `--status` just looks and tells you what it sees, changing nothing.
- Headphone users: compression is a taste thing on headphones. Your system
  volume menu lets you switch output back to plain "Built-in Audio" any time.

---

## The story (and the lesson) — why this exists

This fix comes out of the Gorilla Unleashed project: one IT guy and a long
line of AI assistant sessions, spending months making a 2012 Sony VAIO into
a machine worth using.

Here is the embarrassing part, told on purpose. The speakers whispered for
over a year. In that year: a custom kernel patch was written to boost the
codec (it turned out to do *nothing* — it edited a capability table, not a
single decibel). A browser DSP was built from scratch — crossovers,
psychoacoustic EQ, harmonic bass synthesis, a compander curve with real
mathematics behind it. The math was checked by another AI and the math was
*correct*. It still didn't fix the whisper, because all of it was aimed at
the wrong premise. Somewhere early on, "+5.5 dB" got written into a table
with the note *"never measured"* — and then a year of work inherited that
unmeasured number as settled truth.

The whole thing was finally solved in one evening — not with better math,
but with a **microphone**. Here is how the evening actually went, from the
session log, wrong turns included, because the wrong turns *are* the lesson:

1. Opening complaint, verbatim: *"that's how hard i have to push the volume
   slider just to get a whisper sound"* — every control at 104–117%.
2. First suspect: the celebrated kernel patch. Reading the codec registers
   showed it edits a capability *table* on an amp that has no volume stages
   at all, plus a second node that isn't even an amplifier. A year of faith,
   zero decibels. (Its own documentation contained the confession, verbatim:
   *"+5.5 dB — never measured."*)
3. The amplifier-asleep theory, tested with the mic: toggle the amp-enable
   bit off — tone drops 47 dB to the noise floor; toggle it back — tone
   returns. The amp was awake all along. Fifteen months of "the amp needs
   unlocking" died in four seconds of measurement.
4. The AI then produced a beautiful theory: a browser patch was bypassing
   the Web Audio compressor that YouTube's Stable Volume feature needs for
   its make-up gain. Confident, elegant, fully documented. The owner's
   entire reply: *"yeah.... no such hallucinated menu."* The feature wasn't
   even available on his player. Theory dead on contact with one screenshot.
5. Next came hours of digital "evidence": the browser apparently emitting
   audio 24 dB low, impossible volume responses, a frequency sweep that
   recorded as nothing but clicks — a whole phase-cancellation
   investigation. Then the control experiment: tap a *known* tone the same
   way. It read just as broken. **The measuring instrument itself was
   lying** — on a loaded old CPU, stream capture drops chunks and fabricates
   exactly the kind of deficit that sends you chasing ghosts. Everything
   measured through it was thrown away in one stroke.
6. What never lied: the internal microphone plus a simultaneous reference
   tone (the dual-band pilot method — see the developer track). Calibrated
   properly, it proved the browser's audio path was *healthy*, delivering
   exactly the boost its source code promised.
7. Final measurement, everything at maximum, real music playing: the music
   sat ~13 dB below the machine's own measured ceiling — and its digital
   peaks were already touching full scale. Verdict: **nothing was broken.**
   Low speaker ceiling, quiet-mastered content, normalization that never
   boosts. No slider could ever have fixed it.
8. The fix — squash peaks, lift valleys — measured **+10.5 dB** the same
   night. The owner's comfortable volume now sits at 44% of a slider that
   used to be pinned past 100%.

Twenty minutes of honest measurement disproved fifteen months of assumption
— and two of the AI's own confident theories along the way, both shot down
by an ordinary human looking at his own screen. The only mathematical
operation that adds loudness under a fixed ceiling is compression — which,
funnily enough, is exactly what the project's own abandoned compander math
had been saying all along.

It took an expensive frontier AI model running at its maximum reasoning
setting for a whole evening to untangle this — the kind of compute bill most
people on Earth cannot and should not pay. That is precisely why this repo
exists. There are millions of kids out there on hand-me-down laptops living
on less than a dollar a day. They cannot buy the diagnosis. They should not
have to. The fix itself costs nothing: a 400 KB plugin package and thirty
lines of configuration.

**The lesson, if you want it:** when something stays broken despite correct
math, stop improving the math and go measure the premise. And when you
finally pay for the answer — give it away.

Sharing is caring. It's nice to be nice.

---

## Track 2 — for developers

### What it actually installs

**PipeWire path** (auto-detected):
- `~/.config/pipewire/filter-chain.conf.d/60-loudness.conf` — a
  `libpipewire-module-filter-chain` graph hosting one LADSPA **SC4 mono**
  compressor (`sc4m`, from `swh-plugins`), auto-replicated per channel,
  exposed as sink `loudness_sink` ("Speakers + Loudness"), with
  `playback.props.target.object` pointed at your detected hardware sink.
- `~/.config/systemd/user/loudness-sink.service` — runs
  `pipewire -c filter-chain.conf` (the stock client config, which includes
  user fragments). Enabled, survives reboots.
- Default sink switched to `loudness_sink` via `pactl set-default-sink`.

**PulseAudio path** (no PipeWire found):
- `pactl load-module module-ladspa-sink ... plugin=sc4m_1916 label=sc4m
  control=0,3,150,-20,4,8,12` now, plus persistence lines appended to
  `~/.config/pulse/default.pa` (created with `.include /etc/pulse/default.pa`
  first if absent — a bare user default.pa would otherwise replace your
  whole config).

### The parameters, and why

```
RMS mode, attack 3 ms, release 150 ms,
threshold -20 dB, ratio 4:1, knee 8 dB, makeup gain +12 dB
```

Streaming content sits at −14…−20 LUFS. Threshold −20 dB puts the knee right
at typical program level; 4:1 above it, +12 dB makeup below it. Worst case is
self-limiting by construction: a 0 dBFS peak is 20 dB over threshold, exits
at 5 dB + 12 dB makeup = **−3 dBFS — no clipping, mathematically**, no
lookahead needed at these time constants.

Verified on the reference machine (internal-mic A/B at matched settings):
**+10.5 dB RMS on real music, peaks unchanged, 13.9 µs + 23.1 µs busy per
21.3 ms quantum ≈ 0.2% of one 2012 core.**

### The measurement method (steal this)

The diagnosis method matters more than the fix. Digital stream taps
(`pw-record --target <node>`) silently drop chunks under CPU load on weak
machines and will fabricate 20 dB "losses" that send you chasing ghosts.
The trustworthy instrument is the laptop's own microphone plus a
**simultaneous dual-band pilot**: play a 400 Hz reference tone through the
known-good path and your test signal at another frequency (e.g. 2731 Hz)
through the path under test, record both at once, compare narrow band-passed
peaks. Capture dropouts hit both bands equally and cancel out of the
comparison. Calibrate the speaker+mic frequency-response delta between the
two bands once (play both tones through the same path), and you can resolve
1 dB differences with a built-in mic on a machine that lies to every other
probe.

### Relationship to Gorilla Unleashed Firefox

The same compressor (same parameters, implemented as an envelope follower in
`AudioStream.cpp`, gain driven by the envelope — never a memoryless
waveshaper) ships inside the
[Gorilla Unleashed Firefox 154](https://github.com/gorillanobakaa-dot/firefox.154)
build, verified by two-point transfer test: a −30 dBFS tone exits +10 dB
hotter, a −12 dBFS tone exits +0.5 dB — compression, not gain. This script
is the browser-independent, every-app version of the same idea. Running both
is fine in practice (the browser stage rarely leaves its limiter engaged),
but if you find it over-dense, either works alone.

### Requirements & compatibility

| Needs | Notes |
|---|---|
| Linux, PipeWire *or* PulseAudio | auto-detected via `pactl info` |
| `pactl` | package `pulseaudio-utils` (harmless on PipeWire systems) |
| `swh-plugins` (LADSPA SC4) | ~400 KB; installer offers apt/dnf/pacman/zypper, with an IPv4 retry for broken IPv6 networks |
| systemd user session | PipeWire path only |

### Operations

```bash
python3 speaker_loudness_setup.py --status     # look, touch nothing
python3 speaker_loudness_setup.py              # install (asks first)
python3 speaker_loudness_setup.py --yes        # non-interactive
python3 speaker_loudness_setup.py --uninstall  # full revert
python3 speaker_loudness_setup.py --armor      # chattr +i the installed files
python3 speaker_loudness_setup.py --disarm     # make them editable again
```

`--armor` exists because of a real incident: a bulk cleanup script once
deleted the audio configs *and* the mask that kept a broken service down.
Immutable flags make fixes survive your own future tidiness.

### License

MIT. Take it, ship it, translate it, put it on the school lab image.
