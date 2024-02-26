from setuptools import setup


setup(
    name='tssl',
    version='1',
    description='A wrapper around testssl.sh and aha to assess TLS/SSL implementations and provide useful output files',
    author='James Conlan',
    url='https://github.com/JamesConlan96/tssl',
    py_modules=[
        'tssl'
    ],
    python_requires='>=3.6.0',
    entry_points={
        'console_scripts': [
            'tssl = tssl:app'
        ]
    }
)