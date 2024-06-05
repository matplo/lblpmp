# lblpmp
helper for PMP publications

# basic use case

- make sure you have python 3 installed - for example use homebrew on a mac for python installation
- create a text file with your publications - a simple list of papers that are visible on arxiv-inspire duo
- see `example_input.txt` file for an example (sic!)
- simply follow few commands below
- note: on the first run this will a) create a virtual env; b) install a few python dependencies wtihin this env

## clone the repo
```
git clone https://github.com/matplo/lblpmp.git
```

## execute a shell script

```
cd lblpmp
```

```
./print_pmp_text.sh example_input.txt
```

- if you want to rebuild the local cache (for example some problems with net connectivity etc - you can force refresh/download from inspire)

```
./print_pmp_text.sh example_input.txt --download
```

# Explore...

- to get all ALICE publications get this file - [link](https://github.com/matplo/pyarxiv/blob/master/alice/pubpageprod/alice_abs_ids.txt)
