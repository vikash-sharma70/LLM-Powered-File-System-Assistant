# LLM-Powered File System Assistant

An AI assistant that reads, lists, writes, and searches resume files
(`.pdf`, `.txt`, `.docx`) using LLM function calling / tool use.

- **Part A** (`fs_tools.py`) — plain Python file-system tools. ✅ Done.
- **Part B** (`llm_file_assistant.py`) — Claude tool-calling integration over those tools. ✅ Done.

## Project Structure

```
.
├── fs_tools.py                  # Part A: read_file, list_files, write_file, search_in_file
├── llm_file_assistant.py        # Part B: Claude tool-calling loop over fs_tools
├── requirements.txt
├── .env.example                 # copy to .env and fill in your Anthropic API key (Part B only)
├── resumes/                     # 10 sample dummy resumes (generated)
├── output/                      # generated summary files land here
├── scripts/
│   ├── generate_sample_data.py  # creates the 10 sample resumes
│   └── demo_part_a.py           # visual demo of all 4 tools, no LLM needed
└── tests/
    └── test_fs_tools.py         # pytest suite for fs_tools.py
```

## Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Environment variables (only needed for Part B):
   ```bash
   cp .env.example .env
   ```
   Open `.env` and set `ANTHROPIC_API_KEY` to your Anthropic API key
   (get one at https://console.anthropic.com/settings/keys — your
   workspace needs available credits/billing set up).
   **Part A does not require any API key.**

## Part A: File System Tools

`fs_tools.py` exposes four functions:

| Function | Purpose |
|---|---|
| `read_file(filepath)` | Reads a `.pdf` / `.txt` / `.docx` file, returns `{success, filepath, filename, extension, content, metadata, error}` |
| `list_files(directory, extension=None)` | Lists files in a directory, optionally filtered by extension, with size/modified metadata |
| `write_file(filepath, content)` | Writes text to a file, auto-creating parent directories, returns `{success, filepath, bytes_written, error}` |
| `search_in_file(filepath, keyword)` | Case-insensitive keyword search with surrounding context, returns match list with line numbers |

### 1. Generate sample resumes

```bash
python scripts/generate_sample_data.py
```

Creates 10 dummy resumes in `resumes/` — 4 `.txt`, 3 `.docx`, 3 `.pdf` —
across different roles (Python/Django, Java, Data Science, React,
DevOps, .NET, etc.) so both format-parsing and keyword search have
realistic, varied data to work against.

### 2. Run the automated test suite

```bash
pytest -v
```

19 tests covering all 4 tools, including edge cases: missing files,
unsupported extensions, empty/nonexistent directories, nested directory
creation, empty search keywords, and case-insensitive matching.

### 3. Run the visual demo (no API key needed)

```bash
python scripts/demo_part_a.py
```

Prints real output for every tool: listing all resumes, filtering by
`.pdf`, reading one file of each format, a graceful error for a missing
file, searching for "Python" across every resume, and writing a summary
file to `output/`.

### 4. Try it yourself interactively

```bash
python
>>> from fs_tools import read_file, list_files, write_file, search_in_file
>>> list_files("resumes", extension=".pdf")
>>> read_file("resumes/resume_aditi_sharma.txt")
>>> search_in_file("resumes/resume_priya_nair.txt", "python")
>>> write_file("output/test.txt", "hello world")
```

## Part B: LLM Integration

`llm_file_assistant.py` wires the four Part A tools into an Anthropic
Claude tool-calling loop (via the SDK's `@beta_tool` decorator +
`client.beta.messages.tool_runner`). Claude decides which tool(s) to call
based on the natural-language query, the tools execute locally against
`fs_tools.py`, and Claude turns the results into a final answer — looping
automatically until it has enough information to respond.

Model used: `claude-opus-4-8`.

### Run a one-off query

```bash
python llm_file_assistant.py "Read all resumes in the resumes folder"
python llm_file_assistant.py "Find resumes mentioning Python experience"
python llm_file_assistant.py "Create a summary file for resume_aditi_sharma.txt"
```

### Interactive chat mode

```bash
python llm_file_assistant.py
```

Type a query, get a response, keep chatting. Type `exit` or `quit` to leave.

### How it works

1. Each tool (`read_file_tool`, `list_files_tool`, `write_file_tool`,
   `search_in_file_tool`) is a thin `@beta_tool`-decorated wrapper around
   the matching `fs_tools.py` function — the decorator generates the JSON
   tool schema from the Python type hints and docstring automatically.
2. `ask()` starts a `tool_runner` with those 4 tools and the user's query.
3. The runner loops: Claude requests a tool call → the wrapper runs the
   real `fs_tools` function → the result goes back to Claude → repeat until
   Claude has a final text answer (capped at `MAX_TOOL_ITERATIONS = 20` to
   avoid runaway loops, e.g. for "read all 10 resumes" queries).
4. Network/auth/rate-limit/billing errors are caught and reported as a
   clear message instead of a stack trace.

## Running Tests

```bash
pytest -v
```
