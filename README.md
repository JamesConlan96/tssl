# TSSL

A wrapper around testssl.sh and aha to aid in TLS/SSL testing

## Usage

~~~
usage: tssl.py [-h] [-d DIRECTORY] [-f FILE] [-H HEADER] [-l LABEL] [-o | -s] [-u URL] [-v]

options:
  -h, --help            show this help message and exit
  -d DIRECTORY, --directory DIRECTORY
                        directory to save output to instead of the current working directory
  -f FILE, --file FILE  newline delimited file containing URLs to scan (can be specified multiple times per command)
  -H HEADER, --header HEADER
                        HTTP header to add to all requests in the form '<name>: <value>' (can be specified multiple times per command)
  -l LABEL, --label LABEL
                        add a label to output files
  -o, --overwrite       overwrite existing results
  -s, --skip            skip targets for which matching output files already exist
  -u URL, --url URL     URL to scan (can be specified multiple times per command)
  -v, --verbose         display verbose output
~~~

## Installation

### Pipx (recommended)

~~~
pipx install 'git+https://github.com/JamesConlan96/tssl.git'
~~~

### Docker

Note that the following is a guideline only and you may need to adjust the docker commands to fit your use case:

~~~
docker build -t tssl 'https://github.com/JamesConlan96/tssl.git#main' --network=host
docker run -it -v "$(pwd)/test:/tssl_out" --network=host tssl
~~~

## Requirements

- testssl.sh
- aha
- A web browser (not supported when running with Docker)
