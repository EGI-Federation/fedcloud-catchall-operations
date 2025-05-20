# This is where the info about the deployment is to be stored
terraform {
  backend "swift" {
    container = "terraform-image-sync"
    cloud     = "backend"
  }
}

# The provider where the deployment is actually performed
provider "openstack" {
  cloud = "deploy"
}
