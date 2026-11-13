from test_platform import headers, login, make_user, new_client


def test_text_upload_above_global_json_limit_is_allowed():
    make_user("901")
    client = new_client()
    login(client, "901")

    payload = ("a" * (300 * 1024)).encode("utf-8")
    response = client.post(
        "/api/v1/me/files",
        files={"file": ("large-notes.txt", payload, "text/plain")},
        headers=headers(client),
    )

    assert response.status_code == 201, response.text
    assert response.json()["sizeBytes"] == len(payload)


def test_upload_over_five_mib_is_rejected():
    make_user("902")
    client = new_client()
    login(client, "902")

    payload = b"x" * (5 * 1024 * 1024 + 1)
    response = client.post(
        "/api/v1/me/files",
        files={"file": ("too-large.txt", payload, "text/plain")},
        headers=headers(client),
    )

    assert response.status_code == 413, response.text
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_binary_file_type_is_rejected():
    make_user("903")
    client = new_client()
    login(client, "903")

    response = client.post(
        "/api/v1/me/files",
        files={"file": ("payload.exe", b"MZ\x00\x01", "application/octet-stream")},
        headers=headers(client),
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "FILE_TYPE_UNSUPPORTED"


def test_invalid_utf8_text_is_rejected():
    make_user("904")
    client = new_client()
    login(client, "904")

    response = client.post(
        "/api/v1/me/files",
        files={"file": ("broken.txt", b"valid prefix\xff\xfe", "text/plain")},
        headers=headers(client),
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "FILE_CONTENT_INVALID"
