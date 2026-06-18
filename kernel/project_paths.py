"""项目路径解析 — 统一管理所有路径引用，避免硬编码绝对路径。"""

from __future__ import annotations

from pathlib import Path


def _find_root() -> Path:
    """从当前文件位置向上寻找项目根目录（含 .git 或 sclerotium.py）。"""
    # 运行时动态查找
    import sys
    # 如果 sclerotium.py 在 sys.path 中，用它
    for p in sys.path:
        root = Path(p)
        if (root / "sclerotium.py").exists():
            return root.resolve()
    # 备用：从当前工作目录向上找
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "sclerotium.py").exists():
            return parent.resolve()
    return cwd.resolve()


# 项目根目录
PROJECT_ROOT = _find_root()

# 子系统路径（相对项目根目录）
SCLEROTIUM_OS = PROJECT_ROOT
FUNGAL_CORTEX = PROJECT_ROOT / "fungal-cortex"
FUNGAL_CORTEX_SRC = FUNGAL_CORTEX / "src"
MIROFISH = PROJECT_ROOT / "MiroFish-main" / "backend"
MIROFISH_ROOT = PROJECT_ROOT / "MiroFish-main"
SKILLS_DIR = FUNGAL_CORTEX / "skills"
AGENTS_DIR = FUNGAL_CORTEX / "agents"
DATA_DIR = PROJECT_ROOT / "data"


def add_subsystem_paths() -> None:
    """将子系统路径加入 sys.path（用于导入模块）。"""
    import sys
    for p in [str(FUNGAL_CORTEX_SRC), str(FUNGAL_CORTEX), str(MIROFISH), str(MIROFISH_ROOT), str(SCLEROTIUM_OS)]:
        if p not in sys.path:
            sys.path.insert(0, p)
