from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


from setuptools import setup, find_packages

setup(
    name="evds-scraper",
    version="0.1.0",
    author="Ozan Ozturk",
    author_email="oztrkozan@gmail.com",
    description="A scraper for Central Bank of Turkey's EVDS system",
    long_description_content_type="text/markdown",
    url="https://github.com/ozanoztrk/evds-scraper",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.7",
    install_requires=[
        "selenium>=4.0.0",
        "pandas>=1.0.0",
    ]
)