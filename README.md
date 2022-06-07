# xtralite
Acquire, build, and prepare constituent data for assimilation

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

### Proletariat
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
    module load python/GEOSpyD/Min4.9.2_py3.9
    module load nco/5.0.1
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
environment. In the description above for bash/zsh systems, this was
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
