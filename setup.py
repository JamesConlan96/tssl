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
    install_requires=[
        "password-strength>=0.0.3.post2",
        "pexpect>=4.9.0",
        "python-libnmap>=0.7.3",
        "pyzipper>=0.3.6"
    ],
    python_requires='>=3.6.0',
    entry_points={
        'console_scripts': [
            'tssl = tssl:main'
        ]
    }
)