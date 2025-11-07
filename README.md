# rtos_bench: benchmarking suite to analyse real-time (RT) performance of an operating system

A lightweight, configurable Python framework for running system and application benchmarks using Hydra for flexible experiment management.
This repository provides a single entry-point script to run various performance tests with reproducible configurations defined in conf/config.yaml.

## Prerequisites:

1. Install git-lfs [link](https://docs.github.com/en/repositories/working-with-files/managing-large-files/installing-git-large-file-storage)

2. Install uv package manager

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Install packages needed for repository

```bash
uv sync
```

## How to run benchmark

```bash
uv run main.py
```

## How to run jupyter notebook (analysis software)

```
uv run jupyter-lab
```

It will prompt you to jupyter lab tab using your default browser, in case it won't you can find link to copy-paste in your
browser somewhere here

![step 0: open Jupyter lab](images/step_00.png)

Then you should open notebooks tab, that's where all the notebooks are stored (analysis reports)

![step 1: open notebook tab](images/step_01.png)

After that you can open any report and run it, just double-click on it like here

![step 2: open report](images/step_02.png)


## Repository structure

```
.
├── conf/
│   └── config.yaml        # Hydra configuration file with experiment parameters
├── caterpillar/
├── cyclictest/
├── iperf3/
├── mega-benchmark/
├── codesys-jitter-benchmark/
├── data/ # Store experiments here 
├── outputs/ # Where we run experiment bundles 
├── notebooks/ # Jupyter notebooks to analyse data 
├── src/ # libraries 
│
├── main.py      # Main Python script to launch benchmarks
└── README.md

```

## Configuration

All experiment parameters are controlled via Hydra’s configuration file at:
```
conf/config.yaml
```

## Example configuration

```
run:
  command: "caterpillar"
  llc_cache_mask: "0x000f"
  t_core: "3"
  stressor: true
  tests_path: "tests"
```

| Parameter        | Type    | Description                                                                                                    |
| ---------------- | ------- | -------------------------------------------------------------------------------------------------------------- |
| `command`        | str     | Benchmark to run. One of: `caterpillar`, `cyclictest`, `iperf3`, `mega-benchmark`, `codesys-jitter-benchmark`. |
| `llc_cache_mask` | str     | Hexadecimal mask for Last-Level Cache (LLC) configuration.                                                     |
| `t_core`         | str/int | Target CPU core for running the benchmark (i.e. '3,5,7,9')                                                     |
| `stressor`       | bool    | Enables additional stress workload during the benchmark.                                                       |
| `tests_path`     | str     | Path to the directory containing benchmark implementations.                                                    |



