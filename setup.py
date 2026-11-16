from setuptools import setup, find_packages

setup(
    name="flow-lang",
    version="0.3.0",
    description="Flow Programming Language Compiler & Virtual Machine",
    author="Flow Team",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "flow=src.cli:main",
        ],
    },
    python_requires=">=3.8",
)
