from clipos import reframe
from clipos.ondertitels import ass_tijd, groepeer, maak_ass
from clipos.render import bepaal_grenzen


def w(start, woord):
    return {"start": start, "end": start + 0.3, "woord": woord}


def test_ass_tijd():
    assert ass_tijd(0) == "0:00:00.00"
    assert ass_tijd(61.234) == "0:01:01.23"


def test_groepeer_breekt_op_zinseinde_en_max_woorden():
    woorden = [w(0, "Dit"), w(0.4, "is"), w(0.8, "waar."), w(1.2, "Echt"), w(1.6, "heel"), w(2.0, "erg"), w(2.4, "waar")]
    groepen = groepeer(woorden)
    assert [len(g) for g in groepen] == [3, 3, 1]


def test_maak_ass_markeert_huidig_woord_en_hook():
    ass = maak_ass([w(10.0, "Hallo"), w(10.4, "wereld")], clip_start=10.0, duur=5.0, hook="Kijk dit")
    assert "Hook,,0,0,0,,Kijk dit" in ass
    assert "{\\c&H0000E5FF&}HALLO{\\c&H00FFFFFF&} WERELD" in ass
    assert "HALLO {\\c&H0000E5FF&}WERELD" in ass


def test_maak_ass_verwijdert_ass_codes_uit_tekst():
    ass = maak_ass([w(0, "{\\b1}hack")], 0, 2)
    assert "\\b1" not in ass


def test_crop_segmenten_stabiel_bij_ruis():
    posities = [(i * 0.5, 0.5 + (0.02 if i % 2 else -0.02)) for i in range(20)]
    assert len(reframe.crop_segmenten(posities, 10)) == 1


def test_crop_segmenten_volgt_camerawissel_en_vult_gaten():
    posities = [(i * 0.5, None if i == 3 else (0.25 if i < 10 else 0.75)) for i in range(20)]
    seg = reframe.crop_segmenten(posities, 10)
    assert len(seg) == 2 and seg[0][1] == 0.25 and seg[1][1] == 0.75


def test_crop_expressie_binnen_beeld():
    expr = reframe.crop_x_expressie([(0.0, 0.0), (5.0, 1.0)], 1920, 606)
    assert expr == "if(lt(t\\,5.00)\\,0\\,1314)"


def test_grenzen_vallen_op_woorden():
    transcript = {"segmenten": [{"woorden": [w(9.8, "a"), w(10.5, "b"), w(19.9, "c")]}]}
    start, end = bepaal_grenzen({"start": 10.0, "end": 20.0}, transcript, 100)
    assert start < 9.8 and end > 20.2
