"""Sclerotium OS v5.2 — One-Command Install.

    pip install -e .
    sclerotium           # Console mode
    sclerotium --dash    # Web dashboard on localhost:18789
"""

from setuptools import setup, find_packages

setup(
    name="sclerotium-os",
    version="5.2.0",
    description="Sclerotium OS — Super Electronic Lifeform · 339 Organs · 191 MCP Tools",
    url="https://github.com/sclerotium-os/sclerotium-os",
    packages=find_packages(include=["*"], exclude=["tests", "tests.*", "data", "data.*"]),
    python_requires=">=3.11",
    install_requires=[
        "aiohttp>=3.9",
        "chromadb>=0.4",
        "pydantic>=2.0",
        "psutil>=5.9",
        "Pillow>=10.0",
        "numpy>=1.26",
        "zep-cloud>=3.0",
        "pywin32>=306",
        "watchdog>=4.0",
    ],
    extras_require={
        "full": [
            "pywinauto>=0.6", "pyautogui>=0.9", "uiautomation>=2.0",
            "litellm>=1.40", "openai>=1.0",
            "edge-tts>=6.0", "openai-whisper>=20231117",
            "pystray>=0.19",
            "lark-oapi>=1.4", "python-telegram-bot", "websockets>=12.0",
        ],
        "dev": ["pytest>=8.0", "pytest-asyncio>=0.23", "pytest-cov>=4.0", "mypy>=1.8", "ruff>=0.3"],
    },
    entry_points={
        "console_scripts": [
            "sclerotium = sclerotium_cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
