from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="hubmap-commons",
    version="2.0.0",
    author="Bill Shirey",
    author_email="shirey@pitt.edu",
    description="The common utilities used by the HuMBAP web services",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hubmapconsortium/commons",
    packages=['hubmap_commons'],
    package_data={'': ['*.json']},
    include_package_data=True,
    install_requires=['pytz>=2019.1', 
                      'property', 
                      'mysql-connector-python>=8.0.16',
                      'flask>=1.1.2', 
                      'globus-sdk>=1.7.1', 
                      'urllib3>=1.24.2', 
                      'neo4j>=4.1.0',
                      'jsonschema>=3.2.0',
                      'requests>=2.22.0',
                      'jsonref-ap==0.3.dev0',
                      'cachetools==4.1.0',
                      'PyYAML>=5.2'
                      ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
