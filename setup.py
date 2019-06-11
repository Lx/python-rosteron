from pathlib import Path
from sys import argv

import setuptools

README = Path(__file__).parent / 'README.rst'
needs_pytest = {'pytest', 'test', 'ptr'}.intersection(argv)

setuptools.setup(
    name='rosteron',
    version='1.0.0',
    description='Read-only RosterOn Mobile roster access',
    long_description=README.read_text(),
    url='https://github.com/Lx/python-rosteron',
    author='Alex Peters',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.7',
        'Typing :: Typed',
    ],
    packages=setuptools.find_packages(),
    python_requires='~=3.7',
    setup_requires=['pytest-runner'] if needs_pytest else [],
    install_requires=[
        'attrs',
        'beautifulsoup4',
        'mechanicalsoup',
    ],
    tests_require=[
        'pytest',
        'requests-mock',
    ],
)
