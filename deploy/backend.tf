# This is where the info about the deployment is to be stored
terraform {
  backend "swift" {
    container = "terraform"
    cloud     = "backend"
  }
  required_providers {
    openstack = "~> 1.48"
  }
}

# The provider where the deployment is actually performed
provider "openstack" {
  cloud = "deploy"
}
