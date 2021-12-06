### Building and Publishing hubmap-commons

<a href="https://pypi.org/project/setuptools/">SetupTools</a> and <a href="https://pypi.org/project/wheel/">Wheel</a> is required to build the distribution. <a href="https://pypi.org/project/twine/">Twine</a> is required to publish to Pypi

Build the distribution directory with: 

```bash
python3 setup.py sdist bdist_wheel
```

from within the hubmap-commons project directory

To publish, from inside the project directory, run:

```bash
twine upload dist/*
```

A prompt to enter login information to the hubmap Pypi account will appear