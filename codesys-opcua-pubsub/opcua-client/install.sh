#!/bin/bash

# default versions
VERSION=4.5.0.0
BUILD=codesyscontrol # Values: codesysgateway
# Overload versions, when they are passed as command line arguments
[ ! -z $1 ] && BUILD=$1
[ ! -z $2 ] && VERSION=$2

case $BUILD in
    codesyscontrol|codesysgateway)
        CDS_VERSION=$VERSION
        EDGE_VERSION=$VERSION
		;;

    *)
		echo " codesys installation ignore"
		exit 1
        ;;

esac

URL="https://store.codesys.com/ftp_download/3S/LinuxSL/2302000005/${CDS_VERSION}/CODESYS%20Control%20for%20Linux%20SL%20${CDS_VERSION}.package"
EDGE_URL="https://store.codesys.com/ftp_download/3S/EdgeGatewayLinux/000120/${EDGE_VERSION}/CODESYS%20Edge%20Gateway%20for%20Linux%20${EDGE_VERSION}.package"

# check if this linux system is debian based
if ! command -v dpkg >/dev/zero; then 
	echo "This install script only runs on debian based distributions"
	exit 1
fi

# check necessary tools
if ! command -v wget >/dev/zero; then
	echo "'wget' required to download the CODESYS package."
	echo "You may try:"
	echo "  apt-get install wget"
	exit 1;
fi

if ! command -v unzip >/dev/zero; then
	echo "'unzip' required to unpack the CODESYS package."
	echo "You may try:"
	echo "  apt-get install unzip"
	exit 1;
fi

# check if /lib64 is available
if [ ! -d /lib64 ]; then
	echo "Seems that you are not running on a traditional multi arch system."
	echo "As a workaround, you can link /lib to /lib64."
	echo "ln -s /lib /lib64"
fi

# check availability of ipv4, and try to install xinetd forwarding if not
ipv4=$(ip -4 addr list scope global)
ipv6=$(ip -6 addr list scope global)

if [ -z "${ipv4}" -a ! -z "${ipv6}" ]; then
	echo "You are running on an ipv6 only host. CODESYS doesn't support this, yet."
	echo "So we try to install an ipv6 forwarding, using xinetd."
	# check if xinetd is installed
	if [ ! -d /etc/xinetd.d ]; then
		echo "'xinetd' is required to tunnel between ipv4 and ipv6."
		echo "You may try:"
		echo "  apt-get install xinetd"
		exit 1;
	fi
	address=$(ip -6 addr list scope global dev eth0 | grep -v " fd" | sed -n 's/.*inet6 \([0-9a-f:]\+\).*/\1/p' | head -n 1)
	cat << EOF > /etc/xinetd.d/codesys-ipv6
service codesys-tcp
{
    flags           = IPv6
    disable         = no
    type            = UNLISTED
    socket_type     = stream
    protocol        = tcp
    user            = nobody
    wait            = no
    redirect        = 127.0.0.1 11740
    port            = 11740
    bind            = ${address}
}
service codesys-gw
{
    flags           = IPv6
    disable         = no
    type            = UNLISTED
    socket_type     = stream
    protocol        = tcp
    user            = nobody
    wait            = no
    redirect        = 127.0.0.1 1217
    port            = 1217
    bind            = ${address}
}
service codesys-edge
{
    flags           = IPv6
    disable         = no
    type            = UNLISTED
    socket_type     = stream
    protocol        = tcp
    user            = nobody
    wait            = no
    redirect        = 127.0.0.1 11743
    port            = 11743
    bind            = ${address}
}
EOF
	systemctl reload xinetd
fi

# start installation
if [ -z "${TRY_RUN}" ]; then
   case $BUILD in
        codesyscontrol)
			# download and install the control package
			[ ! -f /tmp/codesys.package ] && wget --no-check-certificate --output-document=/tmp/codesys.package ${URL}
			(
				unzip -p /tmp/codesys.package '*codemeter*.deb' > /tmp/codemeter.deb && \
				dpkg -i /tmp/codemeter.deb
				unzip -p /tmp/codesys.package '*codesyscontrol*.deb' > /tmp/codesys.deb && \
				dpkg -i /tmp/codesys.deb
			)
            ;;

        codesysgateway)
			# download and install the edge package
			[ ! -f /tmp/edge.package ] && wget --no-check-certificate --output-document=/tmp/edge.package ${EDGE_URL}
			(
				unzip -p /tmp/edge.package '*.deb' > /tmp/edge.deb && \
				dpkg -i /tmp/edge.deb
			)
            ;;
        *)
			echo "ignore codesys installation"
			exit 1
            ;;
    esac
fi

