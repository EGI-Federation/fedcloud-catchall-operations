#!/bin/sh

goc_method="https://goc.egi.eu/gocdbpi/public/?method=get_service_endpoint"

exit_value=0

for f in sites/*.yaml; do
    goc_site=$(grep "^gocdb:" "$f" | cut -f2 -d":" | tr -d "[:space:]")
    endpoint=$(grep "^endpoint:" "$f" | cut -f2- -d":" | tr -d "[:space:]")
    echo "Searching for endpoint $endpoint in $goc_site site ($f)"
    curl -s "$goc_method&sitename=$goc_site&service_type=org.openstack.nova" > "/tmp/site-$goc_site.xml"
    if ! grep -q "<SITENAME>$goc_site</SITENAME>" "/tmp/site-$goc_site.xml";
    then
        echo "\033[0;31m[ERROR] Site $goc_site not found in GOC\033[0m"
        exit_value=1
        continue
    fi
    if ! grep -q "<URL>$endpoint</URL>" "/tmp/site-$goc_site.xml";
    then
        echo "\033[0;31m[ERROR] URL $endpoint for $goc_site not found in GOC\033[0m"
        exit_value=1
    else
        echo "\033[0;32m[OK]\033[0m"
     fi
done

exit $exit_value

