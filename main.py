import argparse
import os

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "target_repo")


def interactive():
    from agent import Agent
    agent = Agent(repo=REPO)
    print(f"repo: {REPO}")
    print("ask something, empty line to quit\n")
    while True:
        try:
            q = input("Q: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not q:
            break
        r = agent.run(q)
        print(f"\n{r.answer}")
        print(f"\n[{r.steps} steps, {len(r.tool_calls)} tool calls]")
        if r.hit_cap:
            print("[hit step cap]")
        print()


def run_eval(args):
    from eval import run_eval, print_report, CASES
    cases = CASES
    if args.cases:
        ids = set(args.cases)
        cases = [c for c in CASES if c.id in ids]
    results = run_eval(REPO, cases)
    print_report(results)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("interactive")
    ep = sub.add_parser("eval")
    ep.add_argument("--cases", nargs="+")
    args = p.parse_args()
    if args.cmd == "interactive":
        interactive()
    elif args.cmd == "eval":
        run_eval(args)


if __name__ == "__main__":
    main()
