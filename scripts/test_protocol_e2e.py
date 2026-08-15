"""End-to-end protocol exercise against a running WindowVerse backend.

Start the backend first (python server.py), then run this script.
"""
import asyncio, json, sys
import websockets

URL = "ws://localhost:8765"
fails = []

def check(cond, label):
    print(("OK:   " if cond else "FAIL: ") + label)
    if not cond:
        fails.append(label)

async def collect(ws, seconds=1.2):
    out = []
    try:
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=seconds)
            out.append(json.loads(raw))
    except asyncio.TimeoutError:
        pass
    return out

def types(msgs):
    return [m["type"] for m in msgs]

def first(msgs, t):
    return next((m for m in msgs if m["type"] == t), None)

async def main():
    async with websockets.connect(URL, max_size=None) as ws:
        boot = await collect(ws, 3)
        check(first(boot, "nav_state") is not None, "boot sends nav_state")

        await ws.send(json.dumps({"action": "get_bible_structure", "testament": "all"}))
        m = first(await collect(ws), "bible_structure")
        check(m and len(m["books"]) == 66, f"bible_structure returns 66 books ({len(m['books']) if m else 0})")
        john = next((b for b in m["books"] if b["book"] == "John"), None)
        check(john and john["chapters"] == 21 and john["testament"] == "NT", "John: 21 chapters, NT")
        # Book numbers come from the loaded database, which may use its own
        # numbering scheme, so never hardcode them here.
        num = {b["book"]: b["book_number"] for b in m["books"]}

        await ws.send(json.dumps({"action": "get_chapter", "book_number": num["Mark"], "chapter": 16}))
        m = first(await collect(ws), "chapter_verses")
        vs = [v["verse"] for v in m["verses"]]
        check(m["book"] == "Mark" and m["chapter"] == 16, "get_chapter Mark 16")
        check(
            vs == sorted(set(vs)) and all((v.get("text") or "").strip() for v in m["verses"]),
            "chapter verses are the database's own, in order, none faked",
        )
        check(m["chapters"] == list(range(1, 17)), "Mark chapter list 1..16")

        # lookup_reference stages preview only
        await ws.send(json.dumps({"action": "lookup_reference", "book": "MAT", "chapter": 5, "verse": 3}))
        msgs = await collect(ws)
        pv = first(msgs, "preview_verse")
        check(pv and pv["book"] == "Matthew" and pv["verse"] == 3, "abbreviation 'MAT' resolves to Matthew 5:3")
        check(first(msgs, "broadcast_verse") is None, "lookup previews, does NOT broadcast")
        ns = first(msgs, "nav_state")
        check(ns and ns["reference"]["book"] == "Matthew" and ns["on_air"] is False, "nav_state tracks preview, off air")

        # navigate from preview stays in preview
        await ws.send(json.dumps({"action": "navigate_verse", "direction": 1}))
        msgs = await collect(ws)
        pv = first(msgs, "preview_verse")
        check(pv and (pv["chapter"], pv["verse"]) == (5, 4), "next verse -> Matthew 5:4 (preview)")
        check(first(msgs, "broadcast_verse") is None, "navigation with preview does not go on air")

        # broadcast
        await ws.send(json.dumps({"action": "broadcast_verse"}))
        msgs = await collect(ws)
        bv = first(msgs, "broadcast_verse")
        check(bv and (bv["book"], bv["chapter"], bv["verse"]) == ("Matthew", 5, 4), "broadcast_verse puts preview on air")
        ns = first(msgs, "nav_state")
        check(ns and ns["on_air"] is True and ns["preview"] is None, "on air, preview consumed")

        # typed reference search: no semantic index needed
        await ws.send(json.dumps({"action": "search_verse", "query": "John 3:16"}))
        msgs = await collect(ws)
        sr = first(msgs, "search_results")
        check(sr and len(sr["results"]) == 1 and sr["results"][0]["book"] == "John", "typed reference search -> single hit")
        check(first(msgs, "preview_verse") is not None, "reference search stages preview")
        check(first(msgs, "broadcast_verse") is None, "search never auto-broadcasts")

        # whole chapter reference
        await ws.send(json.dumps({"action": "get_chapter", "book_number": num["Psalms"], "chapter": 23}))
        ps23 = first(await collect(ws), "chapter_verses")
        await ws.send(json.dumps({"action": "search_verse", "query": "Psalm 23"}))
        sr = first(await collect(ws), "search_results")
        check(
            sr and ps23 and len(sr["results"]) == len(ps23["verses"]),
            f"'Psalm 23' returns the whole chapter ({len(sr['results']) if sr else 0})",
        )

        # browser handoff
        await ws.send(json.dumps({"action": "load_search_results", "query": "1 Corinthians 13"}))
        br = first(await collect(ws), "browser_results")
        check(br and len(br["results"]) == 13, "browser handoff loads 1 Cor 13 (13 verses)")

        # chapter boundary crossing
        await ws.send(json.dumps({"action": "lookup_reference", "book": "John", "chapter": 3, "verse": 36}))
        await collect(ws)
        await ws.send(json.dumps({"action": "navigate_verse", "direction": 1}))
        pv = first(await collect(ws), "preview_verse")
        check(pv and (pv["chapter"], pv["verse"]) == (4, 1), "chapter boundary: John 3:36 -> 4:1")

        # book boundary: step off the very last verse of the Old Testament
        await ws.send(json.dumps({"action": "get_chapter", "book_number": num["Malachi"], "chapter": 4}))
        mal = first(await collect(ws), "chapter_verses")
        last_mal = max(v["verse"] for v in mal["verses"])
        await ws.send(json.dumps({"action": "lookup_reference", "book": "Malachi", "chapter": 4, "verse": last_mal}))
        await collect(ws)
        await ws.send(json.dumps({"action": "navigate_verse", "direction": 1}))
        pv = first(await collect(ws), "preview_verse")
        check(pv and pv["book"] == "Matthew" and (pv["chapter"], pv["verse"]) == (1, 1), "book boundary: Malachi -> Matthew 1:1")

        # canon end
        await ws.send(json.dumps({"action": "lookup_reference", "book": "Revelation", "chapter": 22, "verse": 21}))
        await collect(ws)
        await ws.send(json.dumps({"action": "navigate_verse", "direction": 1}))
        msgs = await collect(ws)
        check(first(msgs, "preview_verse") is None, "navigation stops at Revelation 22:21")

        # clear preview / broadcast
        await ws.send(json.dumps({"action": "clear_preview"}))
        check(first(await collect(ws), "preview_cleared") is not None, "clear_preview acknowledged")
        await ws.send(json.dumps({"action": "clear_broadcast"}))
        msgs = await collect(ws)
        bs = first(msgs, "broadcast_state")
        check(bs is not None and bs.get("on_air") is False, "clear_broadcast takes it off air")

        # voice settings round-trip + persistence echo
        await ws.send(json.dumps({"action": "set_voice_nav", "voice_nav_enabled": True,
                                  "transcript_auto_broadcast": False}))
        ds = first(await collect(ws), "detection_state")
        check(ds and ds["settings"]["voice_nav_enabled"] is True
              and ds["settings"]["transcript_auto_broadcast"] is False, "voice settings saved + echoed")
        await ws.send(json.dumps({"action": "set_voice_nav", "voice_nav_enabled": False,
                                  "transcript_auto_broadcast": True}))
        await collect(ws)

        # ── UI-staged preview (a click in Search / Scripture Browser) ──
        await ws.send(json.dumps({"action": "get_chapter", "book_number": 430, "chapter": 3}))
        chap = first(await collect(ws), "chapter_verses")
        row = next(v for v in chap["verses"] if v["verse"] == 16)

        await ws.send(json.dumps({"action": "stage_preview", "verse": row}))
        msgs = await collect(ws)
        pv = first(msgs, "preview_verse")
        check(pv and (pv["book"], pv["chapter"], pv["verse"]) == ("John", 3, 16),
              "stage_preview mirrors a browser click into server preview")
        ns = first(msgs, "nav_state")
        check(ns and ns["preview"] and ns["preview"]["verse"] == 16,
              "nav_state carries the staged preview instead of clearing it")

        # Broadcast with no payload: the server must use its own preview
        await ws.send(json.dumps({"action": "broadcast_verse"}))
        msgs = await collect(ws)
        bv = first(msgs, "broadcast_verse")
        check(bv and (bv["book"], bv["chapter"], bv["verse"]) == ("John", 3, 16),
              "Broadcast sends the staged verse on air")
        ns = first(msgs, "nav_state")
        check(ns and ns["on_air"] is True, "nav_state reports ON AIR after broadcast")

        # Voice next/back operate on whatever is on air, not just preview
        await ws.send(json.dumps({"action": "navigate_verse", "direction": 1,
                                  "broadcast": True}))
        bv = first(await collect(ws), "broadcast_verse")
        check(bv and (bv["chapter"], bv["verse"]) == (3, 17),
              "voice 'next' from on-air verse -> John 3:17 on air")

        await ws.send(json.dumps({"action": "navigate_verse", "direction": -1,
                                  "broadcast": True}))
        bv = first(await collect(ws), "broadcast_verse")
        check(bv and (bv["chapter"], bv["verse"]) == (3, 16),
              "voice 'back' from on-air verse -> John 3:16 on air")

        await ws.send(json.dumps({"action": "clear_broadcast"}))
        await collect(ws)

        # ── Book tiles need a short label for the Scripture Browser grid ──
        await ws.send(json.dumps({"action": "get_bible_structure", "testament": "all"}))
        struct = first(await collect(ws), "bible_structure")
        books = {b["book"]: b for b in (struct or {}).get("books", [])}
        check(books.get("Genesis", {}).get("abbrev") == "Gen"
              and books.get("1 Samuel", {}).get("abbrev", "").startswith("1 "),
              "book structure carries abbreviations for the box grid")

        # ── Voice keyword editor round-trip ──
        await ws.send(json.dumps({"action": "get_voice_keywords"}))
        kw = first(await collect(ws), "voice_keywords")
        by_intent = {g["intent"]: g for g in (kw or {}).get("intents", [])}
        check("continue" in [e["phrase"] for e in by_intent.get("next", {}).get("builtin", [])]
              and "back" in [e["phrase"] for e in by_intent.get("prev", {}).get("builtin", [])],
              "'continue' and 'back' are exposed as editable keywords")

        await ws.send(json.dumps({"action": "set_voice_keywords", "op": "disable",
                                  "intent": "next", "phrase": "continue"}))
        kw = first(await collect(ws), "voice_keywords")
        entry = next(e for e in next(g for g in kw["intents"] if g["intent"] == "next")["builtin"]
                     if e["phrase"] == "continue")
        check(entry["enabled"] is False, "a stock keyword can be switched off and persists")

        await ws.send(json.dumps({"action": "set_voice_keywords", "op": "add",
                                  "intent": "prev", "phrase": "rewind that"}))
        kw = first(await collect(ws), "voice_keywords")
        check("rewind that" in next(g for g in kw["intents"] if g["intent"] == "prev")["custom"],
              "a custom keyword can be added")

        await ws.send(json.dumps({"action": "set_voice_keywords", "op": "remove",
                                  "intent": "prev", "phrase": "rewind that"}))
        kw = first(await collect(ws), "voice_keywords")
        check("rewind that" not in next(g for g in kw["intents"] if g["intent"] == "prev")["custom"],
              "a custom keyword can be removed")
        await ws.send(json.dumps({"action": "set_voice_keywords", "op": "enable",
                                  "intent": "next", "phrase": "continue"}))
        await collect(ws)

        # ── Every preview carries the French secondary text ──
        await ws.send(json.dumps({"action": "get_chapter", "book_number": 430, "chapter": 3}))
        chap = first(await collect(ws), "chapter_verses")
        row = next(v for v in chap["verses"] if v["verse"] == 16)
        await ws.send(json.dumps({"action": "stage_preview", "verse": row}))
        pv = first(await collect(ws), "preview_verse")
        check(pv is not None and "book_french" in pv,
              "a browser-staged preview is enriched with the French reference")
        # secondary_text only exists when a French edition is installed
        check(pv.get("secondary_text") is None or pv["secondary_text"].strip() != "",
              "a browser-staged preview carries the French verse text when available")
        await ws.send(json.dumps({"action": "clear_preview"}))
        await collect(ws)

    print()
    print(f"{len(fails)} failure(s)" if fails else "ALL PROTOCOL CHECKS PASSED")
    sys.exit(1 if fails else 0)

asyncio.run(main())
