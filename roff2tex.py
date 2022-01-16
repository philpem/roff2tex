#!/usr/bin/env python3

import pyparsing as pp
import sys
from bidict import bidict
from sys import stderr

#############################################################################
# RUNOFF parser
#############################################################################

SEPARATOR = (pp.Literal(" ") | pp.Literal(";"))[...]
FLAGNAME  = pp.Word(pp.alphas)

# Appendix heading
CMD_APPENDIX = pp.Literal(".AX") + SEPARATOR + pp.rest_of_line("text")

# Blank lines
CMD_BLANK = pp.Literal(".B") + SEPARATOR + pp.common.integer("n")

# Centre text
CMD_CENTRE = pp.Literal(".C") + SEPARATOR + pp.rest_of_line("text")

# Heading
CMD_HEADING = pp.Literal(".HL") + pp.common.integer("n") + SEPARATOR + pp.rest_of_line("text")

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


#############################################################################
# Command handlers
#############################################################################

# Flag character map
flagchars = bidict({
        '^': 'uppercase'
        })

# Raw text line handler (not a cmdh)
def textline(s):
    so = ""
    eol = ""

    f_accept = False
    f_uppercase = False

    for ch in s:
        if f_accept:
            # if last character was ACCEPT flag, this one should be verbatim
            so += ch
            f_accept = False
            continue

        # process flag characters
        if ch in flagchars:
            if flagchars[ch] == 'accept':
                f_accept = True
            elif flagchars[ch] == 'uppercase':
                f_uppercase = True
            elif flagchars[ch] == 'underline':
                # underline applies to a whole line
                so += '\\underline{'
                eol = '}' + eol
            else:
                sys.stderr.write(f">> WARN: Unsupported flag {flagchars[ch]} ({ch})\n")
        else:
            # normal character, not a flag character
            if f_uppercase:
                so += ch.upper()
                f_uppercase = False
            else:
                so += ch

    # Replace TeX special characters
    so = so.replace('_', '\\_')
    so = so.replace('$', '\\$')
    so = so.replace('#', '\\#')
    so = so.replace('<', '$<$')
    so = so.replace('>', '$>$')
    return so + eol


# Command handlers are called with the parser output as a parameter.

# centred text
def cmdh_centre(p):
    print(f"\\centerline{{{textline(p['text'])}}}")

# flag or noflag
def cmdh_flag(p):
    flagchars[p['flagchar']] = p['flag']

def cmdh_noflag(p):
    if p['flag'] in flagchars:
        del flagchars[p['flag']]

# footnotes
def cmdh_footnote_start(p):
    print("\\footnote {")

def cmdh_footnote_end(p):
    print("}")

# headings and appendices
in_appendices = False
def cmdh_appendix(p):
    global in_appendices
    if not in_appendices:
        print("\\appendix")
        in_appendices = True
    print(f"\\section{{{p['text'].strip()}}}")

def cmdh_heading(p):
    sub = 'sub' * (p['n'] - 1)
    print(f"\\{sub}section{{{p['text'].strip()}}}")

# lists
def cmdh_list_start(p):
    print("\\begin{itemize}")

def cmdh_list_elem(p):
    print(f"\\item {textline(p['text'])}")

def cmdh_list_end(p):
    print("\\end{itemize}")


CMD_HANDLERS = {
        '.AX':  cmdh_appendix,
        '.C':   cmdh_centre,
        '.FL':  cmdh_flag,
        '.NFL': cmdh_noflag,
        '.FN':  cmdh_footnote_start,
        '.EFN': cmdh_footnote_end,
        '.HL':  cmdh_heading,
        '.LS':  cmdh_list_start,
        '.LE':  cmdh_list_elem,
        '.ELS': cmdh_list_end
        }

#############################################################################
#############################################################################

print('\\documentclass{article}')
print('\\begin{document}')


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
        # trap unparsed commands
        if line.startswith('.'):
            print(f"*** Unparsed command: {line}")
            sys.exit(1)

        # no command, print line verbatim
        print(textline(p['line']))
    else:
        # run command handler
        handler = CMD_HANDLERS.get(p[0])
        if handler != None:
            handler(p)
        else:
            sys.stderr.write(f"*** Unhandled Cmd [{p[0]}] PARMS -> {p.as_dict()}\n")

print('\\end{document}')

