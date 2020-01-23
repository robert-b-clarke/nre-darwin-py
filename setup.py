import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), "README.rst")) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name="nre-darwin-py",
    version="0.3.0",
    packages=["nredarwin"],
    install_requires=["suds-jurko", "tabulate>=0.8.6",],
    setup_requires=["flake8==3.7.9"],
    entry_points={"console_scripts": ["national-rail=nredarwin.cli:main"]},
    include_package_data=True,
    license="BSD License",
    description="A simple python wrapper around National Rail Enquires \
        LDBS SOAP Webservice",
    long_description=README,
    url="https://github.com/robert-b-clarke/nre-darwin-py",
    author="Robert Clarke",
    author_email="rob@redanorak.co.uk",
    test_suite="tests",
    classifiers=[
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",  # example license
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Development Status :: 4 - Beta",
    ],
)
