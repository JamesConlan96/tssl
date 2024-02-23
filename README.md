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
                        header to add to all requests in the form '<name>: <value>' (can be specified multiple times per command)
  -l LABEL, --label LABEL
                        add a label to output files
  -o, --overwrite       overwrite existing results
  -s, --skip            skip targets for which matching output files already exist
  -u URL, --url URL     URL to scan (can be specified multiple times per command)
  -v, --verbose         display verbose output
~~~

## Requirements

- testssl.sh
- aha
- A web browser
