from scripts.watchers.psws_watch9 import parse_instrument_from_trigger


def test_parse_instrument_current_timestamp_suffix():
    instrument, timestamp = parse_instrument_from_trigger(
        "/home/S000467/m_mag_#376_20260921T152537"
    )

    assert instrument == "376"
    assert timestamp == "20260921T152537"


def test_parse_instrument_legacy_hash_timestamp_suffix():
    instrument, timestamp = parse_instrument_from_trigger(
        "/home/S000467/m_#376_#2026-09-21T15:25"
    )

    assert instrument == "376"
    assert timestamp == "2026-09-21T15:25"


def test_parse_instrument_embedded_observation_name_with_legacy_hash_timestamp():
    instrument, timestamp = parse_instrument_from_trigger(
        "/home/S000003/mOBS2025-09-22T22:44_#193_#2026-09-21T17:01"
    )

    assert instrument == "193"
    assert timestamp == "2026-09-21T17:01"


def test_parse_named_instrument_without_timestamp():
    instrument, timestamp = parse_instrument_from_trigger(
        "/home/S000467/m_mag_#GMAG-01"
    )

    assert instrument == "GMAG-01"
    assert timestamp is None
