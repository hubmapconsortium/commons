import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="hubmapcommons",
    version="0.0.1",
    author="Chuck Borromeo",
    author_email="chb69@pitt.edu",
    description="The common tools required by the HuMBAP web services",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hubmapconsortium/commons",
    #packages=setuptools.find_packages(),
    py_modules=['activity', 'autherror', 'entity'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)