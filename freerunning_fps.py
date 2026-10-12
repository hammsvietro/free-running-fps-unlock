#!/usr/bin/env python3
"""Free Running (Steam, 2019 release): raise the 30 fps cap.

The game hard-codes a 30 fps target. Its engine already supports other rates, and gameplay uses
real elapsed time, so this patch picks a different built-in rate and the game speed stays correct.
It changes 19 bytes of your own FreeRunning.exe. It ships no game code.

  python3 freerunning_fps.py                 patch to 150 fps (pair with vsync or a cap)
  python3 freerunning_fps.py --fps 60        patch to 60 fps (also 120 or 150)
  python3 freerunning_fps.py --cap 144       Proton/Linux only: also write dxvk.conf capping fps
  python3 freerunning_fps.py --revert        restore the original exe
  python3 freerunning_fps.py --status        show what is installed
  add --game-dir "<folder>" if the game is not found automatically

Standard library only. Works on Windows, Linux and Steam Deck (desktop mode, Konsole).
"""
import argparse
import hashlib
import os
import re
import struct
import sys

APP_ID = "254940"
EXE = "FreeRunning.exe"
ORIGINAL_SHA256 = "4dea45764fa37cd331b53c875b73a1e81233c7ce47e40c00c0a6a1551dafbaa5"
FPS_CHOICES = (60, 120, 150)  # engine table 0x4edd90: 60->50, 120->25, 150->20 ticks of 1/3000 s

# File offsets (VA - 0x400c00). Hook: mov esi,[ebp+0x34]; push [ebp+0x2c] -> jmp cave; nop.
HOOK_OFF, HOOK_ORIG = 0xED1A2, bytes.fromhex("8b7534ff752c")
HOOK_NEW = bytes.fromhex("e99b00000090")
# Cave in int3 padding at VA 0x4ede42: push [ebp+0x2c]; mov esi,<fps>; jmp 0x4edda8.
CAVE_OFF, CAVE_ORIG = 0xED242, b"\xcc" * 13


def cave_bytes(fps):
    return b"\xff\x75\x2c\xbe" + struct.pack("<I", fps) + bytes.fromhex("e959ffffff")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def steam_roots():
    home = os.path.expanduser("~")
    roots = [
        os.path.join(home, ".local/share/Steam"),
        os.path.join(home, ".steam/steam"),
        os.path.join(home, ".var/app/com.valvesoftware.Steam/.local/share/Steam"),
        os.path.join(home, "Library/Application Support/Steam"),
    ]
    for env in ("PROGRAMFILES(X86)", "PROGRAMFILES"):
        if os.environ.get(env):
            roots.append(os.path.join(os.environ[env], "Steam"))
    return [r for r in roots if os.path.isdir(r)]


def find_game_dir():
    seen = set()
    for root in steam_roots():
        libs = [root]
        vdf = os.path.join(root, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            text = open(vdf, encoding="utf-8", errors="replace").read()
            libs += [p.replace("\\\\", "\\") for p in re.findall(r'"path"\s+"([^"]+)"', text)]
        for lib in libs:
            cand = os.path.join(lib, "steamapps", "common", "Free Running")
            key = os.path.realpath(cand)
            if key not in seen and os.path.isfile(os.path.join(cand, EXE)):
                return cand
            seen.add(key)
    return None


def state(data):
    """Return ('original'|'patched'|'unknown', fps or None)."""
    hook = data[HOOK_OFF:HOOK_OFF + 6]
    cave = data[CAVE_OFF:CAVE_OFF + 13]
    if hook == HOOK_ORIG and cave == CAVE_ORIG:
        return ("original", 30) if sha256(data) == ORIGINAL_SHA256 else ("unknown", None)
    if hook == HOOK_NEW and cave[:4] == b"\xff\x75\x2c\xbe":
        fps = struct.unpack("<I", cave[4:8])[0]
        if cave == cave_bytes(fps) and sha256(unpatch(data)) == ORIGINAL_SHA256:
            return "patched", fps
    return "unknown", None


def unpatch(data):
    out = bytearray(data)
    out[HOOK_OFF:HOOK_OFF + 6] = HOOK_ORIG
    out[CAVE_OFF:CAVE_OFF + 13] = CAVE_ORIG
    return bytes(out)


def write_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description="Raise Free Running's 30 fps cap.")
    ap.add_argument("--game-dir", help="folder that contains FreeRunning.exe")
    ap.add_argument("--fps", type=int, default=150, choices=FPS_CHOICES)
    ap.add_argument("--cap", type=int, metavar="N",
                    help="Proton/Linux: write dxvk.conf with vsync off and an N fps limit")
    ap.add_argument("--revert", action="store_true", help="restore the original exe")
    ap.add_argument("--status", action="store_true", help="show the current state and exit")
    args = ap.parse_args()

    game = args.game_dir or find_game_dir()
    if not game or not os.path.isfile(os.path.join(game, EXE)):
        sys.exit("Free Running not found. Pass --game-dir \"<folder with FreeRunning.exe>\".")
    exe = os.path.join(game, EXE)
    data = open(exe, "rb").read()
    st, fps = state(data)
    print(f"game: {game}\nexe:  {st}" + (f" ({fps} fps)" if fps else ""))

    if st == "unknown":
        sys.exit("This FreeRunning.exe is not the known Steam version (or was changed by something\n"
                 "else). Nothing was modified. Try Steam > Properties > Installed Files > Verify.")
    if args.status:
        return

    if args.revert:
        if st == "original":
            print("already original")
        else:
            write_atomic(exe, unpatch(data))
            print("restored original exe")
        conf = os.path.join(game, "dxvk.conf")
        if os.path.isfile(conf) and "freerunning_fps" in open(conf).read():
            os.remove(conf)
            print("removed dxvk.conf")
        return

    if st == "patched" and fps == args.fps:
        print("already patched")
    else:
        backup = exe + ".orig"
        if not os.path.exists(backup):
            write_atomic(backup, unpatch(data))
        out = bytearray(unpatch(data))
        out[HOOK_OFF:HOOK_OFF + 6] = HOOK_NEW
        out[CAVE_OFF:CAVE_OFF + 13] = cave_bytes(args.fps)
        write_atomic(exe, bytes(out))
        assert state(bytes(out)) == ("patched", args.fps)
        print(f"patched to {args.fps} fps (backup: {os.path.basename(backup)})")

    if args.cap:
        with open(os.path.join(game, "dxvk.conf"), "w") as f:
            f.write("# written by freerunning_fps; --revert removes it\n"
                    f"d3d9.presentInterval = 0\nd3d9.maxFrameRate = {args.cap}\n")
        print(f"wrote dxvk.conf (vsync off, {args.cap} fps limit; only used under Proton/DXVK)")


if __name__ == "__main__":
    main()
