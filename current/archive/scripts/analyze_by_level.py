#!/usr/bin/env python3
"""分析 ds-v4-flash 在 Easy/Hard 不同约束数量下的表现"""
import json
from collections import defaultdict

def main():
    with open("constraint_assignments.json") as f:
        assignments = json.load(f)

    level_map = {a["case_id"]: a["level"] for a in assignments}
    nif_map = {a["case_id"]: a["n_if"] for a in assignments}

    with open("output/scores_ds-v4-flash.json") as f:
        data = json.load(f)

    scores = data["scores"]
    tier_scores = data["tier_scores"]

    print(f"Overall: {tier_scores['overall']:.1%}")
    print(f"T1: {tier_scores['T1']:.1%}  T2: {tier_scores['T2']:.1%}  T3: {tier_scores['T3']:.1%}")

    # By level
    level_scores = defaultdict(list)
    for cid, s in scores.items():
        level = level_map.get(cid, "?")
        level_scores[level].append(s["score"])

    print(f"\n{'='*50}")
    print(f"{'Level':<8} {'Cases':>6} {'Avg Score':>10} {'Min':>8} {'Max':>8}")
    print("-" * 50)
    for level in ["Easy", "Hard"]:
        vals = level_scores[level]
        if vals:
            print(f"{level:<8} {len(vals):>6} {sum(vals)/len(vals):>10.1%} {min(vals):>8.1%} {max(vals):>8.1%}")

    # By n_if
    nif_scores = defaultdict(list)
    for cid, s in scores.items():
        n = nif_map.get(cid, 0)
        nif_scores[n].append(s["score"])

    print(f"\n{'='*50}")
    print(f"{'N_IF':>5} {'Cases':>6} {'Avg Score':>10} {'Min':>8} {'Max':>8}")
    print("-" * 50)
    for n in sorted(nif_scores.keys()):
        vals = nif_scores[n]
        print(f"{n:>5} {len(vals):>6} {sum(vals)/len(vals):>10.1%} {min(vals):>8.1%} {max(vals):>8.1%}")

    # By n_if: hard vs soft breakdown
    print(f"\n{'='*60}")
    print(f"{'N_IF':>5} {'Hard Pass%':>12} {'Soft Pass%':>12} {'IF Score':>12}")
    print("-" * 60)
    for n in sorted(nif_scores.keys()):
        cases_at_n = [cid for cid, ni in nif_map.items() if ni == n]
        h_pass = sum(scores[c]["hard"]["passed"] for c in cases_at_n if c in scores)
        h_total = sum(scores[c]["hard"]["total"] for c in cases_at_n if c in scores)
        s_pass = sum(scores[c]["soft"]["passed"] for c in cases_at_n if c in scores)
        s_total = sum(scores[c]["soft"]["total"] for c in cases_at_n if c in scores)
        avg_score = sum(scores[c]["score"] for c in cases_at_n if c in scores) / len(cases_at_n) if cases_at_n else 0
        print(f"{n:>5} {h_pass}/{h_total:>3} ({h_pass/h_total:.1%}) {s_pass}/{s_total:>3} ({s_pass/s_total:.1%}) {avg_score:>10.1%}")

    # IF-only analysis (only IF constraints)
    print(f"\n{'='*60}")
    print("IF-only analysis (excluding non-IF constraints):")
    with open("eval_config_all.json") as f:
        all_constraints = json.load(f)["constraints"]

    results = data["results"]
    nif_if_scores = defaultdict(list)
    for cid in scores:
        n = nif_map.get(cid, 0)
        if_pass = 0
        if_total = 0
        for key, result in results.get(cid, {}).items():
            ckey = key
            cfg = all_constraints.get(ckey, {})
            if cfg.get("is_if", False):
                if_total += 1
                if result.get("pass") is True:
                    if_pass += 1
        if if_total > 0:
            nif_if_scores[n].append(if_pass / if_total)

    print(f"{'N_IF':>5} {'Cases':>6} {'IF Compliance':>14}")
    print("-" * 30)
    for n in sorted(nif_if_scores.keys()):
        vals = nif_if_scores[n]
        print(f"{n:>5} {len(vals):>6} {sum(vals)/len(vals):>14.1%}")

    # Worst cases
    print(f"\n{'='*50}")
    print("Bottom 10 cases:")
    sorted_cases = sorted(scores.items(), key=lambda x: x[1]["score"])
    for cid, s in sorted_cases[:10]:
        level = level_map.get(cid, "?")
        n = nif_map.get(cid, 0)
        print(f"  {cid}: {s['score']:.1%} (n_if={n}, {level}, hard={s['hard']['passed']}/{s['hard']['total']}, soft={s['soft']['passed']}/{s['soft']['total']})")


if __name__ == "__main__":
    main()
