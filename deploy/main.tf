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

resource "openstack_compute_instance_v2" "cloud-info" {
  name            = "cloud-info"
  image_id        = var.image_id
  flavor_id       = var.flavor_id
  security_groups = ["default", "ssh"]
  user_data       = file("cloud-init.yaml")
  network {
    uuid = var.net_id
  }
}
