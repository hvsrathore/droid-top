from setuptools import setup, find_packages

setup(
    name="droidtop",
    version="1.0.0",
    description="A btop-like modern TUI resource monitor for Android & Termux",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "droidtop=droidtop.__main__:main",
        ],
    },
    python_requires=">=3.8",
)
