# PPX - Cross-Platform Multimedia Utility Toolbox

A modern desktop application framework combining Vue 3 frontend with Python backend, providing PDF/Excel manipulation, system process management, digital seals, and local storage capabilities.

**Version:** V1.0.0 | **Author:** Jdassd | **License:** MIT

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Project Overview](#project-overview)
- [Technology Stack](#technology-stack)
- [Directory Structure](#directory-structure)
- [Installation & Setup](#installation--setup)
- [Development Workflow](#development-workflow)
- [Key Features](#key-features)
- [API Reference](#api-reference)
- [Building & Deployment](#building--deployment)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/yourusername/PPX.git
cd PPX

# Initialize environment
pnpm install
pnpm run init

# Start development
pnpm run start

# Build for production
pnpm run build
```

---

## 📖 Project Overview

PPX is a **hybrid desktop application framework** that leverages:
- **Frontend:** Vue 3 + Element Plus for responsive UI
- **Backend:** Python for business logic and system operations
- **Desktop Engine:** Pywebview for cross-platform window management
- **Distribution:** PyInstaller for executable packaging

### Core Capabilities

| Feature | Purpose |
|---------|---------|
| **PDF Tools** | Merge, split, convert, extract, watermark PDFs |
| **Excel Tools** | Manipulate spreadsheets, import/export data |
| **System Utilities** | File dialogs, process management, system information |
| **Digital Seals** | Apply watermarks and digital signatures |
| **Data Storage** | Encrypted key-value storage with JSON/SQL backends |
| **Auto-Update** | GitHub releases-based version checking |
| **Process Manager** | Real-time system process monitoring |

---

## 🛠️ Technology Stack

### Frontend (GUI Layer)
```json
{
  "vue": "^3.2.47",
  "element-plus": "^2.3.4",
  "vite": "^4.3.1",
  "sass": "^1.62.0"
}
```

### Backend (Business Layer)
```
Python 3.8-3.11
├── pywebview 5.4          (Desktop window framework)
├── PyInstaller 6.12.0     (Executable packaging)
├── PyPDF2 3.0.1           (PDF manipulation)
├── openpyxl 3.1.5         (Excel operations)
├── psutil 5.9.8           (System monitoring)
├── httpx 0.27.2           (HTTP client)
├── TinyDB 4.8.2           (JSON database)
└── SQLAlchemy 2.0.7       (SQL ORM - optional)
```

### Build & Deployment
- **pnpm 8.x+** - Node package manager
- **Node.js 16.14+** - Runtime
- **Inno Setup** - Windows installer
- **dmgbuild 1.6.2** - macOS DMG creation
- **dpkg** - Linux DEB packaging

---

## 📁 Directory Structure

```
PPX_lobechat/
│
├── api/                              # Python API Backend
│   ├── api.py                        # Main API aggregator
│   ├── system.py                     # System utilities & file operations
│   ├── storage.py                    # Data persistence layer
│   ├── pdf.py                        # PDF manipulation
│   ├── excel.py                      # Excel operations
│   ├── seal.py                       # Digital seal/watermark
│   └── db/                           # Database layer
│       ├── orm.py                    # ORM interface
│       ├── json/                     # TinyDB implementation
│       └── sql/                      # SQLAlchemy implementation
│
├── gui/                              # Vue 3 Frontend
│   ├── src/
│   │   ├── main.js                   # Vue app entry point
│   │   ├── App.vue                   # Root component
│   │   ├── components/
│   │   │   ├── pdf/PdfTool.vue      # PDF manipulation UI
│   │   │   ├── excel/ExcelTool.vue  # Excel manipulation UI
│   │   │   ├── seal/SealTool.vue    # Digital seal UI
│   │   │   ├── system/ProcessManager.vue
│   │   │   ├── BtnUpdate.vue        # Auto-update button
│   │   │   └── SvgIcon/             # Icon components
│   │   └── assets/                   # Static resources
│   ├── vite.config.js               # Vite configuration
│   └── package.json
│
├── pyapp/                            # Python Application Runtime
│   ├── config/
│   │   └── config.py                 # Central configuration
│   ├── db/
│   │   ├── db.py                     # Database factory & init
│   │   ├── json/getKeyDB.py         # TinyDB encryption
│   │   └── sql/alembic/             # Migration scripts
│   ├── spec/
│   │   └── getSpec.py               # PyInstaller spec generator
│   ├── package/
│   │   ├── exe/getIss.py            # Windows installer generator
│   │   ├── dmg/getDMG.py            # macOS DMG generator
│   │   └── deb/makeDeb.py           # Linux DEB generator
│   ├── update/
│   │   └── update.py                # Auto-update mechanism
│   ├── requirements.txt             # Python dependencies
│   └── nodemon.json                 # HMR file watching config
│
├── static/                           # Packaged static assets
│   ├── db/                           # Database schemas
│   └── cache/                        # Runtime cache
│
├── main.py                           # Application entry point
├── package.json                      # Root pnpm scripts
├── PPX_README.md                     # Chinese documentation
├── AGENTS.md                         # Development guidelines
└── README.md                         # This file
```

---

## 💻 Installation & Setup

### Prerequisites

- **Node.js** 16.14+ and **pnpm** 8.x+
- **Python** 3.8-3.11 with pip
- **Git** for version control
- Platform-specific tools:
  - **Windows:** Visual C++ Build Tools, Inno Setup
  - **macOS:** Xcode command-line tools, dmgbuild
  - **Linux:** Build essentials, dpkg

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/PPX.git
cd PPX
```

### Step 2: Install Frontend Dependencies

```bash
pnpm install
```

### Step 3: Initialize Python Environment

```bash
pnpm run init
```

This command:
- Creates virtual environment in `pyapp/pyenv/`
- Installs Python dependencies from `pyapp/requirements.txt`
- Initializes database (TinyDB or SQLite based on config)
- Generates configuration files

### Step 4: Verify Installation

```bash
pnpm run start
```

The application should launch with:
- Frontend: Vue dev server (http://localhost:5173)
- Backend: Python API server running locally
- Desktop: Pywebview window displaying the UI

---

## 🔄 Development Workflow

### Development Mode

```bash
# Start development with hot reload
pnpm run start

# Automatic features:
# - Vue Vite dev server with HMR
# - Python backend with auto-reload (nodemon)
# - WebView displays latest changes
```

### Available Scripts

| Command | Purpose |
|---------|---------|
| `pnpm install` | Install Node dependencies |
| `pnpm run init` | Setup Python environment |
| `pnpm run start` | Launch dev mode |
| `pnpm run build` | Build production package |
| `pnpm run pre` | Pre-release with full logs |
| `pnpm run dev` | Frontend dev only (Vite) |
| `pnpm run build:gui` | Build Vue app only |

### Frontend Development

```bash
# Development server (requires backend running)
cd gui
pnpm run dev

# Build for production
pnpm run build

# Preview production build
pnpm run preview
```

### Backend Development

```bash
# Python hot reload (requires pyapp/pyenv activated)
cd pyapp
python -m nodemon main.py

# Or manually test API
python -c "from api import API; api = API(); print(api.get_system_info())"
```

---

## 🎯 Key Features

### 1. PDF Tools (`api/pdf.py`)

```python
# Merge multiple PDFs
api.merge_pdfs(["file1.pdf", "file2.pdf"], "output.pdf")

# Split PDF by pages
api.split_pdf("input.pdf", [0, 2, 5], "output/")

# Extract text
text = api.extract_pdf_text("input.pdf")

# Add watermark
api.add_watermark("input.pdf", "output.pdf", "CONFIDENTIAL")
```

### 2. Excel Tools (`api/excel.py`)

```python
# Read spreadsheet
data = api.read_excel("file.xlsx")

# Write to Excel
api.write_excel("output.xlsx", data)

# Apply formatting
api.format_excel("file.xlsx", {"header": True, "freeze_panes": True})
```

### 3. System Utilities (`api/system.py`)

```python
# File dialogs
file_path = api.open_file_dialog()
folder_path = api.open_folder_dialog()

# Process management
processes = api.get_processes()
api.terminate_process(pid)

# System information
info = api.get_system_info()  # CPU, RAM, Disk usage, etc.
```

### 4. Digital Seals (`api/seal.py`)

```python
# Apply seal/watermark
api.apply_seal("document.pdf", "output.pdf",
               text="Sealed", image="seal.png")
```

### 5. Data Storage (`api/storage.py`)

```python
# Key-value storage with encryption
api.set_value("user_token", "abc123xyz")
token = api.get_value("user_token")

# Delete key
api.delete_value("user_token")

# List all keys
keys = api.list_keys()
```

### 6. Auto-Update (`pyapp/update/update.py`)

Automatically checks GitHub releases and prompts user to update when new version available.

---

## 🔌 API Reference

### JavaScript to Python Communication

```javascript
// Call Python API method
await window.pywebview.api.get_system_info();

// With parameters
await window.pywebview.api.read_excel("file.xlsx");

// Error handling
try {
  const result = await window.pywebview.api.get_processes();
} catch (error) {
  console.error("API Error:", error);
}
```

### Python to JavaScript Communication

```python
# Evaluate JavaScript from Python
window.evaluate_js("alert('Message from Python')")

# Get JavaScript variable
window.evaluate_js("window.myVar = 'value'")
```

### Available API Methods

| Method | Parameters | Returns | Purpose |
|--------|-----------|---------|---------|
| `get_system_info()` | - | dict | System CPU, RAM, disk info |
| `get_processes()` | - | list | Running processes |
| `terminate_process(pid)` | pid: int | bool | Kill process |
| `open_file_dialog()` | - | str | File browser dialog |
| `read_excel(path)` | path: str | list | Read spreadsheet |
| `merge_pdfs(files, out)` | files: list, out: str | bool | Merge PDFs |
| `get_value(key)` | key: str | any | Get stored value |
| `set_value(key, value)` | key: str, value: any | bool | Store value |

---

## 📦 Building & Deployment

### Build for All Platforms

```bash
# Full production build (generates EXE, DMG, DEB)
pnpm run build

# Pre-release with detailed logs
pnpm run pre
```

### Platform-Specific Builds

#### Windows (EXE)

```bash
# Requires Inno Setup installed
cd pyapp/package/exe
python getIss.py

# Output: dist/PPX-V1.0.0-Setup.exe
```

#### macOS (DMG)

```bash
# Requires dmgbuild
cd pyapp/package/dmg
python getDMG.py

# Output: dist/PPX-V1.0.0.dmg
```

#### Linux (DEB)

```bash
# Requires dpkg
cd pyapp/package/deb
python makeDeb.py

# Output: dist/ppx_1.0.0_amd64.deb
```

### Distribution Channels

1. **GitHub Releases** - Primary distribution channel
2. **Direct Download** - Host executables on your website
3. **Package Managers** - Register on apt (Linux), homebrew (macOS), etc.

---

## ⚙️ Configuration

### Main Configuration (`pyapp/config/config.py`)

```python
# Database selection
DATABASE_TYPE = "json"  # or "sql"

# Application metadata
APP_NAME = "PPX"
APP_VERSION = "1.0.0"
DEVELOPER = "Jdassd"

# Auto-update settings
UPDATE_CHECK_INTERVAL = 86400  # seconds
GITHUB_REPO = "owner/repo"

# API settings
API_PORT = 5173
API_HOST = "127.0.0.1"
```

### Database Configuration

#### TinyDB (Default)

```python
# Lightweight JSON-based, no setup required
DATABASE_TYPE = "json"
DB_PATH = "static/db/data.json"
```

#### SQLite

```python
# Production-ready SQL database
DATABASE_TYPE = "sql"
DATABASE_URL = "sqlite:///static/db/app.db"

# Run migrations
python pyapp/db/sql/alembic/migrate.py upgrade head
```

### WebView Configuration

Edit `main.py` to customize:

```python
# Window properties
webview.create_window(
    title='PPX Toolbox',
    url='http://localhost:5173',  # dev mode
    width=1200,
    height=800,
    min_width=800,
    min_height=600,
    resizable=True,
    background_color='#ffffff'
)

# CEF mode for older Windows systems
os.environ['PYWEBVIEW_BROWSER'] = 'cef'
```

---

## 🐛 Troubleshooting

### Issue: Port Already in Use

**Error:** `Address already in use: ('127.0.0.1', 5173)`

**Solution:**
```bash
# Kill process using the port (Windows)
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :5173
kill -9 <PID>
```

### Issue: Python Virtual Environment Not Found

**Error:** `ModuleNotFoundError: No module named 'pywebview'`

**Solution:**
```bash
# Reinitialize Python environment
pnpm run init

# Or manually activate venv
source pyapp/pyenv/bin/activate  # macOS/Linux
pyapp\pyenv\Scripts\activate     # Windows
pip install -r pyapp/requirements.txt
```

### Issue: WebView Failed to Start

**Error:** `Error: WebView2 not installed` (Windows)

**Solution:**
- Install WebView2: https://developer.microsoft.com/en-us/microsoft-edge/webview2/
- Or use CEF mode: `export PYWEBVIEW_BROWSER=cef`

### Issue: Database Migration Failed

**Error:** `Alembic migration error`

**Solution:**
```bash
# Reset database and re-initialize
rm static/db/app.db
python pyapp/db/db.py  # Reinitialize

# Or run migrations manually
cd pyapp/db/sql/alembic
alembic upgrade head
```

### Issue: Build Fails on macOS/Linux

**Error:** `ModuleNotFoundError` or `Command not found`

**Solution:**
```bash
# Ensure all dependencies installed
pip install -r pyapp/requirements.txt
pip install dmgbuild

# Clear cache and rebuild
rm -rf dist build *.spec
pnpm run build
```

---

## 📚 Additional Resources

- **[PPX_README.md](./PPX_README.md)** - Comprehensive Chinese documentation
- **[AGENTS.md](./AGENTS.md)** - Development guidelines and conventions
- **Official Docs:**
  - [Vue 3](https://vuejs.org/)
  - [Pywebview](https://pywebview.kivy.org/)
  - [Element Plus](https://element-plus.org/)
  - [PyInstaller](https://pyinstaller.org/)

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m "Add your feature"`
4. Push branch: `git push origin feature/your-feature`
5. Open Pull Request

**Please review [AGENTS.md](./AGENTS.md) for code style and conventions.**

---

## 📄 License

MIT License - see LICENSE file for details

---

## 👨‍💻 Author

**Jdassd** - Full-stack developer and maintainer

**Contact:** [Your Contact Info]

---

## 📝 Changelog

### V1.0.0 (Current)
- Initial stable release
- Cross-platform desktop application support
- PDF, Excel, and system utility tools
- Auto-update mechanism
- Hybrid Python-JavaScript architecture

### Version History
See [PPX_README.md](./PPX_README.md) for complete changelog (V1.0.0 - V5.3.3)

---

**Last Updated:** 2025-11-12
**Repository:** PPX_lobechat
**Branch:** pc_tools2
