import hashlib
import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ["MOLECULE_INVENTORY_FILE"]
).get_hosts("all")


def test_site_files(host):
    endpoint_hash = hashlib.md5(b"https://example.com:5000/v3/").hexdigest()
    filename = "foo-bar-%s" % endpoint_hash
    assert host.file("/etc/egi/cloud-info/").is_directory
    assert host.file("/etc/egi/cloud-info/%s.yaml" % filename).exists
    assert not host.file("/etc/egi/cloud-info/%s.env" % filename).contains("OS_REGION")
    assert host.file("/etc/egi/cloud-info/%s.env" % filename).exists
    assert host.file("/etc/cron.d/cloud-info-%s" % filename).exists
    assert host.file("/etc/cron.d/egi-image-sync").exists


def test_site_files_region(host):
    endpoint_hash = hashlib.md5(b"https://site.org:5000/v3/").hexdigest()
    filename = "bar-foo-%s" % endpoint_hash
    assert host.file("/etc/egi/cloud-info/").is_directory
    assert host.file("/etc/egi/cloud-info/%s.yaml" % filename).exists
    assert host.file("/etc/egi/cloud-info/%s.env" % filename).exists
    assert host.file("/etc/egi/cloud-info/%s.env" % filename).contains(
        "OS_REGION=region1"
    )
    assert host.file("/etc/cron.d/cloud-info-%s" % filename).exists
