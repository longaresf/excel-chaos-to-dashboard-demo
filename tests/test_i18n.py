from __future__ import annotations

import pandas as pd
import pytest

from app.i18n import (
    COLUMN_TRANSLATIONS,
    DEFAULT_LANGUAGE,
    LABEL_TO_LANGUAGE,
    LANGUAGE_NAMES,
    SUPPORTED_LANGUAGES,
    TRANSLATIONS,
    extract_format_placeholders,
    get_audit_metric_cards,
    localize_dataframe,
    t,
)


def test_supported_languages_configuration() -> None:
    assert DEFAULT_LANGUAGE == "es"
    assert "es" in SUPPORTED_LANGUAGES
    assert "en" in SUPPORTED_LANGUAGES
    assert set(LANGUAGE_NAMES.keys()) == set(SUPPORTED_LANGUAGES)
    assert set(LABEL_TO_LANGUAGE.values()) == set(SUPPORTED_LANGUAGES)


def test_translation_keys_parity() -> None:
    es_keys = set(TRANSLATIONS["es"].keys())
    en_keys = set(TRANSLATIONS["en"].keys())
    missing_in_en = es_keys - en_keys
    missing_in_es = en_keys - es_keys
    assert not missing_in_en, f"Keys in ES missing in EN: {missing_in_en}"
    assert not missing_in_es, f"Keys in EN missing in ES: {missing_in_es}"


def test_column_translations_parity() -> None:
    es_cols = set(COLUMN_TRANSLATIONS["es"].keys())
    en_cols = set(COLUMN_TRANSLATIONS["en"].keys())
    missing_in_en = es_cols - en_cols
    missing_in_es = en_cols - es_cols
    assert not missing_in_en, f"Column keys in ES missing in EN: {missing_in_en}"
    assert not missing_in_es, f"Column keys in EN missing in ES: {missing_in_es}"


def test_format_placeholders_parity() -> None:
    for key in TRANSLATIONS["es"]:
        es_text = TRANSLATIONS["es"][key]
        en_text = TRANSLATIONS["en"][key]
        es_placeholders = extract_format_placeholders(es_text)
        en_placeholders = extract_format_placeholders(en_text)
        assert es_placeholders == en_placeholders, (
            f"Placeholder mismatch for key '{key}': "
            f"es={es_placeholders} vs en={en_placeholders}"
        )


@pytest.mark.parametrize("lang", ["es", "en"])
def test_t_function_translates_known_keys(lang: str) -> None:
    title = t("page_title", lang=lang)
    assert isinstance(title, str)
    assert len(title) > 0
    if lang == "es":
        assert "Visibilidad" in title
    else:
        assert "Visibility" in title


def test_t_formatting_with_kwargs() -> None:
    error_msg = "test error"
    es_error = t("pipeline_error", "es", error=error_msg)
    en_error = t("pipeline_error", "en", error=error_msg)
    assert error_msg in es_error
    assert "pipeline" in es_error
    assert error_msg in en_error
    assert "pipeline" in en_error

    caption_es = t("raw_file_caption", "es", rows=10, blanks=2, duplicates=1)
    caption_en = t("raw_file_caption", "en", rows=10, blanks=2, duplicates=1)
    assert "10 filas" in caption_es
    assert "10 rows" in caption_en


def test_t_fallback_behavior() -> None:
    # Unknown key returns the key itself
    assert t("non_existent_key_xyz", "es") == "non_existent_key_xyz"
    # Unsupported language code falls back to default language (es)
    assert t("page_title", "fr") == TRANSLATIONS["es"]["page_title"]


def test_localize_dataframe_translates_columns_without_modifying_original() -> None:
    original = pd.DataFrame({"ventas_netas": [1000], "margen_bruto": [500]})
    localized_es = localize_dataframe(original, "es")
    localized_en = localize_dataframe(original, "en")

    # Original columns unchanged
    assert list(original.columns) == ["ventas_netas", "margen_bruto"]
    # Localized versions renamed
    assert list(localized_es.columns) == ["Ventas Netas", "Margen Bruto"]
    assert list(localized_en.columns) == ["Net Sales", "Gross Margin"]
    # Values match
    assert localized_en["Net Sales"].iloc[0] == 1000


def test_get_audit_metric_cards() -> None:
    cards_es = get_audit_metric_cards("es")
    cards_en = get_audit_metric_cards("en")

    assert len(cards_es) == 4
    assert len(cards_en) == 4

    keys_es = [k for _, k in cards_es]
    keys_en = [k for _, k in cards_en]
    assert keys_es == keys_en
    assert keys_es == [
        "filas_procesadas",
        "duplicados_eliminados",
        "ids_normalizados",
        "filas_en_cuarentena",
    ]

    labels_es = [label for label, _ in cards_es]
    labels_en = [label for label, _ in cards_en]
    assert "Filas procesadas" in labels_es
    assert "Rows processed" in labels_en


def test_language_switching_simulation() -> None:
    # Simulate UI state transitions
    session_state = {}

    # Initial state defaults to es
    selected_label = session_state.get("lang_choice", LANGUAGE_NAMES[DEFAULT_LANGUAGE])
    lang = LABEL_TO_LANGUAGE.get(selected_label, DEFAULT_LANGUAGE)
    assert lang == "es"
    assert t("run_pipeline_button", lang) == "Ejecutar pipeline de datos"

    # User changes selection to English
    session_state["lang_choice"] = "English"
    selected_label = session_state["lang_choice"]
    lang = LABEL_TO_LANGUAGE.get(selected_label, DEFAULT_LANGUAGE)
    assert lang == "en"
    assert t("run_pipeline_button", lang) == "Run data pipeline"
