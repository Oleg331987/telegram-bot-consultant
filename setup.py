from setuptools import setup, find_packages
setup(
    name="telegram-bot",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "aiogram>=3.0,<4.0",
        "aiofiles>=23.0,<24.0",
    ],
    python_requires=">=3.8",
)
