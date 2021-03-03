#!/usr/bin/env bash

# Modify ossec.conf
python3 /scripts/xml_parser.py /var/ossec/etc/ossec.conf /scripts/xml_templates/ossec.conf
if [ $3  == "4.x" ]; then
  python3 /scripts/xml_parser.py /var/ossec/etc/ossec.conf /scripts/xml_templates/ossec_4.x.conf
fi

sed -i "s:<address>MANAGER_IP</address>:<address>$1</address>:g" /var/ossec/etc/ossec.conf
sed -n "/$2 /p" /var/ossec/etc/test.keys > /var/ossec/etc/client.keys
chown root:wazuh /var/ossec/etc/client.keys
rm /var/ossec/etc/test.keys

# Agent configuration
for sh_file in /configuration_files/*.sh; do
  . $sh_file
done

if [ $3  == "4.x" ]; then
  /var/ossec/bin/wazuh-control start
else
  /var/ossec/bin/ossec-control start
fi

tail -f /var/ossec/logs/ossec.log
