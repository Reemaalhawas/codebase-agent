# codebase-agent

An AI agent that answers questions about a codebase it has never seen, plus an adversarial eval harness that tests where it breaks.

## What it does

The agent gets a question, navigates the repo with three tools (list directory, read file, search), and answers with citations to specific files and line numbers.

The eval harness runs 17 adversarial test cases across categories like missing files, empty search results, false premises, and questions designed to cause infinite tool loops. A second GPT-4o call judges each answer pass or fail.


Target repo: Flask.

## Setup

```bash
uv sync
export OPENAI_API_KEY="sk-..."
```

## Usage

Ask questions interactively:
```bash
python main.py interactive
```

Run the eval suite:
```bash
python main.py eval
```

Run specific cases:
```bash
python main.py eval --cases te-01 mh-02
```

## Results

13/17 passing (76%). See `FAILURE_ANALYSIS.md`.
