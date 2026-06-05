# Edge Multi Profile

A Python GUI application to **manage and open multiple isolated Microsoft Edge profiles** at once. Each profile uses its own data directory (`--user-data-dir`), so cookies, logins, history, etc. are fully separated.

## Features

- Add / rename / delete profiles. Deleting a profile **closes its open Edge windows first**, then removes its data folder (no leftover locked files).
- Open **one**, **multiple selected profiles**, or **all** with a single click.
- Each profile is an independent Edge session (log in to many different accounts).
- Icon-only toolbar with hover tooltips.
- Settings: Edge path (auto-detected), **multiple start URLs** (one per line, empty by default — opens each in a tab), delay between launches, and **Clear profiles folder** (closes all sessions and wipes `EdgeProfiles/profiles`).
- Modern dark UI (customtkinter).
- Data is stored **portably** in an `EdgeProfiles` folder next to the app.

## Requirements

- Windows + Microsoft Edge.
- Python 3.10+ (tested with 3.14).

## Run (dev mode)

```bash
pip install -r requirements.txt
python main.py
```

## Build a .exe file

Run the script:

```bash
build.bat
```

Or manually:

```bash
pip install -r requirements.txt
python tools/make_version.py
python -m PyInstaller --noconfirm --onefile --windowed --name "EdgeMultiProfile" --icon "assets\icon.ico" --version-file "version_info.txt" --paths src --collect-submodules edge_multi --collect-all customtkinter main.py
```

The exe version (shown in Windows file properties) comes from `__version__` in `src/edge_multi/__init__.py`; bump it there before building a new release.

### Regenerating the app icon

The exe icon is `assets/icon.ico`, generated from `assets/icon.png`. To recreate it after changing the source image:

```bash
pip install pillow
python tools/make_icon.py
```

After building, the file is located at `dist\EdgeMultiProfile.exe`. You can copy the exe elsewhere; the `EdgeProfiles` data folder will be created next to the exe.

## Project structure

```
OpenChrome/
├─ main.py                     # entry point
├─ requirements.txt
├─ build.bat                   # exe packaging script
├─ README.md
├─ assets/
│  ├─ icon.png                 # source icon image
│  └─ icon.ico                 # app icon used by the exe
├─ tools/
│  └─ make_icon.py             # regenerate icon.ico from icon.png
└─ src/edge_multi/
   ├─ __init__.py
   ├─ config.py                # paths, settings, Edge detection
   ├─ profile_manager.py       # profile CRUD, persists profiles.json
   ├─ edge_launcher.py         # launches Edge for each profile
   └─ app.py                   # GUI (customtkinter)
```

## Notes

- Deleting a profile removes all of its browsing data (cookies, logins).
- The app does not collect or send any data externally.
