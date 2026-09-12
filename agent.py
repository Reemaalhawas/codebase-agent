import json
from dataclasses import dataclass, field
import openai
from tools import list_directory, read_file, grep_search

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and folders at a path in the repo. Use '.' for root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "relative path inside the repo"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file in the repo. Returns up to 300 lines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "relative path to the file"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_search",
            "description": "Search for a pattern across repo files. Returns matching lines with file:line.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "text or regex to search for"},
                    "path": {"type": "string", "description": "directory or file to search in, default '.'"},
                },
                "required": ["pattern"],
            },
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
        self.client = openai.OpenAI()

    def run(self, question: str) -> AgentResult:
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": question},
        ]
        tool_calls = []
        answer = ""
        steps = 0
        finish_reason = ""

        while steps < self.max_steps:
            resp = self.client.chat.completions.create(
                model="gpt-4o",
                tools=TOOLS,
                messages=messages,
            )
            steps += 1
            msg = resp.choices[0].message
            finish_reason = resp.choices[0].finish_reason

            if msg.content:
                answer = msg.content

            messages.append(msg)

            if finish_reason == "stop":
                break

            if finish_reason == "tool_calls":
                for tc in msg.tool_calls:
                    args = json.loads(tc.function.arguments)
                    out = self._run_tool(tc.function.name, args)
                    tool_calls.append(ToolCall(tc.function.name, args, out))
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": out,
                    })
            else:
                break

        hit_cap = steps >= self.max_steps and finish_reason == "tool_calls"
        return AgentResult(answer=answer, tool_calls=tool_calls, steps=steps, hit_cap=hit_cap)

    def _run_tool(self, name: str, inputs: dict) -> str:
        if name == "list_directory":
            return list_directory(self.repo, inputs.get("path", "."))
        if name == "read_file":
            return read_file(self.repo, inputs.get("path", ""))
        if name == "grep_search":
            return grep_search(self.repo, inputs.get("pattern", ""), inputs.get("path", "."))
        return f"unknown tool: {name}"
