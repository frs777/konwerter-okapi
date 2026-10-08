import json

import pytest

from execution.protocol import IpcMessage


def test_ipc_message_round_trips_as_one_json_line():
    message = IpcMessage(
        protocol_version=1,
        request_id="req-1",
        message_type="job.started",
        payload={"job_id": "job-1", "state": "OPENING"},
    )

    line = message.to_json_line()

    assert line.endswith("\n")
    assert json.loads(line) == {
        "protocol_version": 1,
        "request_id": "req-1",
        "message_type": "job.started",
        "payload": {"job_id": "job-1", "state": "OPENING"},
    }
    assert IpcMessage.from_json_line(line) == message


def test_ipc_message_rejects_invalid_envelope():
    with pytest.raises(ValueError, match="protocol_version"):
        IpcMessage.from_json_line('{"request_id":"req-1","message_type":"x","payload":{}}\n')
