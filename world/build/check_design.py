"""Phase 7B check: the designed layer (SITE.json `designed` and the designed nodes / edges of `process`)
against the rule of the user decision 2026-09-27 and against the norms in research/design/*.md.

FAIL (rule / norm):
  every designed node / edge points to a design note that exists, with >= 2 analog cards (basis analog or
  sourced) and >= 1 norm card, all present in inbox/records;
  wet bins: >= 2 (НПАОП: no filling and emptying of one metal silo at once), buffer >= 8 h of the dryer
  (ВНТП 05-88 п. 7.10);
  the dryer fits the plan of building «4» (user decision: the dryer is there);
  scales: 2, platform >= the longest road train (ПДР 22.5: 22 m), capacity >= its mass (40 t);
  power: S = P * Kc_max / cos φ within both transformers (ДБН В.2.2-8-98 табл. 5, II category);
  fire water: >= 2 tanks, volume >= the lower need (ДБН В.2.5-74);
  explosion vents of H5 / H6 >= РД 14-568-03 (analog).
WARN (own recommendation): one transformer short of the full load at Kc_max; fire water under the upper need.
FINDING: what the sampler reach covers.

Broken variants that must fail: the dryer note gone, a note with one analog, wet bins of 150 m³, 18 m
scales, the SSh-50 in building «4», 2 × 250 kVA, one fire tank, H5 vent 0.20 m².

Run:
    blender --background --python world/build/check_design.py
"""

import copy
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

# norms and analogs, typed from the cards (research/process_design.md), not read back from SITE.json
MIN_BUFFER_H = 8.0            # ВНТП 05-88 п. 7.10 (rec_d98f51e1)
MIN_WET_BINS = 2              # НПАОП п. 31 via KMZ (rec_82713fcf)
TRUCK_LEN, TRUCK_T = 22.0, 40.0   # ПДР п. 22.5 (rec_3ebdcd45)
KC_MAX, COS_PHI = 0.75, 0.75  # ДБН В.2.2-8-98 табл. 5 (rec_62e70183)
SPEC_KW = 546.88              # check_process.py: register = spec p.8-12
FIRE_NEED = (162.0, 270.0)    # ДБН В.2.5-74 (rec_5a301d66)
VENT_MIN = {"H5": 0.338, "H6": 0.145}   # РД 14-568-03 табл. 2, 3 (rec_56e8efc2)


def front(path):
    t = (REPO / path).read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---", t, re.S)
    meta = {}
    for ln in (m.group(1) if m else "").splitlines():
        k, _, v = ln.partition(":")
        meta[k.strip()] = [x.strip() for x in v.strip().strip("[]").split(",") if x.strip()] if v.strip().startswith("[") else v.strip()
    return meta


def card(rid):
    p = REPO / "inbox" / "records" / f"{rid}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def checks(site):
    out = []
    p, d = site["process"], site["designed"]
    notes = {n["note"].split(":")[0] for n in p["nodes"] if n.get("layer") == "designed" and n.get("note")}
    notes |= {e["note"].split(":")[0] for e in p["edges"] if e.get("layer") == "designed" and e.get("note")}
    notes |= {v["note"] for v in d.values() if isinstance(v, dict) and v.get("note")}
    undocumented = [n["id"] for n in p["nodes"] if n.get("layer") == "designed" and not n.get("note")] + \
        [f"{e['from']}->{e['to']}" for e in p["edges"] if e.get("layer") == "designed" and not e.get("note")]
    bad = []
    for path in sorted(notes):
        if not (REPO / path).exists():
            bad.append(f"{path}: missing")
            continue
        meta = front(path)
        an = [r for r in meta.get("analogs", []) if (c := card(r)) and c.get("basis") in ("analog", "sourced")]
        nm = [r for r in meta.get("norms", []) if card(r)]
        if len(an) < 2 or len(nm) < 1:
            bad.append(f"{path}: analogs {len(an)}, norms {len(nm)}")
    out.append(("every designed node / edge has a design note with >= 2 analogs and a norm", not bad and not undocumented,
                f"{len(notes)} notes; {bad}; no note {undocumented}"))

    wb, dr = d["wet_bins"], d["dryer"]
    t_each = wb["volume_m3_each"] * wb["bulk_t_m3"]
    hours = len(wb["silos"]) * t_each / dr["t_h_wet"]
    out.append(("wet bins: >= 2, buffer >= 8 h of the dryer (ВНТП п. 7.10, НПАОП)", len(wb["silos"]) >= MIN_WET_BINS and hours >= MIN_BUFFER_H,
                f"{len(wb['silos'])} × {t_each:.0f} t = {hours:.1f} h at {dr['t_h_wet']} t/h"))

    b4 = site["receiving"]["building_4"]
    bx, by = b4["outer_x"][1] - b4["outer_x"][0], b4["outer_y"][1] - b4["outer_y"][0]
    L, W = dr["size"][:2]
    fits = (L <= bx and W <= by) or (L <= by and W <= bx)
    out.append(("the dryer fits building «4» (user decision 2026-09-27)", fits, f"dryer {L} × {W} in {bx:.2f} × {by:.2f}"))

    sc = d["scales"]
    out.append(("scales: 2, platform >= road train 22 m, capacity >= 40 t (ПДР 22.5)",
                sc["count"] >= 2 and sc["platform"][0] >= TRUCK_LEN and sc["capacity_t"] >= TRUCK_T,
                f"{sc['count']} × {sc['platform'][0]} × {sc['platform'][1]} m, {sc['capacity_t']} t"))

    pw = d["power"]
    p_kw = SPEC_KW + sum(pw["extra_kw"].values())
    s_max = p_kw * KC_MAX / COS_PHI
    total = sum(pw["ktp_kva"])
    out.append(("power: S at Kc 0.75 within the substation (ДБН В.2.2-8-98, II category)", len(pw["ktp_kva"]) >= 2 and s_max <= total,
                f"P {p_kw:.0f} kW -> S {s_max:.0f} kVA vs {pw['ktp_kva']}"))
    one = min(pw["ktp_kva"])
    out.append(("power: one transformer carries the full load" + (": WARN" if one < s_max else ""), True,
                f"{one} kVA vs {s_max:.0f} kVA at Kc_max" + (" — on one transformer the load is shed (II category allows a break for switching)" if one < s_max else "")))

    fw = d["fire_water"]
    vol = fw["tanks"] * fw["tank_m3"]
    out.append(("fire water: >= 2 tanks, volume >= the lower need (ДБН В.2.5-74)", fw["tanks"] >= 2 and vol >= FIRE_NEED[0],
                f"{fw['tanks']} × {fw['tank_m3']} = {vol} m³, need {FIRE_NEED}"))
    if vol < FIRE_NEED[1]:
        out.append(("fire water under the upper need: WARN", True, f"{vol} < {FIRE_NEED[1]}"))

    vents = {k: d["vents"].get(k, 0) for k in VENT_MIN}
    reg = {m["id"]: m for m in site["equipment"]["items"]}
    reg_ok = all(reg.get(f"{k}.vent", {}).get("area_m2", 0) >= VENT_MIN[k] for k in VENT_MIN)
    from kit import noria_n100 as nn
    built = {}
    for t in site["noria_towers"]:
        vx, vy = nn.vent_panel(t["noria_model"])
        built[t["id"]] = (round(vx * vy, 3), vx <= nn.hood_length(nn.MODELS[t["noria_model"]]) - 0.1)
    geo_ok = all(built[k][0] >= VENT_MIN[k] - 1e-6 and built[k][1] for k in VENT_MIN)
    out.append(("explosion vents of H5 / H6 >= РД 14-568-03 (analog), in SITE and on the built head", all(vents[k] >= VENT_MIN[k] for k in VENT_MIN) and reg_ok and geo_ok,
                f"SITE {vents}, built (area, fits the hood) {built} vs {VENT_MIN}"))

    sm = d["sampler"]
    out.append(("sampler reach: FINDING", True, f"{sm['model']} reaches {sm['reach_m'][0]}-{sm['reach_m'][1]} m: about "
                f"{2 * sm['reach_m'][1]:.1f} m of a {TRUCK_LEN:.0f} m road train from one post — the truck moves once between probes"))
    return out


def main():
    run(json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8")))


def run(site):
    ok_all = True
    for name, ok, info in checks(site):
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)

    tmp = Path(tempfile.mkdtemp())
    one = tmp / "one_analog.md"
    one.write_text("---\nnode: x\nanalogs: [rec_eda294e3]\nnorms: [rec_d98f51e1]\n---\n", encoding="utf-8")

    def v_gone(s):
        s["designed"]["dryer"]["note"] = "research/design/no_such_note.md"
    def v_one(s):
        s["designed"]["dryer"]["note"] = str(one)                  # absolute: REPO / abs == abs
    def v_bins(s):
        s["designed"]["wet_bins"]["volume_m3_each"] = 150
    def v_scales(s):
        s["designed"]["scales"]["platform"] = [18.0, 3.0]
    def v_ssh50(s):
        s["designed"]["dryer"]["size"] = [11.646, 5.206, 22.435]
    def v_ktp(s):
        s["designed"]["power"]["ktp_kva"] = [250, 250]
    def v_fire(s):
        s["designed"]["fire_water"]["tanks"] = 1
    def v_vent(s):
        s["designed"]["vents"]["H5"] = 0.20

    variants = [("dryer note gone", v_gone), ("note with one analog", v_one), ("wet bins of 150 m³", v_bins),
                ("18 m scales", v_scales), ("SSh-50 in building «4»", v_ssh50), ("2 × 250 kVA", v_ktp),
                ("one fire tank", v_fire), ("H5 vent 0.20 m²", v_vent)]
    for name, patch in variants:
        bad = copy.deepcopy(site)
        patch(bad)
        failed = [n for n, ok, _ in checks(bad) if not ok]
        ok_all &= bool(failed)
        print(f"{'PASS' if failed else 'FAIL'}  broken variant must be rejected — {name}: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
