"""Hiragana / katakana data for อักษรภาษาญี่ปุ่น.online (RYU KANA).

Each sound is defined once in hiragana; katakana is derived by code point (+0x60).  Romaji is Hepburn; the Thai
reading follows the common Thai transcription used in Japanese textbooks.  Example words are everyday words a
beginner meets early (hiragana: native words, katakana: loanwords).
"""

# (hiragana, romaji, thai) laid out as the classic 5-column chart; None = empty cell
BASIC = [
    [("あ", "a", "อะ"), ("い", "i", "อิ"), ("う", "u", "อุ"), ("え", "e", "เอะ"), ("お", "o", "โอะ")],
    [("か", "ka", "คะ"), ("き", "ki", "คิ"), ("く", "ku", "คุ"), ("け", "ke", "เคะ"), ("こ", "ko", "โคะ")],
    [("さ", "sa", "สะ"), ("し", "shi", "ชิ"), ("す", "su", "สุ"), ("せ", "se", "เสะ"), ("そ", "so", "โสะ")],
    [("た", "ta", "ทะ"), ("ち", "chi", "จิ"), ("つ", "tsu", "ทสึ"), ("て", "te", "เทะ"), ("と", "to", "โทะ")],
    [("な", "na", "นะ"), ("に", "ni", "นิ"), ("ぬ", "nu", "นุ"), ("ね", "ne", "เนะ"), ("の", "no", "โนะ")],
    [("は", "ha", "ฮะ"), ("ひ", "hi", "ฮิ"), ("ふ", "fu", "ฟุ"), ("へ", "he", "เฮะ"), ("ほ", "ho", "โฮะ")],
    [("ま", "ma", "มะ"), ("み", "mi", "มิ"), ("む", "mu", "มุ"), ("め", "me", "เมะ"), ("も", "mo", "โมะ")],
    [("や", "ya", "ยะ"), None, ("ゆ", "yu", "ยุ"), None, ("よ", "yo", "โยะ")],
    [("ら", "ra", "ระ"), ("り", "ri", "ริ"), ("る", "ru", "รุ"), ("れ", "re", "เระ"), ("ろ", "ro", "โระ")],
    [("わ", "wa", "วะ"), None, None, None, ("を", "o (wo)", "โอะ")],
    [("ん", "n", "อึน"), None, None, None, None],
]

DAKUTEN = [
    [("が", "ga", "กะ"), ("ぎ", "gi", "กิ"), ("ぐ", "gu", "กุ"), ("げ", "ge", "เกะ"), ("ご", "go", "โกะ")],
    [("ざ", "za", "ซะ"), ("じ", "ji", "จิ"), ("ず", "zu", "ซุ"), ("ぜ", "ze", "เซะ"), ("ぞ", "zo", "โซะ")],
    [("だ", "da", "ดะ"), ("ぢ", "ji", "จิ"), ("づ", "zu", "ซุ"), ("で", "de", "เดะ"), ("ど", "do", "โดะ")],
    [("ば", "ba", "บะ"), ("び", "bi", "บิ"), ("ぶ", "bu", "บุ"), ("べ", "be", "เบะ"), ("ぼ", "bo", "โบะ")],
    [("ぱ", "pa", "ปะ"), ("ぴ", "pi", "ปิ"), ("ぷ", "pu", "ปุ"), ("ぺ", "pe", "เปะ"), ("ぽ", "po", "โปะ")],
]

YOON = [
    [("きゃ", "kya", "เคียะ"), ("きゅ", "kyu", "คิว"), ("きょ", "kyo", "เคียว")],
    [("しゃ", "sha", "ชะ"), ("しゅ", "shu", "ชุ"), ("しょ", "sho", "โชะ")],
    [("ちゃ", "cha", "จะ"), ("ちゅ", "chu", "จุ"), ("ちょ", "cho", "โจะ")],
    [("にゃ", "nya", "เนียะ"), ("にゅ", "nyu", "นิว"), ("にょ", "nyo", "เนียว")],
    [("ひゃ", "hya", "เฮียะ"), ("ひゅ", "hyu", "ฮิว"), ("ひょ", "hyo", "เฮียว")],
    [("みゃ", "mya", "เมียะ"), ("みゅ", "myu", "มิว"), ("みょ", "myo", "เมียว")],
    [("りゃ", "rya", "เรียะ"), ("りゅ", "ryu", "ริว"), ("りょ", "ryo", "เรียว")],
    [("ぎゃ", "gya", "เกียะ"), ("ぎゅ", "gyu", "กิว"), ("ぎょ", "gyo", "เกียว")],
    [("じゃ", "ja", "จะ"), ("じゅ", "ju", "จุ"), ("じょ", "jo", "โจะ")],
    [("びゃ", "bya", "เบียะ"), ("びゅ", "byu", "บิว"), ("びょ", "byo", "เบียว")],
    [("ぴゃ", "pya", "เปียะ"), ("ぴゅ", "pyu", "ปิว"), ("ぴょ", "pyo", "เปียว")],
]

# example word for each basic sound: hiragana key -> ((hiragana word, romaji, Thai), (katakana word, romaji, Thai))
EXAMPLES = {
    "あ": (("あめ", "ame", "ฝน"), ("アイス", "aisu", "ไอศกรีม")),
    "い": (("いぬ", "inu", "สุนัข"), ("イギリス", "igirisu", "ประเทศอังกฤษ")),
    "う": (("うみ", "umi", "ทะเล"), ("ウイルス", "uirusu", "ไวรัส")),
    "え": (("えき", "eki", "สถานีรถไฟ"), ("エアコン", "eakon", "เครื่องปรับอากาศ")),
    "お": (("おちゃ", "ocha", "ชาเขียว"), ("オレンジ", "orenji", "ส้ม")),
    "か": (("かさ", "kasa", "ร่ม"), ("カメラ", "kamera", "กล้องถ่ายรูป")),
    "き": (("きのこ", "kinoko", "เห็ด"), ("キロ", "kiro", "กิโล")),
    "く": (("くるま", "kuruma", "รถยนต์"), ("クラス", "kurasu", "ห้องเรียน")),
    "け": (("けいたい", "keitai", "โทรศัพท์มือถือ"), ("ケーキ", "kēki", "เค้ก")),
    "こ": (("こども", "kodomo", "เด็ก"), ("コーヒー", "kōhī", "กาแฟ")),
    "さ": (("さかな", "sakana", "ปลา"), ("サラダ", "sarada", "สลัด")),
    "し": (("しお", "shio", "เกลือ"), ("シャツ", "shatsu", "เสื้อเชิ้ต")),
    "す": (("すし", "sushi", "ซูชิ"), ("スマホ", "sumaho", "สมาร์ตโฟน")),
    "せ": (("せんせい", "sensei", "ครู"), ("セーター", "sētā", "เสื้อสเวตเตอร์")),
    "そ": (("そら", "sora", "ท้องฟ้า"), ("ソファ", "sofa", "โซฟา")),
    "た": (("たまご", "tamago", "ไข่"), ("タクシー", "takushī", "แท็กซี่")),
    "ち": (("ちず", "chizu", "แผนที่"), ("チーズ", "chīzu", "ชีส")),
    "つ": (("つくえ", "tsukue", "โต๊ะ"), ("ツアー", "tsuā", "ทัวร์")),
    "て": (("てがみ", "tegami", "จดหมาย"), ("テレビ", "terebi", "โทรทัศน์")),
    "と": (("とけい", "tokei", "นาฬิกา"), ("トマト", "tomato", "มะเขือเทศ")),
    "な": (("なつ", "natsu", "ฤดูร้อน"), ("ナイフ", "naifu", "มีด")),
    "に": (("にく", "niku", "เนื้อสัตว์"), ("ニュース", "nyūsu", "ข่าว")),
    "ぬ": (("ぬいぐるみ", "nuigurumi", "ตุ๊กตา"), ("ヌードル", "nūdoru", "บะหมี่")),
    "ね": (("ねこ", "neko", "แมว"), ("ネクタイ", "nekutai", "เนกไท")),
    "の": (("のみもの", "nomimono", "เครื่องดื่ม"), ("ノート", "nōto", "สมุดโน้ต")),
    "は": (("はな", "hana", "ดอกไม้"), ("ハンバーガー", "hanbāgā", "แฮมเบอร์เกอร์")),
    "ひ": (("ひと", "hito", "คน"), ("ヒーター", "hītā", "เครื่องทำความร้อน")),
    "ふ": (("ふね", "fune", "เรือ"), ("フランス", "furansu", "ประเทศฝรั่งเศส")),
    "へ": (("へや", "heya", "ห้อง"), ("ヘリコプター", "herikoputā", "เฮลิคอปเตอร์")),
    "ほ": (("ほん", "hon", "หนังสือ"), ("ホテル", "hoteru", "โรงแรม")),
    "ま": (("まど", "mado", "หน้าต่าง"), ("マンガ", "manga", "มังงะ")),
    "み": (("みみ", "mimi", "หู"), ("ミルク", "miruku", "นม")),
    "む": (("むし", "mushi", "แมลง"), ("ムービー", "mūbī", "ภาพยนตร์")),
    "め": (("めがね", "megane", "แว่นตา"), ("メール", "mēru", "อีเมล")),
    "も": (("もも", "momo", "ลูกพีช"), ("モデル", "moderu", "นายแบบ / นางแบบ")),
    "や": (("やま", "yama", "ภูเขา"), ("ヤング", "yangu", "วัยรุ่น")),
    "ゆ": (("ゆき", "yuki", "หิมะ"), ("ユニフォーム", "yunifōmu", "ชุดยูนิฟอร์ม")),
    "よ": (("よる", "yoru", "กลางคืน"), ("ヨーグルト", "yōguruto", "โยเกิร์ต")),
    "ら": (("らいねん", "rainen", "ปีหน้า"), ("ラーメン", "rāmen", "ราเมน")),
    "り": (("りんご", "ringo", "แอปเปิล"), ("リモコン", "rimokon", "รีโมต")),
    "る": (("るす", "rusu", "ไม่อยู่บ้าน"), ("ルール", "rūru", "กฎ")),
    "れ": (("れいぞうこ", "reizōko", "ตู้เย็น"), ("レストラン", "resutoran", "ร้านอาหาร")),
    "ろ": (("ろうそく", "rōsoku", "เทียน"), ("ロボット", "robotto", "หุ่นยนต์")),
    "わ": (("わたし", "watashi", "ฉัน"), ("ワイン", "wain", "ไวน์")),
    "を": (("ほんをよむ", "hon o yomu", "อ่านหนังสือ (を ใช้เป็นคำช่วยเท่านั้น)"), None),
    "ん": (("ぱん", "pan", "ขนมปัง (ん ไม่อยู่ต้นคำ)"), ("パン", "pan", "ขนมปัง")),
}


def to_katakana(text):
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in text)


def _cell(entry, script):
    if entry is None:
        return None
    hira, romaji, thai = entry
    cell = {"kana": hira if script == "hiragana" else to_katakana(hira), "romaji": romaji, "thai": thai, "key": hira}
    example = EXAMPLES.get(hira)
    if example:
        word = example[0] if script == "hiragana" else example[1]
        if word:
            cell["example"] = {"word": word[0], "romaji": word[1], "meaning": word[2]}
    return cell


GROUPS = [("basic", "ตัวพื้นฐาน (เซอิอง)", BASIC), ("dakuten", "เสียงขุ่น (ดะกุอง · ฮันดะกุอง)", DAKUTEN),
          ("yoon", "เสียงควบ (โยอง)", YOON)]


def chart(script):
    """[{key, title, rows: [[cell|None, ...]], count}] for one script ("hiragana" | "katakana")."""
    out = []
    for key, title, rows in GROUPS:
        grid = [[_cell(e, script) for e in row] for row in rows]
        out.append({"key": key, "title": title, "rows": grid, "count": sum(1 for row in grid for c in row if c)})
    return out


def flat(script):
    """Every cell of one script, for the quiz."""
    return [dict(c, group=g["key"]) for g in chart(script) for row in g["rows"] for c in row if c]


def to_hiragana(text):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)


_THAI = {e[0]: e[2] for rows in (BASIC, DAKUTEN, YOON) for row in rows for e in row if e}
_THAI["を"] = "โวะ"


_ROMAJI = {e[0]: e[1] for rows in (BASIC, DAKUTEN, YOON) for row in rows for e in row if e}


def _close_with_n(syllable):
    """Thai syllable + final ん: "คะ" -> "คัน", "เสะ" -> "เส็น", "จิ" -> "จิน"."""
    if syllable.endswith("ะ"):
        base = syllable[:-1]
        if "ีย" in base:
            return base + "น"                          # เคียะ -> เคียน
        if base[:1] == "เ":
            return base + "็น"                         # เสะ -> เส็น
        if base[:1] == "โ":
            return base[1:] + "น"                      # โคะ -> คน
        return base[:1] + "ั" + base[1:] + "น"         # คะ -> คัน
    return syllable + "น"


def reading_to_thai(reading):
    """Approximate Thai transcription of a kana reading ("ひと.つ" -> "ฮิโทะทสึ", "きょう" -> "เคียว").
    Long vowels (おう, うう) are shortened, ん closes the previous syllable, small っ and KANJIDIC2 punctuation
    are dropped: a reading aid, not a strict romanisation."""
    text = to_hiragana(reading).replace(".", "").replace("-", "").replace("!", "")
    out, last, i = [], "", 0
    while i < len(text):
        pair = text[i:i + 2]
        unit = pair if pair in _THAI else text[i]
        i += len(unit)
        if unit == "ん" and out:
            out[-1] = _close_with_n(out[-1]); last = "n"; continue
        if unit == "う" and last[-1:] in ("o", "u"):
            continue                                   # long vowel: こう -> โค(ะ), きょう -> เคียว
        if unit in _THAI:
            out.append(_THAI[unit]); last = _ROMAJI.get(unit, "")
    return "".join(out)


def to_katakana_reading(reading):
    return to_katakana(reading.replace("-", ""))
