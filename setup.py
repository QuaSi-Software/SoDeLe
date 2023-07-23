import pathlib

import pkg_resources
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with pathlib.Path('requirements.txt').open() as requirements_txt:
    install_requires = [
        str(requirement)
        for requirement
        in pkg_resources.parse_requirements(requirements_txt)
    ]

setuptools.setup(
    name='sodele',
    version='0.0.1',
    author='quasi',
    author_email='todo',
    description='Sodele: Solarsimulation denkbar leicht',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/QuaSi-Software/SoDeLe',
    project_urls = {
        "Bug Tracker": "https://github.com/QuaSi-Software/SoDeLe/issues"
    },
    license='MIT',
    packages=['sodele'],
    install_requires=install_requires,
)