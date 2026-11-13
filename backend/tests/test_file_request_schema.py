from app.modules.runtime.schemas import ExecuteRequest


def test_run_request_accepts_file_ids():
    request = ExecuteRequest(
        conversationId="conversation", clientTurnId="turn", text="read this",
        fileIds=["file-a"],
    )
    assert request.fileIds == ["file-a"]
