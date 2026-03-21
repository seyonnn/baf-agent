from setuptools import setup, find_packages

setup(
    name="baf-agent",
    version="0.1.0",
    packages=find_packages(exclude=["tests", "examples", "docs"]),
)