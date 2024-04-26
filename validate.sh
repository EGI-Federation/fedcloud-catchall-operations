#!/bin/sh

goc_method="https://goc.egi.eu/gocdbpi/public/?method=get_service_endpoint"

exit_value=0

# Get all VOs names
VO_LIST=$(mktemp)
curl --silent "http://cclavoisier01.in2p3.fr:8080/lavoisier/VoList?accept=json" |
	jq -r ".data[].name" >"$VO_LIST"

# Get fedcloudclient sites
FEDCLOUD_CLI_SITES=$(mktemp)
curl "https://raw.githubusercontent.com/tdviet/fedcloudclient/master/config/sites.yaml" \
	>"$FEDCLOUD_CLI_SITES"

# Temp file for nova endpoint
NOVA_ENDPOINT=$(mktemp)

for f in sites/*.yaml; do
	goc_site=$(grep "^gocdb:" "$f" | cut -f2 -d":" | tr -d "[:space:]")
	endpoint=$(grep "^endpoint:" "$f" | cut -f2- -d":" | tr -d "[:space:]")
	printf "Searching for endpoint %s in %s site (%s)\n" \
		"$endpoint" "$goc_site" "$f"
	curl --silent "$goc_method&sitename=$goc_site&service_type=org.openstack.nova" \
		>"$NOVA_ENDPOINT"
	if ! grep -q "<SITENAME>$goc_site</SITENAME>" "$NOVA_ENDPOINT"; then
		printf "\033[0;31m[ERROR] Site %s not found in GOC\033[0m\n" "$goc_site"
		exit_value=1
		continue
	fi
	if ! grep -q "<URL>$endpoint</URL>" "$NOVA_ENDPOINT"; then
		printf "\033[0;31m[ERROR] URL %s for %s not found in GOC\033[0m\n" \
			"$endpoint" "$goc_site"
		exit_value=1
	else
		printf "\033[0;32m[OK]\033[0m\n"
	fi
	# check if all VOs configured do exist
	# Try to use FQAN
	# So the VO that comes from the file, it will be either:
	# - just the name of the VO
	# - /<name of the VO>/some more extra/
	# - /VO=<name of the VO>/some more stuff/
	for vo in $(yq -r ".vos[].name" <"$f" | cut -f2 -d"/" | sed "s/^VO=//"); do
		if ! grep -q "^$vo\$" "$VO_LIST"; then
			printf "\033[0;31m[ERROR] VO %s not found in ops portal\033[0m\n" \
				"$vo"
			exit_value=1
		fi
	done

	# check if site is also on:
	# https://github.com/tdviet/fedcloudclient/blob/master/config/sites.yaml
	if ! grep -q "$f" "$FEDCLOUD_CLI_SITES"; then
		printf "\033[0;31m[ERROR] Site %s not found in fedcloudclient\033[0m\n" "$goc_site"
		exit_value=1
	fi
done

for site in $(yq -r '.[]' <"$FEDCLOUD_CLI_SITES"); do
	if ! test -s "sites/$(basename "$site")"; then
		printf "\033[0;31m[ERROR] Site %s not found in fedcloud-catchall-operations\033[0m\n" "$(basename "$site")"
		exit_value=1
	fi
done

# check that the VO mappings are up to date according to ops portal
for vo in $(yq -r '.vos | keys[]' <vo-mappings.yaml | cut -f2 -d"/" | sed "s/^VO=//"); do
	if ! grep -q "^$vo\$" "$VO_LIST"; then
		printf "\033[0;31m[ERROR] VO %s not found in ops portal\033[0m\n" \
			"$vo"
		exit_value=1
	fi
done

rm "$NOVA_ENDPOINT"
rm "$FEDCLOUD_CLI_SITES"
rm "$VO_LIST"

exit $exit_value
