#!/usr/bin/env python3
"""Compile the human-editable scenes.json into a Pannellum tour.json.

scenes.json (edit this):
  {
    "title": "...", "firstScene": "scene15",
    "default": { ...Pannellum default block... },
    "scenes": [
      { "id": "scene01", "title": "Спальня", "group": "Спальня",
        "yaw": 0, "pitch": 0,
        "hotspots": [
          {"type": "scene", "sceneId": "scene04", "yaw": 120, "pitch": -5,
           "text": "В коридор", "targetYaw": -30, "targetPitch": 0},
          {"type": "info",  "yaw": 40,  "pitch": 0, "text": "Балкон 6 м²"}
        ] }
    ]
  }

tour.json (generated — do not edit by hand): standard Pannellum config.
Run: python3 scripts/build-tour.py   (or: just tour)
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "scenes.json"
OUT = ROOT / "tour.json"
IMG_DIR = "images"

def main() -> int:
    cfg = json.loads(SRC.read_text(encoding="utf-8"))
    scenes_in = cfg["scenes"]
    ids = {s["id"] for s in scenes_in}
    # Scenes marked "fixedView": true always open at their own yaw/pitch/hfov,
    # no matter which hotspot you arrive through (the per-scene angle is "pinned").
    fixed = {s["id"]: s for s in scenes_in if s.get("fixedView")}

    default = dict(cfg.get("default", {}))
    default.setdefault("firstScene", cfg.get("firstScene", scenes_in[0]["id"]))

    out = {"default": default, "scenes": {}}
    problems = []

    for s in scenes_in:
        sid = s["id"]
        img = ROOT / IMG_DIR / f"{sid}.jpg"
        if not img.exists():
            problems.append(f"missing image: {img}")
        scene = {
            "type": "equirectangular",
            "panorama": f"{IMG_DIR}/{sid}.jpg",
            "title": s.get("title", sid),
            "yaw": s.get("yaw", 0),
            "pitch": s.get("pitch", 0),
            "hfov": s.get("hfov", default.get("hfov", 110)),
        }
        hotspots = []
        for h in s.get("hotspots", []):
            hs = {
                "pitch": h["pitch"],
                "yaw": h["yaw"],
                "type": h.get("type", "scene"),
            }
            if hs["type"] == "scene":
                tgt = h["sceneId"]
                if tgt not in ids:
                    problems.append(f"{sid}: hotspot -> unknown scene '{tgt}'")
                hs["sceneId"] = tgt
                hs["text"] = h.get("text", "")
                if tgt in fixed:
                    # Pinned target: force its fixed angle on every inbound arrow.
                    ft = fixed[tgt]
                    hs["targetYaw"] = ft.get("yaw", 0)
                    hs["targetPitch"] = ft.get("pitch", 0)
                    if "hfov" in ft:
                        hs["targetHfov"] = ft["hfov"]
                else:
                    # Preserve the viewing direction across a hotspot transition:
                    # the target opens at the same yaw the user was looking at.
                    # A per-hotspot "targetYaw" in scenes.json overrides this.
                    # (Menu jumps don't use targetYaw, so they honour the scene's
                    # own default yaw either way.)
                    hs["targetYaw"] = h.get("targetYaw", "sameAzimuth")
                    if "targetPitch" in h:
                        hs["targetPitch"] = h["targetPitch"]
            else:
                hs["text"] = h.get("text", "")
            hotspots.append(hs)
        if hotspots:
            scene["hotSpots"] = hotspots
        # keep group as custom field for the in-page menu
        if "group" in s:
            scene["group"] = s["group"]
        # passthrough so the editor can show the pinned state (Pannellum ignores it)
        if s.get("fixedView"):
            scene["fixedView"] = True
        out["scenes"][sid] = scene

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    n_hs = sum(len(s.get("hotSpots", [])) for s in out["scenes"].values())
    print(f"Wrote {OUT.name}: {len(out['scenes'])} scenes, {n_hs} hotspots.")
    if problems:
        print("WARNINGS:", file=sys.stderr)
        for p in problems:
            print("  -", p, file=sys.stderr)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
