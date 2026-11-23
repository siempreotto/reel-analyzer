from reelkit.build import _voice_between, meta_from_info

PROBE = {"duracion_s": 10.0, "ancho": 1080, "alto": 1920, "tiene_audio": True, "orientacion": "vertical"}


def test_instagram_account_uses_handle_not_numeric_id():
    info = {"id": "X", "uploader": "Mark M", "uploader_id": "26985959", "channel": "markbrazil"}
    assert meta_from_info(info, "instagram", None, PROBE)["cuenta"] == "@markbrazil"


def test_youtube_handle_kept():
    info = {"id": "X", "uploader": "Canal", "uploader_id": "@canal", "channel": "Canal"}
    assert meta_from_info(info, "youtube", None, PROBE)["cuenta"] == "@canal"


def test_voice_split_by_words_across_cuts():
    seg = {"start": 3.8, "end": 9.2, "text": "Yeah, in the world that we live",
           "palabras": [[3.8, 4.1, " Yeah,"], [4.2, 4.5, " in"], [6.4, 6.6, " the"], [7.0, 7.3, " world"]]}
    assert _voice_between([seg], 3.04, 4.21) == "Yeah,"
    assert _voice_between([seg], 4.21, 6.30) == "in"
    assert _voice_between([seg], 6.30, 6.67) == "the"
    assert _voice_between([seg], 6.67, 9.18) == "world"


def test_tiktok_account_uses_handle_not_display_name():
    info = {"id": "X", "uploader": "maverickgpt", "uploader_id": "6812345", "channel": "Maverick Maltin | AI"}
    assert meta_from_info(info, "tiktok", None, PROBE)["cuenta"] == "@maverickgpt"


def test_subtitle_segment_spread_across_cut():
    seg = {"start": 0.0, "end": 4.0, "text": "uno dos tres cuatro"}
    assert _voice_between([seg], 0.0, 2.0) == "uno dos"
    assert _voice_between([seg], 2.0, 4.0) == "tres cuatro"


def test_vocab_prompt_has_no_emojis_or_sentences():
    from reelkit.transcribe import clean_text, vocab_prompt
    cap = "¿Tus webs creadas con Claude siguen pareciendo genéricas? 👀‼️ 1️⃣ Emil Kowalski + Impeccable → reglas"
    p = vocab_prompt("@migue.baena", cap)
    assert "1️⃣" not in p and "👀" not in p and "¿Tus" not in p
    for term in ("migue.baena", "Claude", "Emil", "Kowalski", "Impeccable"):
        assert term in p
    assert clean_text("2️⃣ Claude puede crear") == "2 Claude puede crear"
