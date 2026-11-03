#!/usr/bin/env python3
"""Generate the pinned 195-country capitals benchmark from mledoze/countries."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SOURCE_COMMIT = "6031f5df137c41c76d180c55a0782185ae3ed05b"
SOURCE_SHA256 = "0d92fb23b43ae080bd439f5dc5d61a8845395fdd0af1479b433c59fe079bd6fd"
SOURCE_URL = f"https://github.com/mledoze/countries/blob/{SOURCE_COMMIT}/countries.json"

# These arrangements require more context than a single upstream `capital` value.
CAPITAL_OVERRIDES: dict[str, list[tuple[str, str]]] = {
    "BO": [
        ("Sucre", "constitutional capital"),
        ("La Paz", "seat of government and de facto executive/legislative capital"),
    ],
    "LK": [
        ("Sri Jayawardenepura Kotte", "legislative capital"),
        ("Colombo", "executive and judicial capital"),
    ],
    "MY": [
        ("Kuala Lumpur", "official, legislative, and royal capital"),
        ("Putrajaya", "administrative and judicial capital"),
    ],
    "MN": [("Ulaanbaatar", "national capital")],
    "PS": [
        ("East Jerusalem", "claimed capital"),
        ("Ramallah", "administrative center"),
    ],
    "SZ": [
        ("Mbabane", "administrative capital"),
        ("Lobamba", "royal and legislative capital"),
    ],
    "ZA": [
        ("Pretoria", "executive capital"),
        ("Cape Town", "legislative capital"),
        ("Bloemfontein", "judicial capital"),
    ],
}

ALIASES = {
    "City of San Marino": ["City of San Marino", "San Marino"],
    "Kyiv": ["Kyiv", "Kiev"],
    "South Tarawa": ["South Tarawa", "Tarawa"],
    "St. George's": ["St. George's", "Saint George's"],
    "Tirana": ["Tirana", "Tiranë", "Tirane"],
    "Ulaanbaatar": ["Ulaanbaatar", "Ulan Bator"],
    "Yaren": ["Yaren", "Yaren District"],
    "Sri Jayawardenepura Kotte": [
        "Sri Jayawardenepura Kotte",
        "Sri Jayewardenepura Kotte",
        "Kotte",
    ],
}

ROLE_OVERRIDES = {
    "CH": "de facto federal city; Switzerland has no official capital",
    "NR": "de facto capital; Nauru has no official capital",
}

RELATED_SEATS = {
    "BJ": [{"name": "Cotonou", "role": "seat of government"}],
    "BI": [{"name": "Bujumbura", "role": "economic center and former capital"}],
    "CI": [{"name": "Abidjan", "role": "seat of many government institutions"}],
    "CL": [{"name": "Valparaíso", "role": "seat of the National Congress"}],
    "KR": [{"name": "Sejong City", "role": "administrative center for many ministries"}],
    "ME": [{"name": "Cetinje", "role": "Old Royal Capital"}],
    "NL": [{"name": "The Hague", "role": "seat of government and judiciary"}],
}


def _capital_roles(country: dict[str, Any]) -> list[dict[str, str]]:
    code = country["cca2"]
    override = CAPITAL_OVERRIDES.get(code)
    if override:
        return [{"name": name, "role": role} for name, role in override]
    role = ROLE_OVERRIDES.get(code, "national capital")
    return [{"name": name, "role": role} for name in country["capital"]]


def _question(country: str, index: int, capital_count: int) -> str:
    if capital_count > 1:
        return f"Name all national capital cities or distinct capital seats of {country}."
    templates = (
        "What is the capital of {country}?",
        "Name the capital city of {country}.",
        "Which city is the capital of {country}?",
    )
    return templates[index % len(templates)].format(country=country)


def _record(country: dict[str, Any], index: int) -> dict[str, Any]:
    code = country["cca2"]
    name = country["name"]["common"]
    roles = _capital_roles(country)
    answers = [ALIASES.get(item["name"], [item["name"]]) for item in roles]
    if len(roles) == 1:
        expected = f"{roles[0]['name']}."
    else:
        expected = "; ".join(f"{item['name']} ({item['role']})" for item in roles) + "."
    return {
        "id": f"geography.capital.{code.lower()}",
        "input": _question(name, index, len(roles)),
        "expected_output": expected,
        "accepted_answers": answers,
        "split": "test" if index % 5 == 0 else "validation",
        "metadata": {
            "country": name,
            "official_country_name": country["name"]["official"],
            "cca2": code,
            "cca3": country["cca3"],
            "region": country["region"],
            "subregion": country.get("subregion", ""),
            "capital_roles": roles,
            "related_seats": RELATED_SEATS.get(code, []),
            "source_capitals": country["capital"],
            "source_url": SOURCE_URL,
            "source_commit": SOURCE_COMMIT,
            "source_license": "ODbL-1.0",
        },
    }


def generate(source: Path, output: Path) -> list[dict[str, Any]]:
    payload = source.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(f"source SHA-256 mismatch: expected {SOURCE_SHA256}, got {digest}")
    countries = json.loads(payload)
    selected = [country for country in countries if country["unMember"] or country["cca2"] == "PS"]
    selected.sort(key=lambda country: country["name"]["common"])
    if len(selected) != 195:
        raise ValueError(f"expected 195 countries, found {len(selected)}")
    if len({country["cca2"] for country in selected}) != 195:
        raise ValueError("country codes are not unique")
    if any(not country["capital"] for country in selected):
        raise ValueError("every selected country must have an upstream capital")

    records = [_record(country, index) for index, country in enumerate(selected)]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records
        ),
        encoding="utf-8",
    )
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="pinned countries.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = generate(args.source, args.output)
    print(f"Generated {len(records)} capital records at {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
