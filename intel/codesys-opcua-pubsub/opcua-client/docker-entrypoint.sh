#!/bin/bash

# INTEL CONFIDENTIAL
#
# Copyright 2017-2022 Intel Corporation.
#
# This software and the related documents are Intel copyrighted materials, and
# your use of them is governed by the express license under which they were
# provided to you (License). Unless the License provides otherwise, you may
# not use, modify, copy, publish, distribute, disclose or transmit this
# software or the related documents without Intel's prior written permission.
#
# This software and the related documents are provided as is, with no express
# or implied warranties, other than those that are expressly stated in the
# License.

# stress (for stress only, benchmark won't execute!)
if [[ -n "${STRESS}" ]]; then
        $@
        echo "STRESS DONE"
        exit 0
fi

# CODESYS control runtime
if [ -f /etc/init.d/codesyscontrol ]
then
  echo "CODESYS starting ..."
  chmod +x /etc/init.d/codesyscontrol
  # Call codesyscontrol directly to preserve environment variables
  export L3_CACHE_MASK="${L3_CACHE_MASK}"
  export T_CORE="${T_CORE}"

#   rdtset -r "${T_CORE}" -c "${T_CORE}" -p "$(cat /var/run/codesyscontrol.pid)" || echo "No running codesyscontrol process found, starting a new one"
  /etc/init.d/codesyscontrol start
else
  echo "CODESYS control runtime not found"
  exit 1
fi

# keep container alive
touch /tmp/codesyscontrol.log
tail -f /tmp/codesyscontrol.log
