import argparse
import urllib3
import json
import re
import sys

from omegaconf import DictConfig
from pathlib import Path
from typing import Dict, Optional, Tuple


try:
    import requests
    from requests.auth import HTTPBasicAuth

    REQUESTS_AVAILABLE = True
except ImportError:
    print(
        "ERROR: requests library not found. Install with: pip install requests",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Disable SSL warnings for self-signed iDRAC certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import urllib3


def process_bios_settings(cfg: DictConfig):
    """
    Fetches BIOS settings using parameters from a Hydra config object.

    Expected Config Structure (example):
      redfish:
        enabled: true
        host: "1.2.3.4"
        username: "root"
        password: "password"
        verify_ssl: false
        timeout: 10
      output:
        format: "text"  # json, yaml, text
        file: "bios.json" # or null for stdout
        pretty: true
    """

    # 1. Validation & Setup
    # Access keys safely. Using .get() allows for defaults if keys are missing in YAML.
    # We assume 'redfish' and 'output' are root keys in the passed cfg,
    # or you can pass cfg.bios_task to this function.
    rf_cfg = cfg.get("redfish", {})
    out_cfg = cfg.get("output", {})

    if not rf_cfg.get("enabled", True):
        print("WARNING: Redfish task is disabled in config", file=sys.stderr)
        return

    host = rf_cfg.get("host")
    username = rf_cfg.get("username", "root")
    password = rf_cfg.get("password")
    verify_ssl = rf_cfg.get("verify_ssl", False)
    timeout = rf_cfg.get("timeout", 10)

    if not host:
        print("ERROR: No host specified in config (redfish.host)", file=sys.stderr)
        raise ValueError("Host Missing")

    if not password:
        raise ValueError("ERROR: No password specified in config (redfish.password)")

    session, host_url = connect_redfish(host, username, password, verify_ssl, timeout)
    if not session:
        raise ValueError("Session missing")

    attributes = get_bios_attributes(session, host_url, timeout)
    if not attributes:
        raise ValueError("Attributes missing")

    output_fmt = out_cfg.get("format", "text")
    is_pretty = out_cfg.get("pretty", True)

    if output_fmt == "json":
        output_data = format_json(attributes, pretty=is_pretty)
    elif output_fmt == "yaml":
        output_data = format_yaml(attributes)
    else:
        output_data = format_text(attributes)

    output_file = out_cfg.get("file")

    if output_file:
        try:
            with open(output_file, "w") as f:
                f.write(output_data)
            print(f"✓ Saved to {output_file}", file=sys.stderr)
        except Exception as e:
            raise ValueError(f"ERROR: Failed to write to {output_file}: {e}")
    else:
        # Print to stdout
        print(output_data)


def connect_redfish(
    host: str, username: str, password: str, verify_ssl: bool = False, timeout: int = 10
) -> Tuple[Optional[requests.Session], str]:
    """
    Create authenticated Redfish session to iDRAC.

    Returns:
        Tuple of (authenticated session or None, normalized host URL)
    """
    # Ensure host has https:// prefix
    if not host.startswith("http://") and not host.startswith("https://"):
        host = f"https://{host}"

    session = requests.Session()
    session.auth = HTTPBasicAuth(username, password)
    session.verify = verify_ssl
    session.headers.update(
        {"Content-Type": "application/json", "Accept": "application/json"}
    )

    # Test connection with root endpoint
    try:
        print(f"Connecting to {host}...", file=sys.stderr)
        response = session.get(f"{host}/redfish/v1/", timeout=timeout)
        response.raise_for_status()
        print(f"✓ Connected successfully", file=sys.stderr)
        return session, host
    except requests.exceptions.Timeout:
        print(f"ERROR: Connection timeout to {host}", file=sys.stderr)
        return None, host
    except requests.exceptions.ConnectionError as e:
        print(f"ERROR: Connection failed to {host}: {e}", file=sys.stderr)
        return None, host
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: HTTP error from {host}: {e}", file=sys.stderr)
        return None, host
    except Exception as e:
        print(f"ERROR: Unexpected error connecting to {host}: {e}", file=sys.stderr)
        return None, host


def get_bios_attributes(
    session: requests.Session, host: str, timeout: int = 10
) -> Optional[Dict[str, any]]:
    """
    Retrieve BIOS attributes from Dell iDRAC.

    Returns:
        Dictionary of BIOS attributes or None on failure
    """
    try:
        # Dell iDRAC standard endpoint for BIOS settings
        url = f"{host}/redfish/v1/Systems/System.Embedded.1/Bios"
        print(f"Fetching BIOS attributes from {url}...", file=sys.stderr)

        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        # BIOS attributes are in the "Attributes" key
        attributes = data.get("Attributes", {})
        print(f"✓ Retrieved {len(attributes)} BIOS attributes", file=sys.stderr)
        return attributes
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: Failed to fetch BIOS attributes: {e}", file=sys.stderr)
        print(
            f"  Response: {e.response.text if e.response else 'No response'}",
            file=sys.stderr,
        )
        return None
    except Exception as e:
        print(f"ERROR: Unexpected error fetching BIOS: {e}", file=sys.stderr)
        return None


def format_text(attributes: Dict[str, any]) -> str:
    """
    Format BIOS attributes in human-readable text format.
    Groups attributes by prefix for better organization.
    """
    if not attributes:
        return "No BIOS attributes available"

    lines = []
    lines.append("=" * 80)
    lines.append(f"BIOS SETTINGS ({len(attributes)} total attributes)")
    lines.append("=" * 80)
    lines.append("")

    # Group by prefix (first word before capital letter)
    groups = {}
    ungrouped = []

    for key in sorted(attributes.keys()):
        value = attributes[key]
        # Try to extract prefix (e.g., "Proc" from "ProcTurboMode")
        match = re.match(r"^([A-Z][a-z]+)", key)
        if match:
            prefix = match.group(1)
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append((key, value))
        else:
            ungrouped.append((key, value))

    # Output grouped attributes
    for prefix in sorted(groups.keys()):
        lines.append(f"[{prefix}*] Settings ({len(groups[prefix])} attributes)")
        lines.append("-" * 80)
        for key, value in groups[prefix]:
            # Format value nicely
            if isinstance(value, bool):
                value_str = "Enabled" if value else "Disabled"
            elif isinstance(value, str) and len(value) > 60:
                value_str = value[:57] + "..."
            else:
                value_str = str(value)
            lines.append(f"  {key:<40} = {value_str}")
        lines.append("")

    # Output ungrouped attributes
    if ungrouped:
        lines.append(f"[Other] Settings ({len(ungrouped)} attributes)")
        lines.append("-" * 80)
        for key, value in ungrouped:
            if isinstance(value, bool):
                value_str = "Enabled" if value else "Disabled"
            elif isinstance(value, str) and len(value) > 60:
                value_str = value[:57] + "..."
            else:
                value_str = str(value)
            lines.append(f"  {key:<40} = {value_str}")
        lines.append("")

    return "\n".join(lines)


def format_json(attributes: Dict[str, any], pretty: bool = True) -> str:
    """Format BIOS attributes as JSON."""
    if pretty:
        return json.dumps(attributes, indent=2, sort_keys=True)
    else:
        return json.dumps(attributes, sort_keys=True)


def format_yaml(attributes: Dict[str, any]) -> str:
    """Format BIOS attributes as YAML."""
    if not YAML_AVAILABLE:
        raise ValueError("ERROR: PyYAML not installed. Cannot output YAML format.")
    return yaml.dump(attributes, default_flow_style=False, sort_keys=True)
