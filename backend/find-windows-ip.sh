#!/bin/bash
# This script attempts to find your Windows IP address from WSL

echo "Finding Windows IP address from WSL..."

# Method 1: Try nameserver from resolv.conf (usually Windows host in WSL2)
echo -n "Checking resolv.conf: "
NAMESERVER=$(grep nameserver /etc/resolv.conf | awk '{print $2}')
echo $NAMESERVER
echo "Testing connection to Ollama using nameserver..."
curl -s -m 2 http://$NAMESERVER:11434/api/tags > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ SUCCESS! Ollama is accessible at http://$NAMESERVER:11434"
    echo "Use this IP in your ollama_client.py: $NAMESERVER"
    exit 0
else
    echo "❌ Failed to connect to Ollama using nameserver"
fi

# Method 2: Try host.docker.internal
echo -n "Checking host.docker.internal: "
ping -c 1 host.docker.internal > /dev/null 2>&1
if [ $? -eq 0 ]; then
    HOST_DOCKER_IP=$(ping -c 1 host.docker.internal | grep PING | awk -F '[()]' '{print $2}')
    echo $HOST_DOCKER_IP
    echo "Testing connection to Ollama using host.docker.internal..."
    curl -s -m 2 http://$HOST_DOCKER_IP:11434/api/tags > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ SUCCESS! Ollama is accessible at http://$HOST_DOCKER_IP:11434"
        echo "Use this IP in your ollama_client.py: $HOST_DOCKER_IP"
        exit 0
    else
        echo "❌ Failed to connect to Ollama using host.docker.internal IP"
    fi
else
    echo "❌ Cannot resolve host.docker.internal"
fi

# Method 3: Check IP route for default gateway
echo -n "Checking default gateway: "
DEFAULT_GW=$(ip route | grep default | awk '{print $3}')
echo $DEFAULT_GW
if [ -n "$DEFAULT_GW" ]; then
    echo "Testing connection to Ollama using default gateway..."
    curl -s -m 2 http://$DEFAULT_GW:11434/api/tags > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ SUCCESS! Ollama is accessible at http://$DEFAULT_GW:11434"
        echo "Use this IP in your ollama_client.py: $DEFAULT_GW"
        exit 0
    else
        echo "❌ Failed to connect to Ollama using default gateway"
    fi
fi

# Method 4: If WSL2, try WSL-specific IP ranges
echo "Checking WSL-specific IP ranges..."
for IP_PREFIX in 172.16 172.17 172.18 172.19 172.20 172.21 172.22 172.23 172.24 172.25; do
    TEST_IP="${IP_PREFIX}.1.1"
    echo -n "Testing $TEST_IP: "
    curl -s -m 1 http://$TEST_IP:11434/api/tags > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ SUCCESS! Ollama is accessible at http://$TEST_IP:11434"
        echo "Use this IP in your ollama_client.py: $TEST_IP"
        exit 0
    else
        echo "❌ Failed"
    fi
done

# Method 5: Display Windows IP from host perspective
echo -e "\nChecking your Windows IP address..."
echo "In Windows, run 'ipconfig' in Command Prompt and look for IPv4 Address"
echo "It usually looks like 192.168.x.x or 10.0.x.x"
echo -e "\nAfter finding your Windows IP address:"
echo "1. Edit ollama_client.py"
echo "2. Replace YOUR_WINDOWS_IP with your actual IP address"
echo "3. Restart your application"