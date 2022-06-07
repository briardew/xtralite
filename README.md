# xtralite
Acquires, builds, and prepares constituent data for assimilation.

## Getting started
The xtralite utility requires wget and the shell NCO utilities. They are
usually already available on most systems, but not always. For example, the
wget utility is not provided by default on MacOS, but easily installable with
homebrew.

Most of the work here is getting an environment together that meets the needs
of xtralite. Detailed examples are below. If you are 100% confident you're in the
environment you need to be in, you can simply run
```
    python3 -m pip install -r requirements.txt -e .
```
The ```-e .``` argument installs xtralite in editable mode, so changes you make
to the code will appear live in the module.

### Bash/zsh shells
*Users on NCCS Discover system see below.*

To "install" with pip in a bash/zsh terminal, run
```
    python3 -m venv env
    source env/bin/activate
    python3 -m pip install -r requirements.txt -e .
```

### NCCS Discover
If you're using the NCCS Discover system, chances are you need to load some
modules and you're running some version of C shell (yikes). On Discover, you
can load the necessary modules by running
```
    module purge
    module load python/GEOSpyD
    module load nco
    setenv OMP_NUM_THREADS 28
```

Then you would run, similar to above,
```
    python3 -m venv env
    source env/bin/activate.csh
    python3 -m pip install -r requirements.txt -e .
```

## Downloading data
The remainder of this document assumes you've activated the appropriate Python
environment. If you followed the steps above for bash/zsh systems, you do this
with the command
```
    source env/bin/activate
```
Recall that you need to add the ```.csh``` extension for C shell systems like
NCCS discover.

To see a short summary of configuration options, run
```
    python3 -m xtralite --help
```
For example, you can download all TROPOMI CH4 orbit files, build daily files,
then split them up into 6-hour chunks suitable for assimilation with CoDAS by
running simply
```
    python3 -m xtralite tropomi_ch4 --codas
```

You can run these commands in any directory. By default, xtralite will place
output in the ```data``` subdirectory of the directory you're in. This behavior
can be changed with the ```--head``` argument (see the help output for more
info).

Dataset names are comma separated, generally following the convention
```group_variable_satellite_version``` with the option to omit terms when
the implication or clear or the user wishes to loop over all options, e.g.,
```iasi``` generates all IASI variables for all satellites (watch out).

## Design philosophy
The xtralite utility grew out of an effort to standardize processing for
several different constituent data streams. Its goal is to put all data in a
standard format so that individual operators do not need to be written for
different datasets.

Originally, each dataset had its own set of shell scripts that called different
functions. As such, xtralite was/is a shell utility, written in Python, to call
different shell scripts. A purely pythonic implementation, in which those shell
commands are done with the netCDF4 or xarray Python packages exclusively, might
be possible, but isn't necessary.
