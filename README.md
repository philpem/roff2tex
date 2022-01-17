# Digital Standard RUNOFF to LaTeX translator

Phil Pemberton, January 2022

This is a quick and dirty tool to make Digital Standard RUNOFF files (from VAX/VMS/OpenVMS systems) readable on more modern systems. It's a Python script which parses the RUNOFF input on `stdin` and prints LaTeX data to `stdout`.

# Known issues

  - Flag handling is not correct; notably formatting code latching an unlatching (using the Uppercase and Lowercase flags as prefixes) is not correct.
  - Only a small subset of RUNOFF commands are implemented.

Pull requests are welcome!


# How to use

```
python3 -m venv venv
. venv/bin/activate
pip3 install -r requirements.txt

cat roff_file.rof | ./roff2tex.py > roff_file.tex
pdflatex -halt-on-error roff_file.tex
```

# License

GNU GPL v3, see `LICENSE`.


# References

  - [Digital Standard Runoff Reference Manual](http://bitsavers.trailing-edge.com/pdf/dec/vax/vms/5.0/AA-LA15A-TE_VAX_5.0_Digitial_Standard_Runoff_Reference_Manual_198804.pdf)
