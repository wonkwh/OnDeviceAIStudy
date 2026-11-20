"""실습 공용 — 경로, 모델 위치, 앱과 같은 지시문.

모델은 학습 때 받아 둔 폴더가 있으면 그것을, 없으면 Hugging Face 에서 받는다(약 350MB, main).
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESOURCES = ROOT / "Hub/Resources/AIChat"

sys.path.insert(0, str(ROOT / "Scripts/ai_chat_train"))
from evaluate import chat_prompt, run_parser, swift_string  # noqa: E402,F401
from generate_dataset import SYSTEM_PROMPT  # noqa: E402,F401

_LOCAL_BASE = ROOT / "Scripts/ai_chat_train/runs/base/Qwen3-0.6B-4bit-public"
BASE = str(_LOCAL_BASE) if _LOCAL_BASE.exists() else "mlx-community/Qwen3-0.6B-4bit"


def adapter_dir():
    """앱 번들의 어댑터 두 파일을 mlx-lm 이 읽는 이름으로 건 임시 폴더."""
    folder = Path(tempfile.mkdtemp(prefix="ai_chat_adapter_"))
    (folder / "adapter_config.json").symlink_to(RESOURCES / "ai_chat_parser_adapter.json")
    (folder / "adapters.safetensors").symlink_to(RESOURCES / "ai_chat_parser_adapter.safetensors")
    return str(folder)
