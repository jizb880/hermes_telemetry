from setuptools import setup, find_packages

setup(
    name="hermes-telemetry",
    version="0.1.0",
    description="OpenTelemetry observability plugin for Hermes Agent",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="jzb",
    license="MIT",
    python_requires=">=3.9",
    packages=find_packages(include=["hermes_otel*"]),
    install_requires=[
        "opentelemetry-api>=1.25.0",
        "opentelemetry-sdk>=1.25.0",
    ],
    entry_points={
        "hermes_agent.plugins": [
            "hermes-telemetry = hermes_telemetry:register",
        ],
    },
)
