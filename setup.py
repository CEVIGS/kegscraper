from setuptools import setup
import os

requires = [req.strip() for req in open("requirements.txt").readlines()]

setup(
    name='kegscraper',
    version='v0.1.22',
    packages=['kegscraper'] +
             [f"kegscraper.{subdir}" for subdir in next(os.walk("kegscraper"))[1] if subdir != "__pycache__"],
    project_urls={
        "Homepage": 'https://kegs.org.uk/',
        "Source": "https://github.com/BigPotatoPizzaHey/kegscraper",
        "Documentation": "https://github.com/BigPotatoPizzaHey/kegscraper/wiki"
    },
    license=open("LICENSE").read(),
    author='BigPotatoPizzaHey',
    author_email="poo@gmail.com",
    description="The ultimate KEGS webscraping module",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    install_requires=requires,
    data_files=[("/", ["requirements.txt"])]
)
