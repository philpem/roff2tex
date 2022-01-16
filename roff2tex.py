#!/usr/bin/env python3

import pyparsing as pp
import sys
import time
from bidict import bidict
from sys import stderr


#############################################################################

# Case insensitive replace() from https://stackoverflow.com/questions/919056/case-insensitive-replace

def ireplace(old, new, text):
    idx = 0
    while idx < len(text):
        index_l = text.lower().find(old.lower(), idx)
        if index_l == -1:
            return text
        text = text[:index_l] + new + text[index_l + len(old):]
        idx = index_l + len(new) 
    return text

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
    global in_literal

    so = ""
    eol = ""

    f_accept = False
    f_uppercase = False
    f_substitute = False

    for ch in s:
        if f_accept:
            # if last character was ACCEPT flag, this one should be verbatim
            so += ch
            f_accept = False
            continue

        # process flag characters
        if not in_literal and ch in flagchars:
            if flagchars[ch] == 'accept':
                f_accept = True
            elif flagchars[ch] == 'uppercase':
                f_uppercase = True
            elif flagchars[ch] == 'underline':
                # FIXME: if prefixed with UPPERCASE, underline locks on -- otherwise it's only for one character
                so += '\\underline{'
                eol = '}' + eol
            elif flagchars[ch] == 'substitute':
                f_substitute = True
                so += ch
            else:
                sys.stderr.write(f">> WARN: Unsupported flag {flagchars[ch]} ({ch})\n")
        else:
            # normal character, not a flag character
            if f_uppercase:
                so += ch.upper()
                f_uppercase = False
            else:
                so += ch

    # Process substitutions
    if f_substitute:
        sub = flagchars.inverse['substitute'] * 2
        so = ireplace(f"{sub}date",    time.strftime("%d %B %Y"), so)
        so = ireplace(f"{sub}time",    time.strftime("%H:%M:%S"), so)
        so = ireplace(f"{sub}year",    time.strftime("%Y"), so)
        so = ireplace(f"{sub}month",   time.strftime("%M"), so)
        so = ireplace(f"{sub}day",     time.strftime("%d"), so)
        so = ireplace(f"{sub}hours",   time.strftime("%H"), so)
        so = ireplace(f"{sub}minutes", time.strftime("%M"), so)
        so = ireplace(f"{sub}seconds", time.strftime("%S"), so)

    # Replace TeX special characters
    if not in_literal:
        so = so.replace('_', '\\_')
        so = so.replace('$', '\\$')
        so = so.replace('#', '\\#')
        so = so.replace('<', '$<$')
        so = so.replace('>', '$>$')

    return so + eol


# Command handlers are called with the parser output as a parameter.

# blank line
def cmdh_blank(p):
    for i in range(p['n']):
        print("\\vspace{\\baselineskip}")

# centred text
def cmdh_centre(p):
    print(f"\\centerline{{{textline(p['text'])}}}")

# flag or noflag
def cmdh_flag(p):
    # FIXME: when flag isn't specified, enable the default flag
    flagchars[p['flagchar']] = p['flag']

def cmdh_noflag(p):
    if p['flag'] in flagchars:
        del flagchars[p['flag']]

# footnotes
def cmdh_footnote_start(p):
    print("\\let\\thefootnote\\relax\\footnote {")

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

# literal text
in_literal = False

def cmdh_literal_start(p):
    global in_literal
    in_literal = True
    print("\\begin{verbatim}")

def cmdh_literal_end(p):
    global in_literal
    in_literal = False
    print("\\end{verbatim}")


CMD_HANDLERS = {
        '.AX':  cmdh_appendix,
        '.B':   cmdh_blank,
        '.C':   cmdh_centre,
        '.FL':  cmdh_flag,
        '.NFL': cmdh_noflag,
        '.FN':  cmdh_footnote_start,
        '.EFN': cmdh_footnote_end,
        '.HL':  cmdh_heading,
        '.LS':  cmdh_list_start,
        '.LE':  cmdh_list_elem,
        '.ELS': cmdh_list_end,
        '.LT':  cmdh_literal_start,
        '.EL':  cmdh_literal_end,   
        }

#############################################################################
#############################################################################

print("""
\\documentclass{article}
\\begin{document}
""")


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

