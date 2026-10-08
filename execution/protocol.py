from dataclasses import dataclass
import json
from typing import Any, Mapping


PROTOCOL_VERSION = 1


@dataclass(frozen=True)
class IpcMessage:
    protocol_version: int
    request_id: str
    message_type: str
    payload: Mapping[str, Any]

    def to_json_line(self) -> str:
        return json.dumps(
            {
                "protocol_version": self.protocol_version,
                "request_id": self.request_id,
                "message_type": self.message_type,
                "payload": self.payload,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ) + "\n"

    @classmethod
    def from_json_line(cls, line: str) -> "IpcMessage":
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid JSONL message") from exc

        if not isinstance(data, dict):
            raise ValueError("IPC message must be a JSON object")

        required = ("protocol_version", "request_id", "message_type", "payload")
        for field in required:
            if field not in data:
                raise ValueError(f"missing IPC field: {field}")

        if data["protocol_version"] != PROTOCOL_VERSION:
            raise ValueError(
                f"unsupported protocol_version: {data['protocol_version']}"
            )
        if not isinstance(data["request_id"], str) or not data["request_id"]:
            raise ValueError("request_id must be a non-empty string")
        if not isinstance(data["message_type"], str) or not data["message_type"]:
            raise ValueError("message_type must be a non-empty string")
        if not isinstance(data["payload"], dict):
            raise ValueError("payload must be a JSON object")

        return cls(
            protocol_version=data["protocol_version"],
            request_id=data["request_id"],
            message_type=data["message_type"],
            payload=data["payload"],
        )
