#!/usr/bin/env python3
"""Build data/daily-champs.json from Devil's Lair finished Daily team matches.

Scoring: 1 point per win, 0.5 per draw, 0 per loss. The leaderboard
aggregates the most recent completed Daily team matches returned by the
Chess.com PubAPI. Players listed as fair-play removals are excluded.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

CLUB = "devils-lair"
API = "https://api.chess.com/pub"
MATCH_LIMIT = 10
USER_AGENT = "DevilsLairSidebar/2.0 (Chess.com club: devils-lair)"
OUT = Path("data/daily-champs.json")

DRAW_RESULTS = {
    "agreed", "repetition", "stalemate", "insufficient", "50move",
    "timevsinsufficient", "draw", "drawn",
}


def get_json(url: str, retries: int = 3):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.load(resp)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))


def points_for(result: str | None) -> float:
    r = (result or "").strip().lower()
    if r == "win":
        return 1.0
    if r in DRAW_RESULTS:
        return 0.5
    return 0.0


def match_api_url(item: dict) -> str | None:
    api_id = item.get("@id")
    if isinstance(api_id, str) and "/pub/match/" in api_id and "/live/" not in api_id:
        return api_id
    for value in (item.get("url"), item.get("@id")):
        if not isinstance(value, str):
            continue
        m = re.search(r"/matches/(?:daily/)?(\d+)(?:/|$)", value)
        if not m:
            m = re.search(r"/pub/match/(\d+)(?:/|$)", value)
        if m:
            return f"{API}/match/{m.group(1)}"
    return None


def is_our_team(team: dict) -> bool:
    values = " ".join(str(team.get(k, "")) for k in ("@id", "url", "name")).lower()
    return f"/club/{CLUB}" in values or values.strip() == CLUB or "devil's lair" in values or "devils lair" in values


def normalize_finished(items: list[dict]) -> list[dict]:
    def key(x: dict):
        # Finished-list entries vary by API version. The profile fetch later
        # gives authoritative end_time; this ordering is only a first pass.
        return int(x.get("end_time") or x.get("start_time") or 0)
    return sorted(items, key=key, reverse=True)


def main():
    club_matches = get_json(f"{API}/club/{CLUB}/matches")
    finished = normalize_finished(club_matches.get("finished", []))

    aggregates: dict[str, dict] = {}
    used_matches = []

    # Inspect a few extras in case some old/removed entry cannot be resolved.
    for entry in finished[: max(MATCH_LIMIT * 2, MATCH_LIMIT)]:
        if len(used_matches) >= MATCH_LIMIT:
            break
        api_url = match_api_url(entry)
        if not api_url:
            continue
        try:
            match = get_json(api_url)
        except Exception as exc:
            print(f"Skipping {api_url}: {exc}")
            continue
        time.sleep(0.2)

        if str(match.get("status", "")).lower() != "finished":
            continue
        settings = match.get("settings") or {}
        if str(settings.get("time_class", "daily")).lower() != "daily":
            continue

        teams = match.get("teams") or {}
        our_team = None
        for team in teams.values():
            if isinstance(team, dict) and is_our_team(team):
                our_team = team
                break
        if not our_team:
            continue

        removed = {str(u).lower() for u in (our_team.get("fair_play_removals") or [])}
        players = our_team.get("players") or []
        if not players:
            continue

        used_matches.append({
            "name": match.get("name") or entry.get("name") or "Daily team match",
            "url": match.get("url") or entry.get("url") or "",
            "end_time": match.get("end_time"),
        })

        for p in players:
            username = str(p.get("username") or "").strip()
            if not username or username.lower() in removed:
                continue
            white_result = p.get("played_as_white")
            black_result = p.get("played_as_black")
            results = [r for r in (white_result, black_result) if r]
            if not results:
                continue

            row = aggregates.setdefault(username, {
                "username": username,
                "points": 0.0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "games": 0,
                "matches": 0,
            })
            row["matches"] += 1
            for result in results:
                pts = points_for(result)
                row["points"] += pts
                row["games"] += 1
                if pts == 1:
                    row["wins"] += 1
                elif pts == 0.5:
                    row["draws"] += 1
                else:
                    row["losses"] += 1

    leaders = sorted(
        aggregates.values(),
        key=lambda x: (x["points"], x["wins"], x["games"], x["username"].lower()),
        reverse=True,
    )[:3]

    for p in leaders:
        if float(p["points"]).is_integer():
            p["points"] = int(p["points"])

    payload = {
        "updated": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "method": "Top individual point scorers across the 10 most recent completed Devil's Lair Daily team matches. Win=1, draw=0.5, loss=0.",
        "matches_counted": len(used_matches),
        "players": leaders,
        "source_matches": used_matches,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} with {len(leaders)} leaders from {len(used_matches)} matches")


if __name__ == "__main__":
    main()
