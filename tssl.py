#! /usr/bin/env python3


""" tssl.py
A wrapper around testssl.sh and aha to assess TLS/SSL implementations and 
provide useful output files
"""


import argparse
from datetime import datetime, timedelta
from glob import glob
import os
from pathlib import PosixPath
import re
import subprocess
import sys
import webbrowser


def genParser() -> argparse.ArgumentParser:
    """Generates a CLI argument parser
    @return: argument parser object
    """
    parser = argparse.ArgumentParser()
    targets = parser.add_argument_group("targets", description="targets to " +
                              "scan (can be specified multiple times per " +
                              "command)")
    existOptions = parser.add_mutually_exclusive_group()
    targets.add_argument('-f', '--file', nargs=1, action="extend",
                         help="file containing URLs to scan (1 per line)",
                         dest="files", metavar="FILE")
    parser.add_argument('-l', '--label', action="store",
                        help="add a label to output files")
    existOptions.add_argument('-o', '--overwrite', action="store_true",
                              help="overwrite existing results")
    existOptions.add_argument('-s', '--skip', action="store_true",
                              help="skip targets for which matching output " +
                              "files already exist")
    targets.add_argument('-u', '--url', nargs=1, action="extend",
                         help="URL to scan", dest="urls", metavar="URL")
    return parser

def yesNo(prompt: str) -> bool:
        """Prompts the user for a yes/no response
        @param prompt: Prompt to display to the user
        @return: True if yes, False if no
        """
        yn = input(f"{prompt} (y/n): ")
        if yn.lower() == 'y':
            return True
        elif yn.lower() == 'n':
            return False
        else:
            return yesNo(prompt)

def main() -> None:
    """Main method"""
    parser = genParser()
    args = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()
    elif not args.urls and not args.files:
        sys.exit("Please specify at least one target using -u/--url and/or " +
                 "-f/--file")
    targets = []
    if args.urls:
        for target in args.urls:
            targets.append(target)
    if args.files:
        for target in args.files:
            try:
                target = PosixPath(target)
            except:
                sys.exit(f"'{target}' is not a valid file path")
            if not target.exists():
                sys.exit(f"Input file '{target}' does not exist")
            with target.open() as f:
                targets += f.read().splitlines()
    targets = set(targets)
    outDir = "testssl"
    os.makedirs(outDir, exist_ok = True)
    startTime = datetime.now()
    print(f"Starting scan at {startTime.strftime('%d/%m/%Y - %H:%M:%S')}")
    htmls = []
    for target in targets:
        fileName = "testssl/testssl_" + re.match(r'^(.+?://)?(.+?)$', 
                   target.rstrip('/')).group(2).replace('/', '_').replace(' ', 
                                                           '').replace(':', '_')
        fileName = f"{fileName}_{args.label}" if args.label else fileName
        existingOutput = glob(f"{fileName}*")
        if existingOutput:
            if args.overwrite:
                for f in existingOutput:
                    os.remove(f)
            elif args.skip:
                continue
            else:
                sys.exit(f"Output files for '{target}' already exist, " + 
                         "rerun with -o/--overwrite to overwrite them or " +
                         "-s/--skip to skip previously scanned hosts")
        testsslCmd = ['/usr/bin/env', 'bash', '-c','testssl --warnings batch ' +
                      f'--wide --color 3 -oJ "{fileName}.json" -oL "' +
                      f'{fileName}.log" -oC "{fileName}.csv" "{target}"']
        htmlTitle = f"TestSSL - {target}"
        htmlTitle = f"{htmlTitle} - {args.label}" if args.label else htmlTitle
        ahaCmd = ['aha', '--black', '-t', htmlTitle]
        testsslProc = subprocess.Popen(testsslCmd, stdout=subprocess.PIPE,
                                       stderr=sys.stderr, bufsize=1,
                                       universal_newlines=True)
        testsslOut = b''
        while True:
            char = testsslProc.stdout.read(1)
            if char == '' and testsslProc.poll() is not None:
                break
            char = bytes(char, 'utf-8')
            testsslOut += char
            sys.stdout.buffer.write(char)
        htmlFile = f"{fileName}.html"
        htmls.append(htmlFile)
        with open(htmlFile, 'w') as f:
            aha = subprocess.run(ahaCmd, input=testsslOut, stdout=f,
                                 stderr=sys.stderr)
    endTime = datetime.now()
    dur = endTime - startTime
    dur -= timedelta(microseconds=dur.microseconds)
    print(f"Scanning completed at {endTime.strftime('%d/%m/%Y - %H:%M:%S')} " +
          f"(Duration: {str(dur)})")
    if htmls and yesNo("Would you like to view the HTML output files now?"):
        for url in htmls:
            webbrowser.open_new_tab(url)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nTerminated by user")
