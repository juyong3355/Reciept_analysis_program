from receipt_mvp.config.settings import DEFAULT_SETTINGS


def test_settings_match_documented_gates() -> None:
    assert DEFAULT_SETTINGS.amount_tolerance_krw == 1
    assert DEFAULT_SETTINGS.text_min_characters == 80
    assert DEFAULT_SETTINGS.critical_confidence_threshold >= DEFAULT_SETTINGS.general_confidence_threshold

