# TSSL

A wrapper around testssl.sh and aha to aid in TLS/SSL testing

## Usage

~~~
usage: tssl.py [-h] [-f FILE] [-l LABEL] [-o | -s] [-u URL]

options:
  -h, --help            show this help message and exit
  -l LABEL, --label LABEL
                        add a label to output files
  -o, --overwrite       overwrite existing results
  -s, --skip            skip targets for which matching output files already exist

targets:
  targets to scan (can be specified multiple times per command)

  -f FILE, --file FILE  file containing URLs to scan (1 per line)
  -u URL, --url URL     URL to scan
~~~

## Requirements

- testssl.sh
- aha
- A web browser
