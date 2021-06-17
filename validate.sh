#!/bin/sh

goc_method="https://goc.egi.eu/gocdbpi/public/?method=get_service_endpoint"

exit_value=0

for f in sites/*.yaml; do
     goc_site=$(grep "^gocdb:" $f | cut -f2 -d":" | tr -d [:space:])
     endpoint=$(grep "^endpoint:" $f | cut -f2- -d":" | tr -d [:space:])
     curl -s "$goc_method&sitename=$goc_site&service_type=org.openstack.nova" > /tmp/site-$goc_site.xml
     grep -q "<SITENAME>$goc_site</SITENAME>" /tmp/site-$goc_site.xml 
     if [ $? -ne 0 ]; then
	echo "Site $goc_site not found in GOC"
	exit_value=1
	continue
     fi
     grep -q "<URL>$endpoint</URL>" /tmp/site-$goc_site.xml 
     if [ $? -ne 0 ]; then
	echo "Endpoint URL $endpoint for $goc_site not in GOC!"
	exit_value=1
     fi
done

exit $exit_value

