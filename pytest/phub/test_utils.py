from app.client.phub import utils


def test_searchify_normalizes_spacing_and_symbols():
    assert utils.searchify("  luna   +test+1 ") == "luna+test+1"
    assert utils.searchify("（香港］ +学 生") == "香港+学+生"


def test_dashify_sorts_and_joins():
    assert utils.dashify(["uncategorized", "transgender", "straight"]) == "straight-transgender-uncategorized"
    assert utils.dashify("single") == "single"


def test_slugify_strips_non_alnum_and_dashifies():
    assert utils.slugify("Eva Elfie!") == "Eva-Elfie"


def test_parse_readable_number_handles_suffixes():
    assert utils.parse_readable_number("1,200") == 1200
    assert utils.parse_readable_number("2.5K") == 2500
    assert utils.parse_readable_number("3M") == 3_000_000
    assert utils.parse_readable_number("4B") == 4_000_000_000


def test_to_hhmmss_formats_properly():
    assert utils.to_hhmmss(59) == "00:59"
    assert utils.to_hhmmss(3601) == "01:00:01"
