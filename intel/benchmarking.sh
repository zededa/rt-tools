#!/bin/bash

# Function to display usage
TESTS=()
for dir in */; do
    if [ -d "$dir" ]; then
        # Remove trailing slash
	if [ ! "${dir}" = "docs/" ] && [ ! "${dir}" = "stressor/" ]; then
            TESTS+=("${dir%/}")
	fi
    fi
done
# eval $(sudo pqos -R)  # Reset pqos
#TESTS=("caterpillar" "RTCP" "FIO" "cyclictest" "IPERF" "codesys-plc-benchmark")
usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  build                    Build the application"
    echo "  <test>              Run <test> with cache and core settings"
    echo ""
    echo "Available Tests:"
    printf "	%s\n" "${TESTS[@]}"
    echo "  Options:"
    echo "  -l, --l3-cache-mask     L3 cache mask (required)"
    echo "  -t, --t-core            Target core (required)"
    echo "  -s, --stressor	    Run with a stress in the background"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 caterpillar -l 0xffe -t 15"
    echo "  $0 caterpillar --l3-cache-mask 0xffe --t-core 15,16,17 --stressor"
    exit 1
}

# Check if at least one argument is provided
if [ $# -eq 0 ]; then
    usage
fi

COMMAND="$1"
shift

case "$COMMAND" in
    "build")
        echo "Running build command..."
        echo "Building Base image"
        docker build -f Dockerfile.base -t eci-base:latest .
        echo "building Stressor"	
        docker build -f stressor/Dockerfile -t stressor:latest stressor/.
        for t in "${TESTS[@]}"; do	
            if [ "${t}" = "codesys-opcua-pubsub" ]; then
                echo "Building Codesys-opcua-client first"
                docker build -f "${t}"/opcua-client/Dockerfile -t codesys-opcua-client:latest --build-arg CDS_VERSION=4.11.0.0 --build-arg APP_DEB=codesys-opcua-benchmark "${t}"/opcua-client/.
                echo "Building Codesys-opcua-server second"
                docker build -f "${t}"/opcua-server/Dockerfile -t codesys-opcua-server:latest --build-arg CONFIG=opcsvr-pubsub.yaml --build-arg APP=opcsvr "${t}"/opcua-server/.
            elif [ "${t}" = "codesys-jitter-benchmark" ]; then
                echo "Building Codesys-jitter-benchmark"
                docker build -f "${t}"/Dockerfile -t codesys-jitter-benchmark:latest --build-arg CDS_VERSION=4.11.0.0 --build-arg APP_DEB=codesys-eci-benchmark "${t}"/.
            else
                echo "building $t"
                docker build -f "${t}"/Dockerfile -t "${t}":latest ./"${t}"
            fi
        done
        exit 0
        ;;
   	 
    *)
	# Check if command is a valid folder
        VALID_TEST=false
        for i in "${TESTS[@]}"; do
            if [ "$COMMAND" = "$i" ]; then
                VALID_TEST=true
                break
            fi
        done
        
        if [ "$VALID_TEST" = false ]; then
            echo "Error: '$COMMAND' is not a valid command or folder"
            usage
        fi
        echo "Running Test $COMMAND"
        L3_CACHE_MASK=""
        T_CORE=""
        
        # Check if no arguments provided for caterpillar
        if [ $# -eq 0 ]; then
            echo "Error: $COMMAND command requires both -l and -t arguments"
            usage
        fi
        
        # Parse caterpillar arguments
        while [[ $# -gt 0 ]]; do
            case $1 in
                -l|--l3-cache-mask)
                    if [ -z "$2" ]; then
                        echo "Error: -l/--l3-cache-mask requires a value"
                        usage
                    fi
                    L3_CACHE_MASK="$2"
                    shift 2
                    ;;
                -t|--t-core)
                    if [ -z "$2" ]; then
                        echo "Error: -t/--t-core requires a value"
                        usage
                    fi
                    T_CORE="$2"
                    shift 2
                    ;;
                -s|--stressor)
                    STRESSOR=1
                    shift 1
                    ;;
                *)
                    echo "Unknown option: $1"
                    usage
                    ;;
            esac
        done
        
        # Validate that both required arguments are provided
        if [ -z "$L3_CACHE_MASK" ]; then
            echo "Error: -l/--l3-cache-mask is required for $COMMAND command"
            usage
        fi
        
        if [ -z "$T_CORE" ]; then
            echo "Error: -t/--t-core is required for $COMMAND command"
            usage
        fi
        if [[ "${STRESSOR}" -eq 1 ]]; then
	        RUNNING=$(docker ps -aq --filter name=stressor)
            if [ -n "$RUNNING" ]; then
                echo "Stressor is already running...skipping"
            else
                echo "Starting stressor container"
                docker run -d --rm --name stressor stressor:latest
            fi
        fi
    echo "Running $COMMAND with:"
    echo "  L3 Cache Mask: $L3_CACHE_MASK"
    echo "  Target Core: $T_CORE"
    echo "  Stressor: $STRESSOR"
	#Base Docker command
    DOCKER_COMMAND+="sudo docker run -it --rm --privileged "
	DOCKER_COMMAND+="--cpuset-cpus=${T_CORE} "
    # DOCKER_COMMAND+="--network host "
	DOCKER_COMMAND+="-v /sys/fs/resctrl:/sys/fs/resctrl  -v /dev/cpu_dma_latency:/dev/cpu_dma_latency "
    DOCKER_COMMAND+="--cap-add=SYS_NICE --cap-add=IPC_LOCK "
    DOCKER_COMMAND+="--name ${COMMAND} "
    # DOCKER_COMMAND+="--ulimit rtprio=95:95 "
        # Add your caterpillar logic here
        # Example: rdtset -t "l3=$L3_CACHE_MASK;cpu=$T_CORE;mba=100" -c "$T_CORE" -k ./caterpillar -c "$T_CORE"
	case "$COMMAND" in
	    "caterpillar")
            DOCKER_COMMAND+="${COMMAND}:latest /bin/bash -c "
            DOCKER_COMMAND+="'/usr/sbin/rdtset -t \"l3=${L3_CACHE_MASK};cpu=${T_CORE}\" -c ${T_CORE} "
            DOCKER_COMMAND+="-k /opt/benchmarking/caterpillar/caterpillar -c ${T_CORE} -s 12000'"
            echo "${DOCKER_COMMAND}"
            eval "${DOCKER_COMMAND}"
	        exit 0
		    ;;
	    "cyclictest")
            DOCKER_COMMAND+="${COMMAND}:latest /bin/bash -c "
            DOCKER_COMMAND+="'/usr/sbin/rdtset -t \"l3=${L3_CACHE_MASK};cpu=${T_CORE}\" -c ${T_CORE} "
            DOCKER_COMMAND+="-k /usr/bin/cyclictest --threads -t 4 -p 99 -l 100000 -d 1 -D 0 -i 100000  -a ${T_CORE}'"
            echo "${DOCKER_COMMAND}"
            eval "${DOCKER_COMMAND}"
            exit 0
            ;;
        "codesys-jitter-benchmark")
            DOCKER_COMMAND+="-p 8080:8080 "
            DOCKER_COMMAND+="-e DEBUGOUTPUT=1 -e DEBUGLOGFILE=/tmp/codesyscontrol_debug.log "
            DOCKER_COMMAND+="-e L3_CACHE_MASK=${L3_CACHE_MASK} -e T_CORE=\"${T_CORE}\" "
            DOCKER_COMMAND+="-d "
            DOCKER_COMMAND+="${COMMAND}:latest /bin/bash -c '/docker-entrypoint.sh'"
            echo "${DOCKER_COMMAND}"
            eval "${DOCKER_COMMAND}"
            SER=$(hostname -I | awk '{print $1}')
            echo "Pleace go to ${SER}:8080"
            exit 0
            ;;
        "codesys-opcua-pubsub")
            echo "Starting ${COMMAND}"
            docker run -d --rm --privileged --name codesys-opcua-server -p 4840:4841 codesys-opcua-server:latest
            sleep 10
            DOCKER_COMMAND+="-e L3_CACHE_MASK=${L3_CACHE_MASK} -e T_CORE=\"${T_CORE}\" "
            DOCKER_COMMAND+="-p 0.0.0.0:8081:8080/tcp "
            DOCKER_COMMAND+="-p 0.0.0.0:8081:8080/udp "
            DOCKER_COMMAND+="codesys-opcua-client:latest /bin/bash -c '/docker-entrypoint.sh'"
            echo "${DOCKER_COMMAND}"
            eval "${DOCKER_COMMAND}"
            echo "Stopping Codesys OPC-UA Server"
            docker stop codesys-opcua-server
            exit 0
            ;;
        "iperf3")
        # Running as Server Examples:
        # docker run  -it --rm --name=iperf3-server -p 5201:5201 iperf3 -s
        # docker run  -it --rm --name=iperf3-server -p 5201:5201 --network=host iperf3 -s

        # Get iperf3 Server IP ADDRESS if needed:
        # docker inspect --format "{{ .NetworkSettings.IPAddress }}" iperf3-server

        # Running as Client example
        # docker run  -it --rm iperf3 -c <SERVER_IP_ADDRESS>
            echo "Starting ${COMMAND}"
            docker run -d --rm --name=iperf3-server -p 5201:5201 iperf3:latest -s # Run as server (-s for server / -c <SERVER_IP_ADDRESS> for client)
            sleep 5
            IPERF3_SERVER_IP=$(docker inspect --format "{{ .NetworkSettings.IPAddress }}" iperf3-server)
            DOCKER_COMMAND+="-e L3_CACHE_MASK=${L3_CACHE_MASK} -e T_CORE=\"${T_CORE}\" "
            #DOCKER_COMMAND+="-d " #leave output for now
            DOCKER_COMMAND+="${COMMAND}:latest "
            DOCKER_COMMAND+="-c ${IPERF3_SERVER_IP}" # Run as client (-s for server / -c <SERVER_IP_ADDRESS> for client)
            echo "${DOCKER_COMMAND}"
            eval "${DOCKER_COMMAND}"
            echo "Stopping iperf3 Server"
            docker stop iperf3-server
            exit 0
            ;;
	    *)
	        exit 1
		    ;;
	esac
        ;;
    
    *)
        echo "Unknown command: $COMMAND"
        usage
        ;;
esac





