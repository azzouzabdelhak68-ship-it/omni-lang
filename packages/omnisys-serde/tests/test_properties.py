import omnisys_serde as serde
from hypothesis import given
from hypothesis import strategies as st

json_value = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(),
    lambda children: (
        st.lists(children, max_size=5) | st.dictionaries(st.text(), children, max_size=5)
    ),
    max_leaves=20,
)

csv_cell = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126, blacklist_characters=','),
    min_size=1,
    max_size=20,
)
csv_rows = st.lists(st.lists(csv_cell, min_size=1, max_size=5), min_size=1, max_size=5)


@given(json_value)
def test_json_round_trip(value: object) -> None:
    assert serde.json_decode(serde.json_encode(value)) == value


@given(st.text())
def test_to_hex_round_trip(text: str) -> None:
    assert serde.from_hex(serde.to_hex(text)) == text


@given(st.text())
def test_base64_round_trip(text: str) -> None:
    assert serde.base64_decode(serde.base64_encode(text)) == text


@given(csv_rows)
def test_csv_round_trip(rows: list[list[str]]) -> None:
    assert serde.csv_decode(serde.csv_encode(rows)) == rows


@given(json_value)
def test_schema_validate_lenient(value: object) -> None:
    assert serde.schema_validate(value, {}) is True
    assert serde.schema_validate(value, {'type': 'any'}) is True
    assert serde.schema_validate(value, None) is True


@given(json_value)
def test_schema_validate_any_schema_matches(value: object) -> None:
    assert serde.schema_validate(value, {'type': 'any', 'fields': {}}) is True
