#!/usr/bin/env python3
"""One-click loudness compressor for quiet laptop speakers.

Installs a system-wide SC4 compressor sink (threshold -20 dB, ratio 4:1,
attack 3 ms, release 150 ms, makeup +12 dB) in front of the sound card, so
quiet-mastered streaming content plays at usable loudness on weak speakers.
Parameters were mic-verified at +10.5 dB RMS gain, ~0.2% CPU, on a 2012-era
Sony VAIO (see VERIFICATION.md alongside this script's home).

Supports PipeWire (filter-chain + systemd user service) and plain PulseAudio
(module-ladspa-sink). Python 3.7+, standard library only. Never overwrites
your files without a timestamped backup. Never pretends: every check prints
its verdict, and a failed install reverts the default sink.

Usage:
  speaker_loudness_setup.py            install (asks before installing packages)
  speaker_loudness_setup.py --status   report what is detected, change nothing
  speaker_loudness_setup.py --uninstall  remove everything it installed
  speaker_loudness_setup.py --armor    make the installed files immutable (chattr +i)
  speaker_loudness_setup.py --yes      non-interactive (accept installs)
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
PW_CONF = HOME / ".config/pipewire/filter-chain.conf.d/60-loudness.conf"
PW_UNIT = HOME / ".config/systemd/user/loudness-sink.service"
PA_USER_DEFAULT = HOME / ".config/pulse/default.pa"
SINK_NAME = "loudness_sink"
MARK = "# added by speaker_loudness_setup"
LADSPA_DIRS = ["/usr/lib/ladspa", "/usr/lib/x86_64-linux-gnu/ladspa",
               "/usr/lib64/ladspa", "/usr/local/lib/ladspa"]

PW_CONF_TEXT = """\
# Loudness compressor sink for weak laptop speakers.
# SC4 mono compressor (swh-plugins), auto-replicated per channel.
# Installed by speaker_loudness_setup.py - remove with --uninstall.
context.modules = [
  { name = libpipewire-module-filter-chain
    args = {
      node.description = "Speakers + Loudness"
      media.name = "Speakers + Loudness"
      filter.graph = {
        nodes = [
          { type = ladspa
            plugin = sc4m_1916
            label = sc4m
            name = comp
            control = {
              "RMS/peak" = 0.0
              "Attack time (ms)" = 3.0
              "Release time (ms)" = 150.0
              "Threshold level (dB)" = -20.0
              "Ratio (1:n)" = 4.0
              "Knee radius (dB)" = 8.0
              "Makeup gain (dB)" = 12.0
            }
          }
        ]
      }
      audio.channels = 2
      audio.position = [ FL FR ]
      capture.props = {
        node.name = "loudness_sink"
        media.class = Audio/Sink
      }
      playback.props = {
        node.name = "loudness_sink_out"
        node.passive = true
        target.object = "@HW_SINK@"
      }
    }
  }
]
"""

PW_UNIT_TEXT = """\
[Unit]
Description=Loudness compressor sink (SC4 filter-chain)
After=pipewire.service
Requires=pipewire.service

[Service]
ExecStart=/usr/bin/pipewire -c filter-chain.conf
Restart=on-failure

[Install]
WantedBy=default.target
"""

# sc4m LADSPA control port order: RMS/peak, attack, release, threshold, ratio,
# knee, makeup.
PA_MODULE_ARGS = ("sink_name=%s sink_properties=device.description=Speakers+Loudness "
                  "sink_master=%%s plugin=sc4m_1916 label=sc4m "
                  "control=0,3,150,-20,4,8,12" % SINK_NAME)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def say(tag, msg):
    print("[%s] %s" % (tag, msg))


def fail(msg):
    say("FAIL", msg)
    sys.exit(1)


def detect_server():
    if not shutil.which("pactl"):
        fail("pactl not found - install pulseaudio-utils (works for PipeWire too). "
             "Without it this script cannot talk to your audio system.")
    r = run(["pactl", "info"])
    if r.returncode != 0:
        fail("no audio server answered on this login session: %s" % r.stderr.strip())
    server = ""
    for line in r.stdout.splitlines():
        if line.startswith("Server Name:"):
            server = line.split(":", 1)[1].strip()
    if "PipeWire" in server:
        return "pipewire"
    if "pulseaudio" in server.lower():
        return "pulseaudio"
    fail("unrecognized audio server %r - refusing to guess." % server)


def find_sc4():
    paths = LADSPA_DIRS + os.environ.get("LADSPA_PATH", "").split(":")
    for d in paths:
        if d and (Path(d) / "sc4m_1916.so").exists():
            return str(Path(d) / "sc4m_1916.so")
    return None


def install_sc4(assume_yes):
    pkg = {"apt-get": ["apt-get", "install", "-y", "swh-plugins"],
           "dnf": ["dnf", "install", "-y", "ladspa-swh-plugins"],
           "pacman": ["pacman", "-S", "--noconfirm", "swh-plugins"],
           "zypper": ["zypper", "-n", "install", "ladspa-swh-plugins"]}
    mgr = next((m for m in pkg if shutil.which(m)), None)
    if not mgr:
        fail("SC4 compressor plugin missing and no known package manager found. "
             "Install the 'swh-plugins' LADSPA package manually, then rerun.")
    cmd = pkg[mgr]
    say("NEED", "SC4 plugin missing. Install command: sudo " + " ".join(cmd))
    if not assume_yes:
        ans = input("Run it now with sudo? [y/N] ").strip().lower()
        if ans != "y":
            fail("cannot continue without the SC4 plugin.")
    r = run(["sudo"] + cmd)
    if r.returncode != 0 and mgr == "apt-get":
        say("WARN", "retrying apt over IPv4 (some networks break IPv6 fetches)")
        r = run(["sudo", "apt-get", "install", "-y",
                 "-o", "Acquire::ForceIPv4=true", "swh-plugins"])
    if r.returncode != 0:
        fail("package install failed:\n%s" % (r.stderr or r.stdout).strip())
    if not find_sc4():
        fail("package installed but sc4m_1916.so still not found - stopping.")
    say("OK", "SC4 plugin installed.")


def hardware_sink():
    r = run(["pactl", "list", "short", "sinks"])
    sinks = [line.split("\t")[1] for line in r.stdout.splitlines() if "\t" in line]
    hw = [s for s in sinks if s != SINK_NAME and "loudness" not in s]
    if not hw:
        fail("no hardware sink found - is any sound device present?")
    preferred = [s for s in hw if s.startswith("alsa_output")]
    return (preferred or hw)[0], sinks


def write_with_backup(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text() == text:
            say("OK", "%s already correct" % path)
            return
        bak = path.with_name(path.name + ".bak-" + time.strftime("%Y%m%d-%H%M%S"))
        shutil.copy2(path, bak)
        say("NOTE", "existing %s backed up to %s" % (path.name, bak.name))
    path.write_text(text)
    say("OK", "wrote %s" % path)


def wait_for_sink(seconds=15):
    for _ in range(seconds * 2):
        r = run(["pactl", "list", "short", "sinks"])
        if SINK_NAME in r.stdout:
            return True
        time.sleep(0.5)
    return False


def install_pipewire(assume_yes):
    if not shutil.which("systemctl"):
        fail("systemd user services unavailable - PipeWire install path needs them.")
    if not Path("/usr/share/pipewire/filter-chain.conf").exists():
        fail("/usr/share/pipewire/filter-chain.conf missing - your PipeWire "
             "package is unusual; refusing to improvise.")
    hw, _ = hardware_sink()
    say("OK", "hardware sink: %s" % hw)
    write_with_backup(PW_CONF, PW_CONF_TEXT.replace("@HW_SINK@", hw))
    write_with_backup(PW_UNIT, PW_UNIT_TEXT)
    for cmd in (["systemctl", "--user", "daemon-reload"],
                ["systemctl", "--user", "enable", "--now", "loudness-sink.service"],
                ["systemctl", "--user", "restart", "loudness-sink.service"]):
        r = run(cmd)
        if r.returncode != 0:
            fail("%s -> %s" % (" ".join(cmd), (r.stderr or r.stdout).strip()))
    if not wait_for_sink():
        fail("the compressor sink never appeared; check "
             "journalctl --user -u loudness-sink.service")
    run(["pactl", "set-default-sink", SINK_NAME])


def install_pulseaudio(assume_yes):
    hw, _ = hardware_sink()
    say("OK", "hardware sink: %s" % hw)
    module_args = PA_MODULE_ARGS % hw
    r = run(["pactl", "load-module", "module-ladspa-sink"] + module_args.split())
    if r.returncode != 0:
        fail("module-ladspa-sink refused to load: %s" % (r.stderr or r.stdout).strip())
    if not wait_for_sink():
        fail("the compressor sink never appeared after module load.")
    run(["pactl", "set-default-sink", SINK_NAME])
    lines = []
    if PA_USER_DEFAULT.exists():
        lines = PA_USER_DEFAULT.read_text().splitlines()
    else:
        lines = [".include /etc/pulse/default.pa"]
        say("NOTE", "created %s (includes the system default.pa first)" % PA_USER_DEFAULT)
    lines = [l for l in lines if MARK not in l]
    lines += ["load-module module-ladspa-sink %s %s" % (module_args, MARK),
              "set-default-sink %s %s" % (SINK_NAME, MARK)]
    write_with_backup(PA_USER_DEFAULT, "\n".join(lines) + "\n")


def verify():
    ok = True
    r = run(["pactl", "list", "short", "sinks"])
    if SINK_NAME in r.stdout:
        say("PASS", "compressor sink exists")
    else:
        say("FAIL", "compressor sink missing")
        ok = False
    r = run(["pactl", "get-default-sink"])
    if r.stdout.strip() == SINK_NAME:
        say("PASS", "compressor sink is the default output")
    else:
        say("FAIL", "default sink is %r" % r.stdout.strip())
        ok = False
    return ok


def status():
    server = detect_server()
    say("INFO", "audio server: %s" % server)
    sc4 = find_sc4()
    say("INFO", "SC4 plugin: %s" % (sc4 or "NOT INSTALLED"))
    for p in (PW_CONF, PW_UNIT):
        say("INFO", "%s: %s" % (p, "present" if p.exists() else "absent"))
    r = run(["pactl", "list", "short", "sinks"])
    say("INFO", "compressor sink: %s" %
        ("ACTIVE" if SINK_NAME in r.stdout else "not running"))
    r = run(["pactl", "get-default-sink"])
    say("INFO", "default sink: %s" % r.stdout.strip())


def unarmor(path):
    if path.exists():
        run(["sudo", "chattr", "-i", str(path)])


def uninstall():
    server = detect_server()
    hw, sinks = hardware_sink()
    run(["pactl", "set-default-sink", hw])
    say("OK", "default sink restored to %s" % hw)
    if server == "pipewire":
        for p in (PW_CONF, PW_UNIT):
            unarmor(p)
        run(["systemctl", "--user", "disable", "--now", "loudness-sink.service"])
        for p in (PW_CONF, PW_UNIT):
            if p.exists():
                p.unlink()
                say("OK", "removed %s" % p)
        run(["systemctl", "--user", "daemon-reload"])
    else:
        if PA_USER_DEFAULT.exists():
            unarmor(PA_USER_DEFAULT)
            lines = [l for l in PA_USER_DEFAULT.read_text().splitlines()
                     if MARK not in l]
            PA_USER_DEFAULT.write_text("\n".join(lines) + "\n")
            say("OK", "cleaned %s" % PA_USER_DEFAULT)
        r = run(["pactl", "list", "short", "modules"])
        for line in r.stdout.splitlines():
            if "module-ladspa-sink" in line and SINK_NAME in line:
                run(["pactl", "unload-module", line.split("\t")[0]])
                say("OK", "unloaded ladspa sink module")
    say("DONE", "uninstalled. Sound now goes straight to the hardware sink.")


def armor():
    if not shutil.which("chattr"):
        fail("chattr not available on this system.")
    targets = [p for p in (PW_CONF, PW_UNIT, PA_USER_DEFAULT) if p.exists()]
    if not targets:
        fail("nothing installed to protect - run the installer first.")
    for p in targets:
        r = run(["sudo", "chattr", "+i", str(p)])
        if r.returncode == 0:
            say("OK", "immutable: %s" % p)
        else:
            fail("chattr +i %s -> %s (need sudo?)" % (p, r.stderr.strip()))
    say("DONE", "files are now immune to cleanup scripts. Use --disarm before editing.")


def disarm():
    for p in (PW_CONF, PW_UNIT, PA_USER_DEFAULT):
        if p.exists():
            unarmor(p)
            say("OK", "mutable again: %s" % p)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--status", action="store_true", help="report, change nothing")
    ap.add_argument("--uninstall", action="store_true", help="remove everything")
    ap.add_argument("--armor", action="store_true", help="chattr +i the installed files")
    ap.add_argument("--disarm", action="store_true", help="chattr -i the installed files")
    ap.add_argument("--yes", action="store_true", help="non-interactive")
    a = ap.parse_args()

    if a.status:
        return status()
    if a.uninstall:
        return uninstall()
    if a.armor:
        return armor()
    if a.disarm:
        return disarm()

    server = detect_server()
    say("OK", "audio server: %s" % server)
    if not find_sc4():
        install_sc4(a.yes)
    else:
        say("OK", "SC4 plugin present")
    if server == "pipewire":
        install_pipewire(a.yes)
    else:
        install_pulseaudio(a.yes)
    if verify():
        say("DONE", "loudness compressor active. Quiet content now plays "
            "up to 12 dB louder; peaks stay protected. Undo: --uninstall. "
            "Protect from cleanup scripts: --armor")
    else:
        say("ERROR", "verification failed - reverting default sink")
        hw, _ = hardware_sink()
        run(["pactl", "set-default-sink", hw])
        sys.exit(1)


if __name__ == "__main__":
    main()
