# Failure Analysis

Model: gpt-4o | Target: Flask | Cases: 17

## Results

Pass rate: 13/17 (76%)

| Category | Passed |
|----------|--------|
| tool_error | 3/3 |
| empty_results | 3/3 |
| no_tool_needed | 2/2 |
| unanswerable | 2/2 |
| misdirection | 2/2 |
| multi_hop | 1/3 |
| infinite_loop_bait | 0/2 |

## What failed and why

**mh-01, mh-02, il-02** — judge parse error. The judge returned JSON with special characters that broke parsing, so they were marked as failures automatically. The agent answers were actually correct.

**il-01** — real failure. Asked to "read every Python file", the agent did exactly that (12 files, 6 steps) instead of giving an overview. It followed the instruction literally rather than recognising it was impractical.

## Key takeaway

The agent breaks when it needs to decide *when to stop*, not *what to look for*. The exit condition is controlled by the model, not the code — so if the model picks a bad strategy, there's nothing in the loop to catch it.

