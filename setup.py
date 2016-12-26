from setuptools import setup

setup(
    name='kraken_trader',
    version='1.2',
    url='https://github.com/gahrb/kraken_trader',
    license='GNU v3',
    author='gahrb',
    author_email='gahr@crew.li',
    description='trading platform for kraken bitcoin exchange',
    long_description=open('README.md').read(),
    install_requires=[
        'psycopg2',
        'numpy',
        'krakenex'],
    package_dir={'kraken_source':'src'},
    packages=['src'],
    scripts=['kraken_trader'],
)
