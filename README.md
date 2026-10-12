# Free Running FPS Unlock

Removes the 30 fps cap in [Free Running](https://store.steampowered.com/app/254940/) (Steam).
Game speed stays normal. The script changes 19 bytes of your own `FreeRunning.exe`. It refuses
any exe that isn't the current Steam version, and it keeps a backup.

## Install

Requires Python 3 (already installed on Linux and Steam Deck).

**Linux / Steam Deck** (Desktop Mode → Konsole):

```
curl -O https://raw.githubusercontent.com/hammsvietro/free-running-fps-unlock/main/freerunning_fps.py
python3 freerunning_fps.py
```

**Windows** (download `freerunning_fps.py`, then in that folder):

```
py freerunning_fps.py
```

The game is found automatically in any Steam library. If it isn't, add
`--game-dir "<folder with FreeRunning.exe>"`.

## Options

| Command | Effect |
|---|---|
| `python3 freerunning_fps.py` | 150 fps target (default). Vsync or a frame limiter caps it to your refresh rate. |
| `--fps 60` / `--fps 120` | other targets the engine supports |
| `--cap 144` | Proton only: writes `dxvk.conf` with vsync off and a 144 fps limit |
| `--status` | show current state |
| `--revert` | restore the original exe |

Steam updates or "Verify integrity of game files" restore the original exe. Run the script
again afterwards.
