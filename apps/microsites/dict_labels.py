"""Thai labels for JMdict part-of-speech tags (anything missing falls back to JMdict's English description)."""

POS_TH = {
    "n": "คำนาม", "pn": "คำสรรพนาม", "n-suf": "คำนามต่อท้าย", "n-pref": "คำนามนำหน้า", "n-adv": "คำนามเชิงวิเศษณ์",
    "adj-i": "คุณศัพท์ い", "adj-ix": "คุณศัพท์ い (いい/よい)", "adj-na": "คุณศัพท์ な", "adj-no": "คำนามที่ขยายด้วย の",
    "adj-pn": "คำขยายนาม", "adj-t": "คุณศัพท์ たる", "adj-f": "คำขยายนาม",
    "adv": "คำวิเศษณ์", "adv-to": "คำวิเศษณ์ (ใช้กับ と)",
    "v1": "กริยากลุ่ม 2", "v1-s": "กริยากลุ่ม 2", "vs": "คำนามที่ใช้กับ する", "vs-i": "กริยากลุ่ม 3 (する)", "vs-s": "กริยากลุ่ม 3 (する)",
    "vk": "กริยากลุ่ม 3 (来る)", "vz": "กริยากลุ่ม 3 (ずる)", "vt": "กริยาที่ต้องมีกรรม", "vi": "กริยาที่ไม่ต้องมีกรรม",
    "prt": "คำช่วย", "conj": "คำสันธาน", "int": "คำอุทาน", "ctr": "ลักษณนาม", "suf": "ปัจจัยต่อท้าย", "pref": "อุปสรรคนำหน้า",
    "exp": "สำนวน / วลี", "aux": "คำช่วย", "aux-v": "คำช่วยกริยา", "aux-adj": "คำช่วยคุณศัพท์", "num": "ตัวเลข", "cop": "คำเชื่อม (だ / です)",
    "unc": "ไม่ระบุประเภท",
}


def pos_label(tag, tags):
    if tag in POS_TH:
        return POS_TH[tag]
    if tag.startswith("v5"):
        return "กริยากลุ่ม 1"
    return tags.get(tag, tag)


def jmdict_tags():
    """JMdict tag descriptions (English), read once from the bundled seed."""
    global _TAGS
    if _TAGS is None:
        from microsites.services.dict_import import load_seed
        _TAGS = load_seed().get("tags", {})
    return _TAGS


_TAGS = None
