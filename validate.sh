#!/bin/sh

goc_method="https://goc.egi.eu/gocdbpi/public/?method=get_service_endpoint"

exit_value=0

# Get all VOs names
VO_LIST=$(mktemp)
curl "http://cclavoisier01.in2p3.fr:8080/lavoisier/VoList?accept=json" | jq -r ".data[].name" > "$VO_LIST"

for f in sites/*.yaml
do
    goc_site=$(grep "^gocdb:" "$f" | cut -f2 -d":" | tr -d "[:space:]")
    endpoint=$(grep "^endpoint:" "$f" | cut -f2- -d":" | tr -d "[:space:]")
    echo "Searching for endpoint $endpoint in $goc_site site ($f)"
    GOC_SITE_FILE=$(mktemp)
    curl -s "$goc_method&sitename=$goc_site&service_type=org.openstack.nova" > "$GOC_SITE_FILE"
    if ! grep -q "<SITENAME>$goc_site</SITENAME>" "$GOC_SITE_FILE"
    then
        echo "\033[0;31m[ERROR] Site $goc_site not found in GOC\033[0m"
        exit_value=1
        continue
    fi
    if ! grep -q "<URL>$endpoint</URL>" "$GOC_SITE_FILE"
    then
        echo "\033[0;31m[ERROR] URL $endpoint for $goc_site not found in GOC\033[0m"
        exit_value=1
    else
        echo "\033[0;32m[OK]\033[0m"
     fi
    # check if all VOs configured do exist
    # Try to use FQAN
    # So the VO that comes from the file, it will be either:
    # - just the name of the VO
    # - /<name of the VO>/some more extra/
    # - /VO=<name of the VO>/some more stuff/
    for vo in $(yq -r ".vos[].name" < "$f" | cut -f2 -d"/" | sed "s/^VO=//")
    do
        if ! grep -q "^$vo\$" "$VO_LIST"
        then
            echo "\033[0;31m[ERROR] VO $vo not found in ops portal\033[0m"
            exit_value=1
        fi
    done
    rm "$GOC_SITE_FILE"
done

rm "$VO_LIST"

exit $exit_value

