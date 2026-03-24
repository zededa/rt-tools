#!/bin/bash

usage()
{
cat <<EOF
OPTIONS := { -s[erver] Add license-server by IP-address
                       Multiple license-servers are specified seperately "... -s <IPa> -s<IPb> ..."
             -n[ic]    Wait for network interface (nic) to be mapped into container namespace.
                       Multiple nics are specified seperately "... -n <NICa> -n<NICb> ..."
             -h[elp]
            }
EOF
}

term() {
    echo "[INFO] $0: Shuting down codesyscontrol..."
    kill -15 $pid
    wait $pid
    # On shutdown, dump a summary of interesting strace findings
    if [ -f "$STRACE_LOG" ]; then
        echo "[STRACE] Log saved at $STRACE_LOG ($(wc -l < "$STRACE_LOG") lines, $(du -h "$STRACE_LOG" | cut -f1))"
        echo "[STRACE] --- sched_setscheduler calls ---"
        grep "sched_setscheduler" "$STRACE_LOG" 2>/dev/null | head -20
        echo "[STRACE] --- sched_setaffinity calls ---"
        grep "sched_setaffinity" "$STRACE_LOG" 2>/dev/null | head -20
        echo "[STRACE] --- sched_getaffinity calls ---"
        grep "sched_getaffinity" "$STRACE_LOG" 2>/dev/null | head -20
        echo "[STRACE] --- failed syscalls (EPERM/EINVAL/ENOSYS) ---"
        grep -E "= -1 E(PERM|INVAL|NOSYS|SRCH|FAULT)" "$STRACE_LOG" 2>/dev/null | grep -v "futex\|nanosleep\|poll\|recvmsg" | head -40
        echo "[STRACE] --- cgroup/cpu/rt related file opens ---"
        grep -E "openat.*(/cgroup|/cpu|rt_runtime|rt_period|cpuset|sched)" "$STRACE_LOG" 2>/dev/null | head -30
        echo "[STRACE] --- /proc and /sys reads ---"
        grep -E "openat.*(\/proc\/|\/sys\/)" "$STRACE_LOG" 2>/dev/null | head -40
        echo "[STRACE] --- mlockall/mlock calls ---"
        grep -E "mlock" "$STRACE_LOG" 2>/dev/null | head -10
        echo "[STRACE] --- prctl calls ---"
        grep "prctl" "$STRACE_LOG" 2>/dev/null | head -20
        echo "[STRACE] --- clone/clone3 calls ---"
        grep -E "clone[^d]" "$STRACE_LOG" 2>/dev/null | head -20
        echo "[STRACE] --- signals (SIGKILL/SIGTERM/SIGSEGV/SIGABRT) ---"
        grep -E "\+\+\+ |--- SIG" "$STRACE_LOG" 2>/dev/null | head -20
        echo "[STRACE] --- END SUMMARY ---"
    fi
}

while getopts s:hn: opt
do
	case "${opt}" in
        s)
            LICENSESERVERLIST+=("${OPTARG}")
            ;;
        h)
		    usage
		    exit 1
		    ;;
        n)
            NICLIST+=("${OPTARG}")
            ;;
		?)
     		echo "Unknown option -"${OPTARG}
		    usage
		    exit 1
		    ;;
	esac
done
shift $((OPTIND -1))

# At runtimestart we expect /conf/codesyscontrol and /data/codesyscontrol to be present
if [ ! -d /conf/codesyscontrol/ ] || [ ! -d /data/codesyscontrol/ ]; then
    echo "[ERROR] $0: Missing /conf/codesyscontrol or /data/codesyscontrol. Call docker run with volume options:"
    echo
    echo "-v ~/<mountingpoint>/conf/codesyscontrol/:/conf/codesyscontrol/ -v ~/<mountingpoint>/data/codesyscontrol/:/data/codesyscontrol/"
    echo "For example:"
    echo "docker run -v ~/dockerMount/conf/codesyscontrol/:/conf/codesyscontrol/ -v ~/dockerMount/data/codesyscontrol/:/data/codesyscontrol/ -p 11740:11740/tcp -p 443:443/tcp -p 8080:8080/tcp codesyscontrol_linux:4.5.0.0"
    exit 1
fi

echo "[INFO] $0: Initialize /conf and /data directories used by docker mounts"

#check if initialization of /conf was already done.
if [ ! -f /conf/codesyscontrol/.docker_initialized ]; then
    #not yet initialized, copy original files
    echo "[INFO] $0: Initialize /conf/codesyscontrol with files from /etc"
    cp -f /etc/codesyscontrol/CODESYSControl.cfg /conf/codesyscontrol/
    cp -f /etc/codesyscontrol/CODESYSControl_User.cfg /conf/codesyscontrol/
    #touch marker file to avoid overwriteing existing files
    touch /conf/codesyscontrol/.docker_initialized
fi

#check for CmpRetain* in User.cfg and add if not there.
RUNTIME_CONFIGFILE=/conf/codesyscontrol/CODESYSControl_User.cfg

if  grep -E "^\[ComponentManager\]" ${RUNTIME_CONFIGFILE} >/dev/null ; then
    echo "[INFO] section found"
    if grep -E "^Component.[0-9]*[0-9]=CmpRetain"  ${RUNTIME_CONFIGFILE} > /dev/null; then
        echo "[INFO] Component entry already found. No change!"
    else
        # get all lines with Component.xy and use highest
        highest_CmpNr=$(sed -n '/^Component\.\([0-9]*[0-9]\)=.*/ s//\1/p' ${RUNTIME_CONFIGFILE} | sort -u | tail -n 1)
        next_CmpNr=0
        # get line nr of ComponentManager section end
        linenr_endofblock=$(sed -n '/^\[ComponentManager\]$/,/^\[.*\]$/=' ${RUNTIME_CONFIGFILE} | tail -n 2 | head -n 1)
        if [ -z ${highest_CmpNr} ]; then
            echo "no other Component found"
            highest_CmpNr=0
        fi
        let "next_CmpNr=${highest_CmpNr} + 1"
        newentry="Component.${next_CmpNr}=CmpRetain"
        # write to CmpSettingsSection, Component might be not set at all
        sed -i "${linenr_endofblock} a ${newentry}" ${RUNTIME_CONFIGFILE}

        echo "writing new Component setting: $newentry at line ${linenr_endofblock}"
    fi
else
    echo "[INFO] section not found"
    section="[ComponentManager]"
    newentry="Component.0=${CMP}"
    echo "" >> ${RUNTIME_CONFIGFILE}
    echo "${section}"  >> ${RUNTIME_CONFIGFILE}
    echo "${newentry}"  >> ${RUNTIME_CONFIGFILE}
    echo "" >> ${RUNTIME_CONFIGFILE}
    echo "[INFO] section appended at end of file"
fi

# add license-server to config-file
if [[ -z $LICENSESERVERLIST ]]
then
    echo "[INFO] $0: To add a license-server start the container with -s <IP> at the end"
    echo "[INFO] $0: For example: docker run -v ~/dockerMount/conf/codesyscontrol/:/conf/codesyscontrol/ -v ~/dockerMount/data/codesyscontrol/:/data/codesyscontrol/ -p 11740:11740/tcp -p 443:443/tcp -p 8080:8080/tcp codesyscontrol_linux:4.5.0.0 -s 192.168.99.1"
fi

CFGPATH="/conf/codesyscontrol/CODESYSControl.cfg"

# Cleanup all old LicenseServer entries
sed -i '/LicenseServer.*/d' $CFGPATH

if [ ! -z $LICENSESERVERLIST ]
then
    NUM=1
    # Write first entry below EnableNetLicenses=1
    sed -i "/EnableNetLicenses=1/a LicenseServer.$NUM=${LICENSESERVERLIST[0]}" $CFGPATH
    echo "[INFO] $0: Licenseserver ${LICENSESERVERLIST[0]} written to config"

    # Write all next entries below last one
    for LICENSESERVER in  "${LICENSESERVERLIST[@]:1}" ; do
        ((NUM=NUM+1))
        sed -i "/LicenseServer.$((NUM-1))=*/a LicenseServer.$NUM=${LICENSESERVER}" $CFGPATH
        echo "[INFO] $0: Licenseserver ${LICENSESERVER} written to config"
    done
fi

#check if initialization of /data was already done.
if [ ! -f /data/codesyscontrol/.docker_initialized ]; then
    #not yet initialized, copy original files
    echo "[INFO] $0: Initialize /data/codesyscontrol with files from /var/opt/codesys"
    #copy contents including all hidden files
    cp -rT /var/opt/codesys/ /data/codesyscontrol/
    #touch marker file to avoid overwriteing existing files
    touch /data/codesyscontrol/.docker_initialized
fi

cd /data/codesyscontrol/

echo "[INFO] $0: Check needed capabilities"

NEEDEDCAPS=("cap_chown" "cap_ipc_lock" "cap_kill" "cap_net_admin" "cap_net_bind_service" "cap_net_broadcast" \
    "cap_net_raw" "cap_setfcap" "cap_setpcap" "cap_sys_admin" "cap_sys_module" "cap_sys_nice" "cap_sys_ptrace" \
    "cap_sys_rawio" "cap_sys_resource" "cap_sys_time")
CAPMISSING=""
for i in ${NEEDEDCAPS[@]}; do
    echo -n "[INFO] $0: Testing $i: "
    if /sbin/capsh --has-p=$i 2>/dev/null ; then
        echo -e "[OK]"
    else
        echo -e "[NOK]"
        CAPMISSING="TRUE"
    fi
done

if [ ! -z $CAPMISSING ] ; then
    echo "[WARNING] $0: Not all needed capabilities found. No realtime behaviour can be achived!"
fi

# check if needed network adapter (NIC) is specified and wait until it got mapped to our namespace
INTERVAL=2
TIMEOUT=10

if [ ! -z "$NICLIST" ]
then
    echo "[INFO] $0: Specified network adapters:"
    for NIC in "${NICLIST[@]}"
    do
        echo "[INFO] $0: - $NIC"
    done
    for NIC in "${NICLIST[@]}"
    do
        echo "[INFO] $0: Waiting for network adapter $NIC"
        COUNTER=0

        while ! grep "up" "/sys/class/net/$NIC/operstate" 1>/dev/null 2>/dev/null  && [ $COUNTER -lt $TIMEOUT ]
        do
            echo "[INFO] $0: sleeping..."
            sleep $INTERVAL
            ((COUNTER+=$INTERVAL))
        done

        # No nic mapped after timeout
		if [ ! -d /sys/class/net/$NIC ]; then
			echo "[ERROR] $0: Specified NIC $NIC not mapped to container. Check configuration."
			exit 1
		fi

        if ! grep "up" "/sys/class/net/$NIC/operstate" 1>/dev/null 2>/dev/null ; then
            echo "[INFO] $0: Specified NIC $NIC mapped to container but operstate is not up. Check if cable is plugged in."
        else
            echo "[INFO] $0: Specified NIC $NIC mapped to container."
        fi
		sleep 1
    done
fi

# ============================================================================
# STRACE INSTRUMENTATION FOR CODESYS CPU AFFINITY / RT TASK DEBUGGING
# ============================================================================
# This wraps codesyscontrol.bin with strace to capture all syscalls.
# The strace log is written to /tmp/codesys_strace.log inside the container.
#
# To retrieve the log after the container runs:
#   ctr -n eve-user-apps t exec --exec-id strace-grab <container_id> cat /tmp/codesys_strace.log > /persist/codesys_strace.log
#
# Or from the host:
#   eve exec <app-uuid> cat /tmp/codesys_strace.log > /tmp/codesys_strace.log
#
# Key things to look for in the log:
#   1. sched_setscheduler / sched_setaffinity / sched_getaffinity calls
#   2. openat() calls for /sys/fs/cgroup/*, /proc/*, /sys/devices/system/cpu/*
#   3. read() calls immediately after those opens (what values does CODESYS see?)
#   4. mlockall / mlock calls and their return values
#   5. prctl calls (PR_SET_NAME for thread naming, etc.)
#   6. Any syscall returning -1 EPERM/EINVAL/ENOSYS near the sched_* calls
#   7. Signals delivered to threads (--- SIG... ---)
#   8. Thread exits (+++ exited with ... +++)
# ============================================================================

STRACE_LOG="/tmp/codesys_strace.log"

# Check if strace is available
if ! command -v strace &>/dev/null; then
    echo "[ERROR] $0: strace not found in container! Falling back to direct execution."
    echo "[ERROR] $0: Install strace in the container image (apt-get install strace) and retry."
    echo "[INFO] $0: Codesyscontrol starting (WITHOUT strace)"
    /opt/codesys/bin/codesyscontrol.bin $DEBUG /conf/codesyscontrol/CODESYSControl.cfg &
    pid=($!)
    trap term SIGTERM
    trap term SIGINT
    wait "$pid"
    exit $?
fi

# Dump pre-launch environment info for context
echo "[STRACE] ============================================"
echo "[STRACE] Pre-launch environment snapshot"
echo "[STRACE] ============================================"
echo "[STRACE] Date: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "[STRACE] Hostname: $(hostname)"
echo "[STRACE] PID: $$"

echo "[STRACE] --- /proc/self/status (caps, seccomp, nonewprivs) ---"
grep -E "^(Cap|NoNewPrivs|Seccomp|Cpus_allowed)" /proc/self/status 2>/dev/null

echo "[STRACE] --- CPU affinity (taskset) ---"
taskset -p $$ 2>/dev/null || echo "(taskset not available)"

echo "[STRACE] --- /proc/self/cgroup ---"
cat /proc/self/cgroup 2>/dev/null

echo "[STRACE] --- cpuset.cpus ---"
CGROUP_PATH=""
for p in /sys/fs/cgroup/cpuset/cpuset.cpus /sys/fs/cgroup/cpuset.cpus /sys/fs/cgroup/*/cpuset.cpus; do
    if [ -f "$p" ]; then
        echo "[STRACE]   $p = $(cat "$p")"
        CGROUP_PATH="$(dirname "$p")"
    fi
done

echo "[STRACE] --- cpu.rt_runtime_us ---"
for p in /sys/fs/cgroup/cpu/cpu.rt_runtime_us /sys/fs/cgroup/cpu.rt_runtime_us /sys/fs/cgroup/*/cpu.rt_runtime_us; do
    if [ -f "$p" ]; then
        echo "[STRACE]   $p = $(cat "$p")"
    fi
done

echo "[STRACE] --- /proc/cpuinfo summary ---"
echo "[STRACE]   processors: $(grep -c ^processor /proc/cpuinfo)"
grep ^processor /proc/cpuinfo

echo "[STRACE] --- /sys/devices/system/cpu/online ---"
cat /sys/devices/system/cpu/online 2>/dev/null && echo "" || echo "(not available)"

echo "[STRACE] --- /sys/devices/system/cpu/ directory listing ---"
ls -la /sys/devices/system/cpu/ 2>/dev/null | grep cpu

echo "[STRACE] --- sysconf values ---"
getconf _NPROCESSORS_ONLN 2>/dev/null && echo " = _NPROCESSORS_ONLN" || true
getconf _NPROCESSORS_CONF 2>/dev/null && echo " = _NPROCESSORS_CONF" || true

echo "[STRACE] --- CODESYS config (RT-relevant sections) ---"
grep -A5 -E "^\[(SysCpuMultiCore|SysTask|CmpSchedule|SysProcess)" /conf/codesyscontrol/CODESYSControl.cfg 2>/dev/null || echo "(no RT sections found)"
grep -A5 -E "^\[(SysCpuMultiCore|SysTask|CmpSchedule|SysProcess)" /conf/codesyscontrol/CODESYSControl_User.cfg 2>/dev/null || echo "(no RT sections in User.cfg)"

echo "[STRACE] --- rlimits ---"
ulimit -a 2>/dev/null

echo "[STRACE] ============================================"
echo "[STRACE] Launching codesyscontrol.bin under strace"
echo "[STRACE] Log file: $STRACE_LOG"
echo "[STRACE] ============================================"

echo "[INFO] $0: Codesyscontrol starting (with strace instrumentation)"

# Full strace: follow forks, microsecond timestamps, long strings, all syscalls
# -f    : follow forks (trace all threads)
# -ff   : separate output per-pid (DISABLED - single file is easier to correlate)
# -tt   : print timestamps with microseconds
# -T    : show time spent in each syscall
# -s 512: print up to 512 bytes of string arguments (to see file contents read)
# -y    : print paths associated with file descriptors
# -yy   : print socket/protocol details too
# -e trace=all : trace everything (can restrict later if log is too large)
strace \
    -f \
    -tt \
    -T \
    -s 512 \
    -y \
    -o "$STRACE_LOG" \
    -e trace=all \
    /opt/codesys/bin/codesyscontrol.bin $DEBUG /conf/codesyscontrol/CODESYSControl.cfg &
pid=($!)

echo "[STRACE] strace PID: $pid"
echo "[STRACE] codesyscontrol.bin will be a child of strace"

trap term SIGTERM
trap term SIGINT

wait "$pid"
