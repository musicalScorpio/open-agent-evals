from datetime import date

from arlab.matching import answer_contains_phrase, arguments_match, normalized_argument_variant


def test_relative_weather_dates_accept_equivalent_iso_dates() -> None:
    reference = date(2026, 11, 2)

    assert arguments_match(
        {"city": "Miami", "date": "2026-11-02"},
        {"city": "Miami", "date": "tonight"},
        reference_date=reference,
    )
    assert arguments_match(
        {"city": "Seattle", "date": "2026-11-03"},
        {"city": "Seattle", "date": "tomorrow"},
        reference_date=reference,
    )


def test_argument_matching_remains_strict_for_unrelated_values() -> None:
    reference = date(2026, 11, 2)

    assert not arguments_match(
        {"city": "Miami", "date": "2026-11-03"},
        {"city": "Miami", "date": "tonight"},
        reference_date=reference,
    )
    assert normalized_argument_variant(
        {"city": "Phoenix", "date": "this afternoon"}, reference_date=reference
    ) == {"city": "Phoenix", "date": "2026-11-02"}


def test_capital_answer_matching_handles_accents_and_boundaries() -> None:
    assert answer_contains_phrase("The capital is Sao Tome.", "São Tomé")
    assert answer_contains_phrase("It is Sri Jayewardenepura Kotte.", "Kotte")
    assert not answer_contains_phrase("That is a female name.", "Malé")
