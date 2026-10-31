"""
OpsLens Exasol Database Connection Helper
Reads connection settings from .env using python-dotenv.
Supports EXA_VERIFY_CERT=false for local development and self-signed certificates.
"""

import os
import ssl
from contextlib import contextmanager
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import pyexasol

# Load environment variables from .env file
load_dotenv()


def _str_to_bool(val: Optional[str], default: bool = False) -> bool:
    """Parse string representation of boolean."""
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes", "t", "y")


def get_db_config() -> Dict[str, Any]:
    """Retrieve Exasol configuration parameters from environment variables."""
    host = os.getenv("EXA_HOST", "localhost")
    port = int(os.getenv("EXA_PORT", "8563"))
    user = os.getenv("EXA_USER", "sys")
    password = os.getenv("EXA_PASSWORD", "exasol")
    schema = os.getenv("EXA_SCHEMA", "OPSLENS")
    verify_cert = _str_to_bool(os.getenv("EXA_VERIFY_CERT", "false"), default=False)
    encryption = _str_to_bool(os.getenv("EXA_ENCRYPTION", "true"), default=True)

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "schema": schema,
        "verify_cert": verify_cert,
        "encryption": encryption,
        "dsn": f"{host}:{port}",
    }


def get_connection(
    schema: Optional[str] = None,
    autocommit: bool = True,
    connection_timeout: int = 15,
    socket_timeout: int = 30,
    **extra_kwargs,
) -> pyexasol.ExaConnection:
    """
    Establish a connection to Exasol using pyexasol.
    
    Handles certificate behavior:
    - If EXA_VERIFY_CERT=false, disables SSL certificate verification (cert_reqs=ssl.CERT_NONE, check_hostname=False).
    - If EXA_VERIFY_CERT=true, requires strict verification.
    """
    config = get_db_config()
    target_schema = schema if schema is not None else config["schema"]

    connect_args: Dict[str, Any] = {
        "dsn": config["dsn"],
        "user": config["user"],
        "password": config["password"],
        "autocommit": autocommit,
        "encryption": config["encryption"],
        "connection_timeout": connection_timeout,
        "socket_timeout": socket_timeout,
    }

    # Only set schema if non-empty
    if target_schema:
        connect_args["schema"] = target_schema

    # Handle SSL verification settings
    if config["encryption"]:
        if not config["verify_cert"]:
            connect_args["websocket_sslopt"] = {
                "cert_reqs": ssl.CERT_NONE,
                "check_hostname": False,
            }
        else:
            connect_args["websocket_sslopt"] = {
                "cert_reqs": ssl.CERT_REQUIRED,
                "check_hostname": True,
            }

    # Merge any additional keyword arguments
    connect_args.update(extra_kwargs)

    try:
        connection = pyexasol.connect(**connect_args)
        return connection
    except Exception as exc:
        # Re-raise with helpful diagnostic details
        dsn = config["dsn"]
        user = config["user"]
        verify = config["verify_cert"]
        raise ConnectionError(
            f"Failed to connect to Exasol at {dsn} as user '{user}' "
            f"(verify_cert={verify}): {exc}"
        ) from exc


@contextmanager
def get_db_session(schema: Optional[str] = None, autocommit: bool = True):
    """Context manager for obtaining and automatically closing an Exasol connection."""
    conn = get_connection(schema=schema, autocommit=autocommit)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass
