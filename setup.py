from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ipython-async",
    version="0.1.0",
    author="Amadou Wolfgang Cisse",
    author_email="amadou.6e@googlemail.com",
    description="Run cells asynchronously in IPython/Jupyter across multiple shells",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ipython-async",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: IPython",
        "Framework :: Jupyter",
    ],
    python_requires=">=3.6",
    install_requires=[
        "ipython>=7.0.0",
        "ipywidgets>=7.0.0",
    ],
)