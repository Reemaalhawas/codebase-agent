from dataclasses import dataclass, field
import anthropic
from tools import list_directory, read_file, grep_search

TOOLS = [
    {
        "name": "list_directory",
        "description": "List files and folders at a path in the repo. Use '.' for root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "relative path inside the repo"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a file in the repo. Returns up to 300 lines.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "relative path to the file"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "grep_search",
        "description": "Search for a pattern across repo files. Returns matching lines with file:line.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "text or regex to search for"},
                "path": {"type": "string", "description": "directory or file to search in, default '.'"},
            },
            "required": ["pattern"],
        },
    },
]

SYSTEM = """You are a code assistant. You have tools to explore a repository.

- Use tools to find evidence before answering. Don't guess at code details.
- Cite file paths and line numbers when you reference code.
- If something doesn't exist in the repo, say so. Don't invent it.
- If the question can't be answered from static code, say so.
- Stop searching once you have enough to answer.
"""


@dataclass
class ToolCall:
    name: str
    input: dict
    result: str


@dataclass
class AgentResult:
    answer: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    steps: int = 0
    hit_cap: bool = False


class Agent:
    def __init__(self, repo: str, max_steps: int = 15):
        self.repo = repo
        self.max_steps = max_steps
        self.client = anthropic.Anthropic()

    def run(self, question: str) -> AgentResult:
        messages = [{"role": "user", "content": question}]
        tool_calls = []
        answer = ""
        steps = 0

        while steps < self.max_steps:
            resp = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM,
                tools=TOOLS,
                messages=messages,
            )
            steps += 1

            for block in resp.content:
                if hasattr(block, "text"):
                    answer = block.text

            messages.append({"role": "assistant", "content": resp.content})

            if resp.stop_reason == "end_turn":
                break

            if resp.stop_reason == "tool_use":
                results = []
                for block in resp.content:
                    if block.type != "tool_use":
                        continue
                    out = self._run_tool(block.name, block.input)
                    tool_calls.append(ToolCall(block.name, dict(block.input), out))
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": out})
                messages.append({"role": "user", "content": results})
            else:
                break

        hit_cap = steps >= self.max_steps and resp.stop_reason == "tool_use"
        return AgentResult(answer=answer, tool_calls=tool_calls, steps=steps, hit_cap=hit_cap)

    def _run_tool(self, name: str, inputs: dict) -> str:
        if name == "list_directory":
            return list_directory(self.repo, inputs.get("path", "."))
        if name == "read_file":
            return read_file(self.repo, inputs.get("path", ""))
        if name == "grep_search":
            return grep_search(self.repo, inputs.get("pattern", ""), inputs.get("path", "."))
        return f"unknown tool: {name}"
