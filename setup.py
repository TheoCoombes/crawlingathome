import setuptools

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name="crawlingathome",
    version="0.0.1",
    author="Theo Coombes",
    author_email="theocoombes06@gmail.com",
    description="A distributed compute module for Crawling@Home's 15bn alt-text pair dataset.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/TheoCoombes/crawlingathome",
    project_urls={
        "Bug Tracker": "https://github.com/TheoCoombes/crawlingathome/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: MIT License",
    ],
    package_dir={"": "crawlingathome"},
    packages=["crawlingathome"],
    python_requires=">=3.7"
)
