#!/bin/bash
set -e

echo "=== VPN Provisioning Agent Setup ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo)"
    exit 1
fi

# Create system user
echo "Creating vpnprov user..."
if ! id -u vpnprov > /dev/null 2>&1; then
    useradd -r -s /bin/bash -m -d /opt/vpn-agent vpnprov
    echo "User vpnprov created"
else
    echo "User vpnprov already exists"
fi

# Install dependencies
echo "Installing Python and dependencies..."
apt-get update
apt-get install -y python3 python3-venv python3-pip

# Create directory structure
echo "Setting up directories..."
mkdir -p /opt/vpn-agent
mkdir -p /etc/vpn-agent

# Copy files
echo "Copying application files..."
cp -r app /opt/vpn-agent/
cp requirements.txt /opt/vpn-agent/
cp .env.example /opt/vpn-agent/.env

# Create virtual environment
echo "Creating Python virtual environment..."
cd /opt/vpn-agent
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Generate self-signed SSL certificate
echo "Generating SSL certificate..."
openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout /etc/vpn-agent/key.pem \
    -out /etc/vpn-agent/cert.pem \
    -days 365 \
    -subj "/CN=vpn-agent"

# Set permissions
echo "Setting permissions..."
chown -R vpnprov:vpnprov /opt/vpn-agent
chown -R vpnprov:vpnprov /etc/vpn-agent
chmod 600 /opt/vpn-agent/.env
chmod 600 /etc/vpn-agent/key.pem

# Configure sudoers for sacli
echo "Configuring sudoers..."
cat > /etc/sudoers.d/vpnprov << 'EOF'
# Allow vpnprov to run sacli commands without password
vpnprov ALL=(ALL) NOPASSWD: /usr/local/openvpn_as/scripts/sacli --user * UserPropPut *
vpnprov ALL=(ALL) NOPASSWD: /usr/local/openvpn_as/scripts/sacli --user * SetLocalPassword *
vpnprov ALL=(ALL) NOPASSWD: /usr/local/openvpn_as/scripts/sacli --user * AddProfileToken
vpnprov ALL=(ALL) NOPASSWD: /usr/local/openvpn_as/scripts/sacli --user * GetUserlogin
EOF

chmod 0440 /etc/sudoers.d/vpnprov
visudo -c

# Install systemd service
echo "Installing systemd service..."
cp vpn-agent.service /etc/systemd/system/
systemctl daemon-reload

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit /opt/vpn-agent/.env with your configuration:"
echo "   - Set API_KEY to a secure random string"
echo "   - Set ALLOWED_IPS to your bot server IP"
echo "   - Update ADMIN_UI_URL to your VPN server's public IP"
echo ""
echo "2. Start the service:"
echo "   systemctl start vpn-agent"
echo "   systemctl enable vpn-agent"
echo ""
echo "3. Check status:"
echo "   systemctl status vpn-agent"
echo "   journalctl -u vpn-agent -f"
echo ""
echo "4. Test the health endpoint:"
echo "   curl -k -H 'X-API-Key: YOUR_API_KEY' https://localhost:8443/health"
echo ""
