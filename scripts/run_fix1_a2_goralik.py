#!/usr/bin/env python3
"""Live FIX-1 acceptance: mine narrow ClaimCards from Goralik source_map."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from edit.a2_claim_miner import mine_claims
from edit.llm import get_chat_model
from models import SourceMap

load_dotenv()

SOURCE_MAP = ROOT / "runs/goralik-mimimi/source_map_semantic.json"
OUT = ROOT / "runs/goralik-mimimi/fix1_a2_narrow.json"

THEMES = (
    "stock",
    "щен",
    "повод",
    "педоморф",
    "каваи",
    "исчисля",
    "счётност",
    "счетност",
    "кот",
    "хрупк",
    "таймер",
    "конфет",
    "пирож",
    "домой",
)


def main() -> int:
    sm = SourceMap.model_validate_json(SOURCE_MAP.read_text(encoding="utf-8"))
    llm = get_chat_model(temperature=0.0, model="gpt-5-2")
    claims = mine_claims(sm, llm=llm)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "n": len(claims),
        "claims": [c.model_dump(mode="json") for c in claims],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"n={len(claims)}")
    for c in claims:
        print("---")
        print("id:", c.claim_id)
        print("claim:", c.claim)
        print("anchor:", c.object_anchor)
        print("A/B:", c.contrast_pair.state_a, "/", c.contrast_pair.state_b)
        print("mech:", c.mechanism_term, "—", c.mechanism_explain)
        print("kind:", c.kind.value, "conf:", c.confidence)

    blob = " ".join(
        " ".join(
            [
                c.claim,
                c.object_anchor,
                c.mechanism_term,
                c.contrast_pair.state_a,
                c.contrast_pair.state_b,
            ]
        )
        for c in claims
    ).lower()
    hits = [t for t in THEMES if t in blob]
    print("theme_hits:", hits)

    anchors = [c.object_anchor.strip().lower() for c in claims]
    print("unique_anchors:", len(set(anchors)), "/", len(anchors))

    source_excerpt = "\n\n".join(s.text for s in sm.segments)[:6000]
    judge = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You check whether each claim is grounded in the source essay. "
                    "Reply JSON only: {\"ok\": bool, \"notes\": [str]}."
                )
            ),
            HumanMessage(
                content=(
                    "SOURCE (excerpt):\n"
                    + source_excerpt
                    + "\n\nCLAIMS:\n"
                    + json.dumps([c.claim for c in claims], ensure_ascii=False, indent=2)
                )
            ),
        ]
    )
    print("judge:", getattr(judge, "content", judge))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
