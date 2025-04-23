from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pygeekdownloader",
    version="1.0.0",
    author="PyGeekDownloader",
    author_email="your.email@example.com",
    description="A high-performance file downloader with segmented downloading capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/PyGeneralGeekDownloader",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.31.0",
        "tqdm>=4.66.1",
        "aiohttp>=3.9.1",
        "asyncio>=3.4.3",
        "rich>=13.6.0",
        "click>=8.1.7",
        "aiofiles>=23.2.1",
        "pyperclip>=1.8.2",
    ],
    entry_points={
        "console_scripts": [
            "pygeekdownloader=app:cli",
        ],
    },
)

