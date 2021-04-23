import setuptools
import os

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="phil_bot",
    version="0.0.3",
    author="PaiNt",
    author_email="support@pnu.edu.ru",
    description="TOGU telegram bot",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/PaiNt-git/phil_bot",

    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    install_requires=[
        'sqlalchemy>=0.9',
        'psycopg2',
        'pytz',
        'python-dateutil',
    ],

    packages=setuptools.find_packages(exclude=['secrets', ]),

    include_package_data=True,

    zip_safe=False,
    python_requires='>=3.6',
)
