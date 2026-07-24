"""LLM-powered assistant that exposes fs_tools to Groq's Llama models via tool use.

Wires read_file, list_files, write_file, and search_in_file into a Groq
(OpenAI-compatible) tool-calling loop so natural-language queries (e.g.
"find resumes mentioning Python experience") resolve into the right
sequence of tool calls automatically.

Usage:
    python llm_file_assistant.py "Read all resumes in the resumes folder"
    python llm_file_assistant.py            # interactive chat mode
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import groq
from dotenv import load_dotenv
from groq import Groq

from fs_tools import list_files, read_file, search_in_file, write_file

load_dotenv()

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_TOOL_ITERATIONS = 20
TOOL_CALL_RETRY_ATTEMPTS = 3

SYSTEM_PROMPT = (
    "You are a file system assistant specialized in working with resume "
    "files. You have exactly four tools: list_files, read_file, "
    "search_in_file, and write_file. Resumes live in the 'resumes' "
    "directory unless the user specifies otherwise.\n\n"
    "Rules:\n"
    "1. ALWAYS call list_files first to discover the exact file names in a "
    "directory before calling read_file or search_in_file. Never guess, "
    "assume, or invent a file name -- only use file names that a tool "
    "result actually returned.\n"
    "2. When a query implies checking multiple files (e.g. 'find resumes "
    "mentioning X'), call list_files once, then call search_in_file or "
    "read_file on each file name from that result.\n"
    "3. Base every answer only on what the tools actually returned -- "
    "never state a file's content without having read or searched it.\n"
    "4. Use write_file only when the user explicitly asks to create or "
    "save a file.\n"
    "5. CRITICAL: Never call write_file in the same turn as read_file. "
    "Call read_file by itself first, wait for its actual content in the "
    "tool result, and only then -- in a later turn -- call write_file "
    "with a real summary you composed from that content. Never write "
    "placeholder text such as '[insert summary here]'."
)

# Maps tool name -> the real fs_tools function that executes it.
FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "write_file": write_file,
    "search_in_file": search_in_file,
}

# OpenAI-compatible JSON schema tool definitions Groq expects.
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a resume file (.pdf, .txt, or .docx) and return its text content and metadata.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the file to read."},
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory, optionally filtered by extension (e.g. '.pdf').",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Path to the directory to list."},
                    "extension": {
                        "type": "string",
                        "description": "Optional extension filter, e.g. '.pdf'. Omit to list all files.",
                    },
                },
                "required": ["directory"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text content to a file, creating parent directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Destination path for the file."},
                    "content": {"type": "string", "description": "Text content to write."},
                },
                "required": ["filepath", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_file",
            "description": "Search for a keyword in a file's content (case-insensitive) and return matches with context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the file to search."},
                    "keyword": {"type": "string", "description": "Keyword or phrase to search for."},
                },
                "required": ["filepath", "keyword"],
            },
        },
    },
]


def _execute_tool_call(tool_call) -> dict:
    """Run the fs_tools function a tool_call refers to and return a JSON-safe result."""
    function = FUNCTIONS.get(tool_call.function.name)
    if function is None:
        return {"error": f"Unknown tool: {tool_call.function.name}"}
    try:
        arguments = json.loads(tool_call.function.arguments)
        return function(**arguments)
    except Exception as exc:  # malformed arguments or an unexpected tool failure
        return {"error": str(exc)}


def _create_completion(client: Groq, messages: list):
    """Call the Groq API, retrying automatically when the model emits a malformed
    tool-call (a known intermittent quirk of some Llama models on Groq) rather than
    a properly structured one."""
    last_error = None
    for _ in range(TOOL_CALL_RETRY_ATTEMPTS):
        try:
            return client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
            )
        except groq.BadRequestError as exc:
            if "tool_use_failed" not in str(exc):
                raise
            last_error = exc
    raise last_error


def run_conversation(client: Groq, messages: list) -> str:
    """Loop tool calls until the model returns a final text answer, mutating messages in place."""
    for _ in range(MAX_TOOL_ITERATIONS):
        completion = _create_completion(client, messages)
        message = completion.choices[0].message

        if not message.tool_calls:
            messages.append({"role": "assistant", "content": message.content})
            return message.content or "(no text response)"

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [tc.model_dump() for tc in message.tool_calls],
            }
        )
        for tool_call in message.tool_calls:
            result = _execute_tool_call(tool_call)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                }
            )

    return f"Stopped after {MAX_TOOL_ITERATIONS} tool-calling iterations without a final answer."


def ask(client: Groq, messages: list) -> str:
    """Run one turn through the tool-calling loop, translating API errors into readable messages."""
    try:
        return run_conversation(client, messages)
    except groq.AuthenticationError:
        return "Authentication failed. Check that GROQ_API_KEY in your .env file is set to a valid key."
    except groq.RateLimitError:
        return "Rate limited by the Groq API. Please wait a moment and try again."
    except groq.APIConnectionError:
        return "Could not connect to the Groq API. Check your internet connection."
    except groq.APIStatusError as exc:
        return f"Groq API error ({exc.status_code}): {exc.message}"


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM-powered file system assistant")
    parser.add_argument(
        "query",
        nargs="?",
        help="One-off natural language query. Omit to start an interactive chat.",
    )
    args = parser.parse_args()

    if not os.environ.get("GROQ_API_KEY"):
        print(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your "
            "free Groq API key from https://console.groq.com/keys, then try again.",
            file=sys.stderr,
        )
        sys.exit(1)

    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    if args.query:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": args.query},
        ]
        print(ask(client, messages))
        return

    print("LLM File System Assistant. Type 'exit' or 'quit' to leave.\n")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    while True:
        try:
            query = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not query:
            continue
        if query.lower() in {"exit", "quit"}:
            break
        messages.append({"role": "user", "content": query})
        print(f"\nAssistant: {ask(client, messages)}\n")


if __name__ == "__main__":
    main()
