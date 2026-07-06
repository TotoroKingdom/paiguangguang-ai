from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.schemas.admin import AdminPagedData, AdminUserData
from app.services.admin import normalize_admin_list_query


def test_normalize_admin_list_query_applies_valid_defaults_and_overrides() -> None:
    query = normalize_admin_list_query(
        page=2,
        page_size=50,
        sort_by="updated_at",
        sort_order="asc",
        allowed_sort_by={"created_at", "updated_at"},
    )

    assert query.page == 2
    assert query.page_size == 50
    assert query.sort_by == "updated_at"
    assert query.sort_order == "asc"


@pytest.mark.parametrize("sort_by", ["email;drop table users", "unknown_field"])
def test_normalize_admin_list_query_rejects_invalid_sort_field(sort_by: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        normalize_admin_list_query(
            page=1,
            page_size=20,
            sort_by=sort_by,
            sort_order="desc",
            allowed_sort_by={"email", "created_at"},
        )

    assert exc_info.value.status_code == 400


def test_normalize_admin_list_query_rejects_invalid_sort_order() -> None:
    with pytest.raises(HTTPException) as exc_info:
        normalize_admin_list_query(
            page=1,
            page_size=20,
            sort_by="created_at",
            sort_order="sideways",
            allowed_sort_by={"created_at"},
        )

    assert exc_info.value.status_code == 400


def test_admin_paged_data_wraps_items_and_metadata() -> None:
    now = datetime.now(timezone.utc)
    payload = AdminPagedData[AdminUserData](
        items=[
            AdminUserData(
                id="user-1",
                email="admin@example.com",
                display_name="Admin",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        ],
        total=1,
        page=1,
        page_size=20,
    )

    assert payload.total == 1
    assert payload.page == 1
    assert payload.page_size == 20
    assert payload.items[0].email == "admin@example.com"
