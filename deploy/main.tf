resource "openstack_compute_instance_v2" "cloud-info" {
  name            = "cloud-info"
  image_id        = var.image_id
  flavor_id       = var.flavor_id
  security_groups = ["default"]
  user_data       = file("cloud-init.yaml")
  network {
    uuid = var.net_id
  }
}

output "instance-id" {
  value = openstack_compute_instance_v2.cloud-info.id
}
