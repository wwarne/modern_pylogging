import json
from typing import Any


def json_dumps(obj_to_serialize: Any) -> str:
    return json.dumps(obj_to_serialize, ensure_ascii=False)
