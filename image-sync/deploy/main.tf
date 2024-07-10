resource "openstack_blockstorage_volume_v3" "image-cache" {
  name = "image-cache"
  size = 200
}

resource "openstack_compute_instance_v2" "image-sync" {
  name            = "image-sync"
  image_id        = var.image_id
  flavor_id       = var.flavor_id
  security_groups = ["default"]
  user_data       = file("cloud-init.yaml")
  network {
    uuid = var.net_id
  }
}

resource "openstack_compute_volume_attach_v2" "attached" {
  instance_id = openstack_compute_instance_v2.image-sync.id
  volume_id   = openstack_blockstorage_volume_v3.image-cache.id
}



output "instance-id" {
  value = openstack_compute_instance_v2.image-sync.id
}
