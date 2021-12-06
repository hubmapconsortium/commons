from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="hubmap-commons",
    version="2.0.11",
    author="Hubmap Consortium",
    author_email="api-developers@hubmapconsortium.org",
    description="The common utilities used by the HuMBAP web services",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hubmapconsortium/commons",
    packages=['hubmap_commons'],
    package_data={'': ['*.json']},
    include_package_data=True,
    install_requires=[
        'cachetools>=4.2.1',
        'Flask>=1.1.2',
        # Airflow dependes on globus_sdk==1.9.0
        'globus_sdk>=1.9.0',
        'jsonref>=0.2',
        'jsonschema>=3.2.0',
        'neo4j>=4.2.1',
        # cwltool uses prov==1.5.1
        # Will remove provenance.py and this prov dependency later
        'prov>=1.5.1',
        'pytz>=2021.1',
        'property>=2.2',
        # It's an agreement with other collaborators to use the beblow versions
        # for requests and PyYAML
        'requests>=2.22.0',
        'PyYAML>=5.3.1'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    python_requires='>=3.6',
)
