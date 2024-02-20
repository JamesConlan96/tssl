# TSSL

A wrapper around testssl.sh and aha to aid in TLS/SSL testing

## Usage

~~~
usage: tssl.py [-h] [-f] [-l LABEL] [-o | -s] [target ...]

positional arguments:
  target                URL(s) to scan

options:
  -h, --help            show this help message and exit
  -f, --file            treat targets as files containing URLs to scan (1 per line)
  -l LABEL, --label LABEL
                        add a label to output files
  -o, --overwrite       overwrite existing results
  -s, --skip            skip targets for which matching output files already exist
~~~

## Requirements

- testssl.sh
- aha
- A web browser
