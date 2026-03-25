# 🔍 SAP Codebase Chat

> **Chat with your SAP Integration Suite / CPI project using Google Gemini.**  
> Upload any SAP project folder, understand its structure, flows, scripts, and
> configuration — all through a natural-language chat interface.

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red)
![Gemini](https://img.shields.io/badge/Google%20Gemini-2.0%20Flash-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

| Feature | Detail |
|---|---|
| 📁 **Universal folder support** | Works with any SAP CPI project structure — no hardcoding |
| 📄 **Multi-format file reading** | `.iflw`, `.groovy`, `.prop`, `.propdef`, `.xml`, `.wsdl`, `.xsl`, `.json`, `.yaml`, `.MF`, `.project`, and more |
| 🗺️ **Directory tree visualisation** | Sidebar renders the full project tree at a glance |
| 💬 **Conversational chat** | Full multi-turn conversation with memory |
| 🖼️ **Image-aware chat** | Attach screenshots, flow diagrams, or error images for analysis |
| 🤖 **SAP-aware AI** | System prompt pre-loaded with SAP CPI/iFlow expertise |
| 🔒 **Local-first** | Your code never leaves your machine (only sent to Gemini API) |
| 📦 **ZIP upload** | Zip your project and upload directly — no need to share paths |

---

## 🍎 Running on a Mac — Complete Beginner's Guide

> **No prior experience needed.** Follow these steps exactly, one at a time.  
> Every command below is typed into the **Terminal** app on your Mac.

---

### How to open Terminal

Press **⌘ Command + Space**, type `Terminal`, and press **Enter**.  
A window will open where you type commands. Keep it open throughout all the steps below.

---

### Step 1 — Install Homebrew (Mac's package manager)

Homebrew is a tool that makes installing developer software easy on a Mac.  
Paste this entire line into Terminal and press **Enter**:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

> It may ask for your Mac login password. Type it and press Enter — nothing will show on screen while typing, that's normal.  
> This takes about 2–5 minutes.

---

### Step 2 — Install Python

```bash
brew install python
```

Once done, confirm Python installed correctly:

```bash
python3 --version
```

You should see something like `Python 3.12.x` ✅

---

### Step 3 — Install Git

Git is the tool used to download the project from GitHub.

```bash
brew install git
```

Confirm it installed:

```bash
git --version
```

You should see something like `git version 2.x.x` ✅

---

### Step 4 — Clone (download) the project to your Desktop

First, navigate to your Desktop:

```bash
cd ~/Desktop
```

Then download the project:

```bash
git clone https://github.com/Ananth170404/sap-codebase-chat.git
```


Now enter the downloaded folder:

```bash
cd sap-codebase-chat
```

---

### Step 5 — Create a virtual environment

A virtual environment keeps this project's packages neatly separated from the rest of your Mac.

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

> ✅ You'll know it worked when you see `(venv)` appear at the start of your Terminal prompt.

---

### Step 6 — Install the required packages

```bash
pip install -r requirements.txt
```

This downloads and installs Streamlit, the Gemini SDK, and everything else the app needs. Takes 1–2 minutes.

---

### Step 7 — Get your Gemini API Key

1. Open your browser and go to **https://aistudio.google.com/app/apikey**
2. Sign in with your Google account
3. Click **Create API Key**
4. Copy the key — it looks like `AIzaSyXXXXXXXX...`

You'll paste it into the app in the next step — no need to save it anywhere yet.

---

### Step 8 — Run the app

```bash
streamlit run app.py
```

Your browser will automatically open at **http://localhost:8501** with the app running. 🎉

---

### Step 9 — Load your SAP project and start chatting

1. Paste your **Gemini API key** in the sidebar on the left
2. Choose **Upload ZIP File** to upload a zipped SAP project, or **Local Folder Path** to point to a folder on your Mac
3. Click **Load Project**
4. Type your question in the chat box at the bottom and press Enter

---

### Stopping the app

Go back to Terminal and press **Control + C**.

---

### ▶️ Running the app again next time

You don't need to redo all the setup steps. Each time you want to use the app, just run these 3 lines:

```bash
cd ~/Desktop/sap-codebase-chat
source venv/bin/activate
streamlit run app.py
```

---

### 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| `command not found: brew` | Redo Step 1 |
| `command not found: python3` | Redo Step 2 |
| `(venv)` not showing in prompt | Run `source venv/bin/activate` again |
| Browser doesn't open automatically | Manually go to **http://localhost:8501** |
| `ModuleNotFoundError` on run | Make sure `(venv)` is active, then redo Step 6 |
| Gemini API error | Double-check you pasted the full API key in the sidebar |

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     Streamlit UI (app.py)                  │
│  Sidebar: API key · Load project · Directory tree          │
│  Main:    Chat messages · Image upload · Chat input        │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│                  file_processor.py                         │
│  build_directory_tree()  – pretty ASCII tree              │
│  build_codebase_context() – reads ALL text files into one  │
│                             Markdown context string        │
│  get_file_type_summary()  – counts files by extension      │
└────────────┬───────────────────────────────────────────────┘
             │  context string (up to ~225 k tokens)
             ▼
┌────────────────────────────────────────────────────────────┐
│              Google Gemini 2.0 Flash API                   │
│  • 1 M token context window                                │
│  • Multimodal (text + images)                              │
│  • Stateful multi-turn chat                                │
└────────────────────────────────────────────────────────────┘
```

### Why no vector database?

SAP CPI projects are typically small enough to fit inside Gemini's
**1 million token** context window directly. Loading everything at once is
simpler *and* more accurate (no chunking artefacts, no retrieval misses).

For extremely large enterprise repositories you can add a RAG layer —
see [Contributing](#-contributing).

---

## 🚀 Quickstart (Windows / Advanced Users)

### Prerequisites

- Python 3.10 or newer
- A **Google Gemini API key** → [Get one free at Google AI Studio](https://aistudio.google.com/app/apikey)

### Install

```bash
git clone https://github.com/<your-org>/sap-codebase-chat.git
cd sap-codebase-chat

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Configure (optional)

```bash
cp .env.example .env
# Edit .env and paste your Gemini API key
```

You can also paste the key directly in the sidebar — no `.env` file needed.

### Run

```bash
streamlit run app.py
```

The app opens at **http://localhost:8501**.

---

## 📖 Usage

### Loading a project

**Option A – Upload ZIP**
1. Zip your SAP project folder.
2. In the sidebar choose *Upload ZIP File* and upload it.
3. Click **Load Project**.

**Option B – Local folder path**
1. In the sidebar choose *Local Folder Path*.
2. Paste the absolute path, e.g. `/Users/you/ESA_Exception_Handling`.
3. Click **Load Project**.

The sidebar will display the directory tree and file-type counts.

### Chatting

Type your question in the chat box. Examples:

```
"Give me a high-level summary of this SAP integration project."
"What does the Groovy script 'Custom Header' do exactly?"
"Explain the iFlow end-to-end: source → transformation → target."
"What retry mechanism is implemented and how does it work?"
"What parameters does this integration need at runtime?"
"Are there any potential issues or improvements you can spot?"
```

### Attaching images

Use the **📎 Attach an image** uploader above the chat box to include
a screenshot, error message, or flow diagram. Gemini will analyse it in
the context of your loaded codebase.

---

## 🗂️ Supported File Types

| Category | Extensions |
|---|---|
| SAP CPI | `.iflw`, `.prop`, `.propdef`, `.mf` |
| Scripting | `.groovy`, `.java`, `.js`, `.ts`, `.py`, `.sh` |
| Config | `.xml`, `.xsd`, `.wsdl`, `.xsl`, `.xslt`, `.json`, `.yaml`, `.yml`, `.toml`, `.properties` |
| Documentation | `.md`, `.txt`, `.rst` |
| Build | `.gradle`, `.pom`, `.project`, `.classpath` |
| Database | `.sql` |
| Web | `.html`, `.css` |
| Images (vision) | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg` |

---

## 📁 Project Structure

```
sap-codebase-chat/
├── app.py              # Streamlit UI + Gemini chat logic
├── file_processor.py   # Directory walker, file reader, context builder
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .gitignore
└── README.md
```

---

## 🔐 Security & Privacy

- Your source code is sent to **Google Gemini API** for analysis.
- The API key is stored only in your local `.env` or browser session (Streamlit).
- No data is stored by this application itself.
- Review [Google's data usage policy](https://ai.google.dev/terms) before loading sensitive/proprietary code.

---

## 🤝 Contributing

PRs are welcome! Some ideas for future enhancements:

- [ ] **RAG mode** — ChromaDB + Gemini embeddings for very large repos
- [ ] **File diff analysis** — compare two versions of an iFlow
- [ ] **Export chat** — download conversation as PDF/Markdown
- [ ] **iFlow visualiser** — render BPMN diagram from `.iflw` XML
- [ ] **Docker image** — one-command deployment

---

## 📄 License

MIT © 2024 — feel free to use, modify, and distribute.
