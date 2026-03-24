# CODESYS HDE2E PLC Containers

Pre-compiled CODESYS PLC application containers for the hard-deterministic end-to-end (hdE2E) latency benchmark. Builds 4 PLC instances from a single parameterized Dockerfile, ready for deployment on EVE OS.

## Prerequisites

- CODESYS runtime `.deb` package (e.g. `codesyscontrol_virtuallinux_4.19.0.0_amd64.deb`) — download from the [CODESYS Store](https://store.codesys.com/)
- Container build tool (`docker build` or equivalent)

No CODESYS IDE is required. The PLC applications are already compiled — each `plc/*/data/codesyscontrol/PlcLogic/Control/Control.app` is a pre-built binary ready to run.

## Building

### Build everything (base + all 4 PLC instances)

```sh
DEB=codesyscontrol_virtuallinux_4.19.0.0_amd64.deb \
TAG=1.0.0 \
  ./build-all.sh --base
```

### Build and push to a registry

```sh
DEB=codesyscontrol_virtuallinux_4.19.0.0_amd64.deb \
TAG=1.0.0 \
  ./build-all.sh --base myregistry.example.com
```

### Build only the base image

Useful when the CODESYS runtime version changes but PLC apps stay the same:

```sh
DEB=codesyscontrol_virtuallinux_4.19.0.0_amd64.deb \
BASE_TAG=1.0.1 \
  ./build-all.sh --base-only
```

### Rebuild instance images only (base must already exist)

```sh
TAG=1.0.0 ./build-all.sh
```

### Environment variables

| Variable   | Default                                                  | Description                        |
|------------|----------------------------------------------------------|------------------------------------|
| `DEB`      | `codesyscontrol_virtuallinux_4.18.0.0_amd64.deb`        | CODESYS runtime `.deb` filename    |
| `TAG`      | `latest`                                                 | Image tag for PLC instance images  |
| `BASE_TAG` | `1.0.1`                                                  | Image tag for the base image       |

### Build options

| Flag         | Description                                   |
|--------------|-----------------------------------------------|
| `--base`     | Build the base image before instance images    |
| `--base-only`| Build only the base image, skip instances      |
| `--no-cache` | Pass `--no-cache` to the build                 |

## What gets built

The build produces 5 container images:

| Image                      | PLC Instance     | Role    |
|----------------------------|------------------|---------|
| `codesys-hde2e-base`       | —                | Base    |
| `codesys-control-plc-01`   | Control_PLC_01   | Control |
| `codesys-control-plc-02`   | Control_PLC_02   | Control |
| `codesys-io-plc-01`        | IO_PLC_01        | I/O     |
| `codesys-io-plc-02`        | IO_PLC_02        | I/O     |

## Container entrypoint

Each PLC instance runs `startup.sh`, which:

1. Initializes `/conf` and `/data` directories
2. Configures CmpRetain component and license servers
3. Waits for assigned network interfaces to appear
4. Runs DHCP on specified interfaces
5. Checks required Linux capabilities
6. Starts `codesyscontrol.bin`

The default `CMD` is `-d eth1` (run DHCP on `eth1`). Override at deploy time if your network interface differs.

A `startup-strace.sh` variant is included for debugging — it wraps the CODESYS binary with `strace` to capture scheduler, affinity, and cgroup syscalls. Switch the entrypoint in the Dockerfile to use it.

## Access

Once a PLC instance is running:

| Service          | Port  |
|------------------|-------|
| WebVisu          | 8080  |
| CODESYS Gateway  | 11740 |
| OPC UA           | 4840  |

## Real-time tuning

For production real-time performance the host kernel must be configured:

```
isolcpus=3,5,7,9 nohz_full=3,5,7,9 rcu_nocbs=3,5,7,9
```


## Directory structure

```
codesys-hde2e/
├── Dockerfile.base             # Base image: OS, CODESYS runtime, debug tools
├── Dockerfile                  # Instance image: PLC app + config overlay
├── build-all.sh                # Build script
├── startup.sh                  # Container entrypoint
├── startup-strace.sh           # Debug entrypoint (strace instrumented)
├── plc/                        # Pre-compiled PLC applications
│   ├── Control_PLC_01/
│   ├── Control_PLC_02/
│   ├── IO_PLC_01/
│   └── IO_PLC_02/
└── configs/                    # Configuration overlays
    ├── control/                # Control PLC configs
    ├── io/                     # I/O PLC configs
    ├── rdt_config_control.yaml
    └── rdt_config_io.yaml
```
