#!/bin/bash

usage()
{
cat <<EOF
OPTIONS := { -s[erver] Add license-server by IP-address
                       Multiple license-servers are specified seperately "... -s <IPa> -s<IPb> ..."
             -n[ic]    Wait for network interface (nic) to be mapped into container namespace.
                       Multiple nics are specified seperately "... -n <NICa> -n<NICb> ..."
             -d[hcp]   Run DHCP client on specified interface before starting CODESYS.
                       Multiple interfaces are specified seperately "... -d <NICa> -d <NICb> ..."
             -h[elp]
            }
EOF
}

term() {
    echo "[INFO] $0: Shuting down codesyscontrol..."
    kill -15 $pid
    wait $pid

    # Release DHCP leases
    if [ ! -z "$DHCPLIST" ]; then
        for DHCPNIC in "${DHCPLIST[@]}"; do
            echo "[INFO] $0: Releasing DHCP lease on $DHCPNIC..."
            dhclient -r "$DHCPNIC" 2>/dev/null
        done
    fi
}

while getopts s:hn:d: opt
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
        d)
            DHCPLIST+=("${OPTARG}")
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

# Run DHCP client on specified interfaces
if [ ! -z "$DHCPLIST" ]; then
    for DHCPNIC in "${DHCPLIST[@]}"; do
        if [ ! -d /sys/class/net/$DHCPNIC ]; then
            echo "[ERROR] $0: DHCP interface $DHCPNIC not found in container. Skipping."
            continue
        fi

        echo "[INFO] $0: Running DHCP client on $DHCPNIC..."
        if command -v dhclient >/dev/null 2>&1; then
            dhclient -v -1 "$DHCPNIC" 2>&1
            DHCP_RC=$?
        else
            echo "[ERROR] $0: dhclient not found. Install isc-dhcp-client in the base image."
            DHCP_RC=1
        fi

        if [ $DHCP_RC -eq 0 ]; then
            DHCP_IP=$(ip -4 addr show "$DHCPNIC" 2>/dev/null | grep -oP 'inet \K[0-9.]+')
            echo "[INFO] $0: DHCP on $DHCPNIC succeeded, got IP: ${DHCP_IP:-unknown}"
        else
            echo "[WARNING] $0: DHCP on $DHCPNIC failed (rc=$DHCP_RC). Continuing anyway."
        fi
    done
fi

echo "[INFO] $0: Codesyscontrol starting"
/opt/codesys/bin/codesyscontrol.bin $DEBUG /conf/codesyscontrol/CODESYSControl.cfg &
pid=($!)

trap term SIGTERM
trap term SIGINT

wait "$pid"
