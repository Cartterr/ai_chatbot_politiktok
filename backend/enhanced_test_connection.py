import asyncio
import httpx
import socket
import subprocess
import re
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_connection")

# Get Windows host IP using multiple methods
def get_potential_windows_hosts():
    potential_hosts = []
    
    # 1. Try to get from /etc/resolv.conf (common in WSL)
    try:
        with open('/etc/resolv.conf', 'r') as f:
            for line in f:
                if line.startswith('nameserver'):
                    ip = line.split()[1].strip()
                    logger.info(f"Found nameserver in resolv.conf: {ip}")
                    potential_hosts.append(ip)
    except Exception as e:
        logger.error(f"Error reading /etc/resolv.conf: {str(e)}")
    
    # 2. Try to get the default gateway
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            logger.info(f"Local IP: {local_ip}")
            # Try variations on the local IP
            parts = local_ip.split('.')
            potential_hosts.append(f"{parts[0]}.{parts[1]}.{parts[2]}.1")  # Typical gateway
            potential_hosts.append(local_ip)  # Local IP itself
    except Exception as e:
        logger.error(f"Error getting socket info: {str(e)}")
    
    # 3. Try to use the 'ip route' command to find the default gateway
    try:
        result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
        if result.returncode == 0:
            # Look for default gateway
            match = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', result.stdout)
            if match:
                gateway = match.group(1)
                logger.info(f"Default gateway from ip route: {gateway}")
                potential_hosts.append(gateway)
    except Exception as e:
        logger.error(f"Error running ip route: {str(e)}")
    
    # 4. Try standard WSL/Docker hosts
    standard_hosts = [
        'localhost',
        'host.docker.internal',
        'wsl.host.internal',  # New in WSL 2
        '172.17.0.1',         # Default Docker bridge
        '172.18.0.1',         # Alternative Docker bridge
        '172.19.0.1',         # Alternative Docker bridge
        '172.20.0.1',         # Alternative Docker bridge
        '172.21.0.1',         # Alternative Docker bridge
        '172.22.0.1',         # Alternative Docker bridge
        '172.16.0.1',         # Common LAN subnet
        '192.168.0.1',        # Common home router
        '192.168.1.1',        # Common home router
        '10.0.0.1',           # Common network gateway
        '127.0.0.1'           # Localhost
    ]
    
    # Add standard hosts
    potential_hosts.extend(standard_hosts)
    
    # 5. Try to parse the ifconfig to find more IPs
    try:
        result = subprocess.run(['ifconfig'], capture_output=True, text=True)
        if result.returncode == 0:
            # Find all IPs
            ips = re.findall(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
            for ip in ips:
                if not ip.startswith('127.'):  # Skip localhost
                    potential_hosts.append(ip)
                    # Also add the theoretical gateway for each subnet
                    parts = ip.split('.')
                    potential_hosts.append(f"{parts[0]}.{parts[1]}.{parts[2]}.1")
    except Exception as e:
        # ifconfig might not be available, try ip addr instead
        try:
            result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
            if result.returncode == 0:
                # Find all IPs
                ips = re.findall(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
                for ip in ips:
                    if not ip.startswith('127.'):  # Skip localhost
                        potential_hosts.append(ip)
                        # Also add the theoretical gateway for each subnet
                        parts = ip.split('.')
                        potential_hosts.append(f"{parts[0]}.{parts[1]}.{parts[2]}.1")
        except Exception as e2:
            logger.error(f"Error getting network interfaces: {str(e2)}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_hosts = []
    for host in potential_hosts:
        if host not in seen:
            seen.add(host)
            unique_hosts.append(host)
    
    logger.info(f"Found {len(unique_hosts)} potential hosts to try")
    return unique_hosts

# Test connection to Ollama
async def test_connection():
    # Get the list of potential hosts
    hosts = get_potential_windows_hosts()
    
    # Print all hosts we're going to try
    logger.info(f"Testing connection to Ollama on these hosts: {hosts}")
    
    for host in hosts:
        url = f"http://{host}:11434/api/tags"
        logger.info(f"Trying to connect to: {url}")
        
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ SUCCESS! Connected to {url}, status: {response.status_code}")
                    models = response.json().get("models", [])
                    logger.info(f"Found {len(models)} models")
                    for model in models:
                        logger.info(f"  - {model.get('name')}")
                    
                    logger.info("\n*** USE THIS HOST IN YOUR CONFIGURATION: ***")
                    logger.info(f"WINDOWS_HOST={host}")
                    return host
                else:
                    logger.info(f"❌ Got response from {url} but status code was {response.status_code}")
                
        except Exception as e:
            logger.info(f"❌ Failed to connect to {url}: {str(e)}")
    
    logger.error("Failed to connect to Ollama on any host")
    return None

# Try to see if Ollama port is open using a raw socket
def check_port_open(host, port=11434):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            if result == 0:
                logger.info(f"✅ Port {port} is OPEN on host {host}")
                return True
            else:
                logger.info(f"❌ Port {port} is CLOSED on host {host}")
                return False
    except Exception as e:
        logger.info(f"❌ Error checking port {port} on host {host}: {str(e)}")
        return False

async def main():
    logger.info("Testing connection to Ollama from WSL...")
    
    # First try the standard connection test
    host = await test_connection()
    
    if host:
        return host
    
    # If the standard test fails, check if the port is open on any host
    logger.info("\nTrying raw socket connections to see if Ollama port is open...")
    hosts = get_potential_windows_hosts()
    
    open_hosts = []
    for host in hosts:
        if check_port_open(host):
            open_hosts.append(host)
    
    if open_hosts:
        logger.info(f"\nFound {len(open_hosts)} hosts with port 11434 open: {open_hosts}")
        logger.info("The HTTP requests failed but the port is open, suggesting a firewall or network issue.")
    else:
        logger.info("\nNo hosts have port 11434 open.")
        logger.info("Suggestions to fix:")
        logger.info("1. Confirm Ollama is running on Windows (check Task Manager)")
        logger.info("2. Check if Ollama is listening on all interfaces (not just localhost)")
        logger.info("3. Check firewall settings between WSL and Windows")
        logger.info("4. Try adding a firewall rule: 'netsh advfirewall firewall add rule name=\"Ollama\" dir=in action=allow protocol=TCP localport=11434'")
    
    return None

if __name__ == "__main__":
    asyncio.run(main())