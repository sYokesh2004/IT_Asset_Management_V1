# IT Asset Management System — Version 1

ByteCraftex IT Asset Manager

A modifiable Windows desktop application built with Python, PySide6 and SQLite.

## Features
- Dashboard with asset status counts
- Asset register: add, edit, search and retire assets
- Type-specific registration fields: CPU, server and laptop component details are shown only for those devices
- Automatic unique asset IDs
- Department/room group records (Parent IDs)
- Searchable groups with connected-asset details
- Fault reporting and fault history
- Asset movement history
- Movement destinations use Department and Parent Group IDs and update the asset assignment
- Fault and movement forms show asset details before entering report information
- QR sticker generation (QR code encodes only the Asset ID)
- Export asset register to Excel
- Local SQLite database and backup

## 1. Install Python
Install Python 3.11 or newer from https://www.python.org/downloads/windows/
During installation, select **Add Python to PATH**.

## 2. Open the project folder
Extract the ZIP to a normal folder, for example:
`C:\\ITAssetManagement`

Open Command Prompt in that folder.

## 3. Create an environment and install packages
```bat
py -m venv .venv
.venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Run
```bat
python main.py
```

The database is created automatically at:
`data/asset_management.db`

Back up from the app using **Backup Database**. Keep backups on another drive too.
To start with an empty database, use **Clear All Data** in the sidebar. This permanently
deletes all departments, groups, assets, fault reports, repairs, and movement history
while keeping the database structure. Make a backup first if any existing records may
be needed later.

Application events and errors are recorded in:
`logs/application.log`

The log file rotates automatically after it reaches 2 MB, keeping up to three
older log files (`application.log.1`, `.2`, and `.3`).

## 5. Build a Windows EXE
With the virtual environment active:
```bat
pyinstaller --noconfirm --clean --windowed --name ITAssetManagement --icon assets\app-icon.ico --add-data "assets;assets" main.py
robocopy data dist\ITAssetManagement\data /E
```
The executable will be under `dist\\ITAssetManagement\\ITAssetManagement.exe` (exact output may vary by PyInstaller version).

Windows may cache taskbar icons. If an older Python icon remains after updating,
close all running copies of the app and restart Windows Explorer or sign out and
back in once. Build a new EXE after changing the icon; an already-created EXE
cannot update its embedded taskbar icon.

## Customise the design
- `styles.py`: colors, fonts, buttons, tables and general appearance.
- `main.py`: sidebar, dashboard, pages and forms.
- `db.py`: database schema and database operations.

You can change the colors in `styles.py` without changing database code. Branding assets
are stored in `assets/company-logo.png`, `assets/app-logo.png`, and `assets/app-icon.ico`.

## Asset ID format
Example IDs:
- Parent group: `APS-CAL-001`
- Desktop CPU: `APS-CPU-0001`
- Monitor: `APS-MON-0001`
- Keyboard: `APS-KBD-0001`

IDs are generated automatically and are not reused. If you want different prefixes, change `ASSET_PREFIXES` in `db.py`.

## Important notes
- This is a Version 1 starter application. Test it with sample records before importing official inventory.
- SQLite is intended for this single-computer version. Do not put this database on a shared network drive for simultaneous multi-user access. A future multi-user version should use a server database and an API.
- The app is not a substitute for a tested backup policy. Keep periodic backups outside the PC.
