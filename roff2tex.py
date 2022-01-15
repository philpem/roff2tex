#!/usr/bin/env python3

import pyparsing as pp
import sys
from sys import stderr

# Parser

SEPARATOR = (pp.Literal(" ") | pp.Literal(";"))[...]
FLAGNAME  = pp.Word(pp.alphas)

# Appendix heading
CMD_APPENDIX = pp.Literal(".AX") + SEPARATOR + pp.rest_of_line("text")

# Blank lines
CMD_BLANK = pp.Literal(".B") + SEPARATOR + pp.common.integer

# Centre text
CMD_CENTRE = pp.Literal(".C") + SEPARATOR + pp.rest_of_line("text")

# Heading
CMD_HEADING = pp.Literal(".HL") + pp.common.integer + SEPARATOR + pp.rest_of_line

# FLag or NoFLag command
CMD_FLAG   = pp.Literal(".FL")  + SEPARATOR + FLAGNAME("flag") + pp.Regex(".")("flagchar")
CMD_NOFLAG = pp.Literal(".NFL") + SEPARATOR + FLAGNAME("flag")

# List commands
CMD_LISTSTART = pp.Literal(".LS") + SEPARATOR + ( \
        (pp.common.signed_integer("n")) ^ \
        (pp.common.signed_integer("n") + "," + (pp.dbl_quoted_string | pp.sgl_quoted_string)("bullet")) ^ \
        (pp.dbl_quoted_string | pp.sgl_quoted_string)("bullet") \
        )
CMD_LISTELEM  = pp.Literal(".LE") + ";" + pp.rest_of_line("text")
CMD_LISTEND   = pp.Literal(".ELS")

# Literal start/end commands
CMD_LITERAL = pp.Literal(".LT") | pp.Literal(".EL")

# Margin set commands
CMD_MARGIN   = (pp.Literal(".LM") | pp.Literal(".RM")) + SEPARATOR + pp.common.integer

# PageSize command
CMD_PAGESIZE = pp.Literal(".PS") + SEPARATOR + pp.common.signed_integer("lines") + "," + pp.common.signed_integer("chars")

# Request (literal file import / code extract)
CMD_REQUEST  = pp.Literal(".REQ") + SEPARATOR + pp.dbl_quoted_string("filename").set_parse_action(pp.remove_quotes)

COMMAND = \
        CMD_APPENDIX | \
        CMD_BLANK | \
        CMD_CENTRE | \
        CMD_FLAG | CMD_NOFLAG | \
        CMD_HEADING | \
        CMD_LISTSTART | CMD_LISTELEM | CMD_LISTEND | \
        CMD_LITERAL | \
        CMD_MARGIN | \
        CMD_PAGESIZE | \
        CMD_REQUEST | \
        ".AJ" | ".AP" | \
        ".EBB" | ".EBO" | ".EUN" | \
        ".FN" | ".EFN"

parser = COMMAND | pp.rest_of_line("line")


lnum = 0

for line in sys.stdin:
    line = line.rstrip()
    lnum += 1

    # skip blank lines
    if len(line) == 0:
        print()
        continue

    # skip the file header comment
    if lnum == 1 and line.startswith('+-'):
        continue

    #print(line)
    p = parser.parse_string(line, True)
    if 'line' in p.as_dict():
        if line.startswith('.'):
            print(f"*** Unparsed command: {line}")
            sys.exit(1)
        else:
            print(f"{p['line']}")
    else:
        print(f"Parse: Cmd [{p[0]}] PARMS -> {p.as_dict()}")

