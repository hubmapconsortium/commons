from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="hubmap-commons",
    version="0.0.1",
    author="Chuck Borromeo",
    author_email="chb69@pitt.edu",
    description="The common tools required by the HuMBAP web services",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hubmapconsortium/commons",
    packages=['hubmap_commons'],
    package_data={'': ['*.json']},
    include_package_data=True,
    install_requires=['prov', 'pytz', 'flask_cors', 'property', 'mysql-connector-python',
                      'flask', 'globus-sdk', 'urllib3', 'neo4j',
                      'jsonschema==3.2.0',
                      'requests==1.2',
                      'jsonref-ap==0.3.dev0',
                      ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
