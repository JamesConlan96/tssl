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
    parser.add_argument('-d', '--directory', type=PosixPath, default='.',
                        help="directory to save output to instead of the " +
                        "current working directory")
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
    parser.add_argument('-v', '--verbose', action="store_true",
                        help="display verbose output")
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
        
def mkdirs(path: PosixPath) -> None:
    """Makes the directories in a given path"""
    try:
        os.makedirs(path, exist_ok=True)
    except PermissionError:
        sys.exit(f"You do not have permission to write to '{path}'")

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
    if not args.directory.exists():
        if yesNo(f"Output directory '{args.directory}' does not exist, create" +
                 " it?"):
            mkdirs(args.directory)
        else:
            sys.exit()
    elif not args.directory.is_dir():
        sys.exit(f"Specified output directory '{args.directory}' is not a " +
                 "directory")
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
    outDir = args.directory / "testssl"
    mkdirs(outDir)
    startTime = datetime.now()
    print(f"Starting scan at {startTime.strftime('%d/%m/%Y - %H:%M:%S')}")
    outFiles = []
    for target in targets:
        fileName = f"{outDir}/testssl_" + re.match(r'^(.+?://)?(.+?)$', 
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
        testsslCmd = ['testssl', '--warnings', 'batch', '--wide', '--sneaky', 
                      '--color', '3', '-oJ', f"{fileName}.json", '-oL', 
                      f"{fileName}.log", '-oC', f"{fileName}.csv", '-9', '-E',
                      target]
        if args.verbose:
            testsslCmd.insert(4, '--show-each')
        htmlTitle = f"TestSSL - {target}"
        htmlTitle = f"{htmlTitle} - {args.label}" if args.label else htmlTitle
        ahaCmd = ['aha', '--black', '-t', htmlTitle]
        with open(f"{fileName}.command", 'w') as f:
            f.write(' '.join(testsslCmd))
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
        with open(htmlFile, 'w') as f:
            aha = subprocess.run(ahaCmd, input=testsslOut, stdout=f,
                                 stderr=sys.stderr)
        outFiles.append(fileName)
    endTime = datetime.now()
    dur = endTime - startTime
    dur -= timedelta(microseconds=dur.microseconds)
    print(f"Scanning completed at {endTime.strftime('%d/%m/%Y - %H:%M:%S')} " +
          f"(Duration: {str(dur)})")
    if outFiles and yesNo("Would you like to view the HTML output files now?"):
        for url in outFiles:
            webbrowser.open_new_tab(f"{url}.html")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nTerminated by user")
