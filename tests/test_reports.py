import glob
import json
import os
from datetime import datetime
from unittest.mock import mock_open, patch

import pandas as pd
import pytest

from src.reports import spending_by_category, write_report


def _cleanup_reports_dir(pattern: str) -> None:
    for path in glob.glob(pattern):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def test_spending_by_category_empty_df_writes_json_with_mock() -> None:
    df = pd.DataFrame()
    m = mock_open()
    with patch("src.reports.os.makedirs") as mk, patch("builtins.open", m):
        res = spending_by_category(df, category="Супермаркеты", date="2021-11-15")
    assert isinstance(res, pd.DataFrame)
    assert res.empty
    handle = m()
    assert handle.write.called
    written = "".join(call.args[0] for call in handle.write.call_args_list)
    payload = json.loads(written or "[]")
    assert isinstance(payload, list)


def test_spending_by_category_filters_three_months_and_category() -> None:
    # ref = 2021-11-15, период = 2021-08-15..2021-11-15 включительно
    data = {
        "Дата операции": [
            "15.11.2021 12:00:00",  # в период, целевая категория
            "14.08.2021 00:00:00",  # в период (нижняя граница), целевая категория
            "13.08.2021 23:59:59",  # вне периода
            "01.10.2021 10:00:00",  # в период, другая категория
        ],
        "Категория": ["Супермаркеты", "Супермаркеты", "Супермаркеты", "Другое"],
        "Сумма операции": [-100.0, -50.0, -999.0, -200.0],
        "Описание": ["Покупка 1", "Покупка 2", "Старая", "Не супермаркет"],
    }
    df = pd.DataFrame(data)

    m = mock_open()
    with patch("src.reports.os.makedirs") as mk, patch("builtins.open", m):
        res = spending_by_category(df, category="Супермаркеты", date="2021-11-15")
    assert list(res.columns) == ["date", "amount", "category", "description"]
    # Должны остаться две строки (15.11 и 14.08), а 13.08 — отфильтрована
    assert len(res) == 2
    # Проверим суммы и категорию
    assert set(res["amount"]) == {-100.0, -50.0}
    assert set(res["category"]) == {"Супермаркеты"}


def test_write_report_custom_filename(tmp_path) -> None:
    target_file = tmp_path / "custom_report.json"

    @write_report(str(target_file))
    def make_report() -> pd.DataFrame:
        return pd.DataFrame([{"a": 1}, {"a": 2}])

    m = mock_open()
    with patch("builtins.open", m):
        df = make_report()
    assert isinstance(df, pd.DataFrame)
    handle = m()
    written = "".join(call.args[0] for call in handle.write.call_args_list)
    payload = json.loads(written)
    assert payload == [{"a": 1}, {"a": 2}]


def test_write_report_default_filename_uses_timestamp_and_writes() -> None:
    fixed_dt = datetime(2024, 12, 31, 23, 59, 59)

    @write_report()
    def report() -> pd.DataFrame:
        return pd.DataFrame([{"x": 1}])

    m = mock_open()
    with (
        patch("src.reports.datetime") as mock_dt,
        patch("builtins.open", m),
        patch("src.reports.os.makedirs") as mk,
    ):
        mock_dt.now.return_value = fixed_dt
        # strptime не используется в декораторе, достаточно now().strftime на объекте datetime
        df = report()

    assert isinstance(df, pd.DataFrame)
    # Проверим, что писали JSON
    handle = m()
    assert handle.write.called
    written = "".join(call.args[0] for call in handle.write.call_args_list)
    payload = json.loads(written)
    assert payload == [{"x": 1}]
