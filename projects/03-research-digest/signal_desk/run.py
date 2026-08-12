from __future__ import annotations

import argparse
import json

from .pipeline import run_once


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a personalized literature, news & fund-research digest (free sources)."
    )
    parser.add_argument("--once", action="store_true", help="Run one review and write artifacts")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip live ArXiv/RSS/Finnhub; use local JSONL + inbox only",
    )
    parser.add_argument(
        "--focus",
        default="",
        help="Domain / keywords that steer ArXiv queries and ranking (e.g. 'realized volatility, GARCH')",
    )
    args = parser.parse_args()
    if args.once:
        review = run_once(live=not args.offline, focus_query=args.focus)
        print(
            json.dumps(
                {
                    "ok": True,
                    "kind": "personal-review",
                    "delivery": "local-only",
                    "date": review["date"],
                    "mode": review.get("mode"),
                    "focus": review.get("focus_query"),
                    "dropped": review["stats"]["claims_dropped"],
                    "topics": review["matched_topics"],
                    "stats": {
                        "literature": review["stats"].get("literature_items"),
                        "news": review["stats"].get("news_items"),
                        "fund_research": review["stats"].get("fund_research_items"),
                        "sources_local": review["stats"].get("sources_local"),
                    },
                }
            )
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
