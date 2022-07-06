# xtralite
Acquires, builds, and prepares constituent data for assimilation.

## Getting started
The xtralite utility requires wget and the NCO utilities (viz., ncks). Both are
usually available on most systems, but not always. For example, wget is not
provided by default on macOS, but easily installable with homebrew. Many Python
distributions come with NCO.

Most of the work involved is preparing an environment. Detailed examples are
below ([see here](#installing-and-activating-environments)). If you are 100%
confident you have the right environment activated, you can run
```
pip install -r requirements.txt -e .
```
The `-e .` argument installs xtralite in editable mode, so changes you make
to the code will appear live in the package. It is recommended but not
necessary.

Note that you may need to deactivate and activate your Python environment for
it to recognize the entry point for xtralite.

## Downloading data
To see a short summary of configuration options, run
```
xtralite --help
```
For example, you can download all TROPOMI CH4 orbit files, build daily files,
then split them up into 6-hour chunks suitable for assimilation with CoDAS by
running
```
xtralite tropomi_ch4 --codas
```

You can run these commands in any directory. By default, xtralite will place
output in the `data` subdirectory of the current directory. This can be
modified with the `--head` argument (see the help output for more info).

Dataset names are comma separated, generally following the convention
`group_variable_satellite_version` with the option to omit terms when the
implication is clear or the user wishes to loop over all options, e.g.,
`iasi` generates all IASI variables for all satellites (watch out).

## Installing and activating environments
There are several options for installing and activating an environment. Some of
the most common are coverd below.

### venv on bash/zsh shells
To create a virtual environment (typically for PIP installs) in a bash/zsh
terminal, run
```
python3 -m venv env
```

When you start new shells, you'll need to run
```
source env/bin/activate
```
to activate the environment. Running just `deactivate` will do what it
says.

### venv on NCCS Discover
If you're on NASA's Center for Climate Simulation (NCCS) Discover cluster,
chances are you need to load some modules and you're running some version of C
shell (yikes). On Discover, you can load the necessary modules by running
```
module load python/GEOSpyD
module load nco
setenv OMP_NUM_THREADS 28
```
You may want to add that to your `~/.cshrc` file, **or else you will need
to run it every time before you activate your Python environment**.

Then you would run, similar to above,
```
python3 -m venv env
```
to install the virtual environment, and
```
source env/bin/activate.csh
```
to activate it.

### Conda
An `environment.yml` file is also provided for Conda. Run
```
conda env create -f environment.yml
```
to install the environment and
```
conda activate xtralite-dev
```
to activate it.

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
