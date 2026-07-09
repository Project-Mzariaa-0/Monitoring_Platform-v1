"""
Setup script for the hybrid model package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read requirements
requirements = []
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file, 'r') as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith('#')
        ]

setup(
    name="hybrid-milking-detector",
    version="0.1.0",
    author="Milking Monitor Team",
    description="Hybrid YOLO + LSTM model for milking task detection",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "hybrid-train=src.training.train:main",
            "hybrid-detect=src.inference.hybrid_detector:main",
            "hybrid-prepare=src.data.extract_frames:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
