resource "openstack_networking_secgroup_v2" "motley" {
  name                 = "motley"
  description          = "Open ports for motley-cue"
  delete_default_rules = "true"
}

resource "openstack_networking_secgroup_rule_v2" "motley-8080" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 8080
  port_range_max    = 8080
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = openstack_networking_secgroup_v2.motley.id
}

resource "openstack_compute_instance_v2" "cloud-info" {
  name            = "cloud-info"
  image_id        = var.image_id
  flavor_id       = var.flavor_id
  security_groups = ["default", "motley"]
  user_data       = file("cloud-init.yaml")
  network {
    uuid = var.net_id
  }
}

output "instance-id" {
  value = openstack_compute_instance_v2.cloud-info.id
}
