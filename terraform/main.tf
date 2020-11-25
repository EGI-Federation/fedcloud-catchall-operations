# Security groups
resource "openstack_compute_secgroup_v2" "ssh" {
  name        = "ssh"
  description = "ssh connection"

  rule {
    from_port   = 22
    to_port     = 22
    ip_protocol = "tcp"
    cidr        = "0.0.0.0/0"
  }
}

resource "openstack_networking_floatingip_v2" "public_ip" {
  pool = "external"
}

resource "openstack_compute_instance_v2" "cloud-info" {
  name            = "cloud-info"
  image_id        = "0a3d51ae-56e9-4492-ba7f-0163ce3f0708"
  flavor_id       = 3
  security_groups = ["default", "ssh"]
  user_data       = file("cloud-init.yaml")
  network {
    uuid = "d6ffdfa7-dcf0-4166-95b4-15db27f8b152"
  }
}

resource "openstack_compute_floatingip_associate_v2" "fip" {
  floating_ip = openstack_networking_floatingip_v2.public_ip.address
  instance_id = openstack_compute_instance_v2.cloud-info.id
}

output "floating_ip" {
  value = openstack_networking_floatingip_v2.public_ip.address
}
