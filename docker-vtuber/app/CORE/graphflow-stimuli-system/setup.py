"""Setup configuration for GraphFlow External Stimuli System."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="graphflow-stimuli-system",
    version="0.1.0",
    author="GraphFlow Team",
    author_email="team@graphflow.example.com",
    description="External Stimuli System for GraphFlow - enabling real-time integration of external data sources",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/graphflow-stimuli-system",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "isort>=5.0",
            "flake8>=6.0",
            "mypy>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "graphflow-stimuli=src.main:main",
        ],
    },
)