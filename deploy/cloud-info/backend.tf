# This is where the info about the deployment is to be stored
terraform {
  backend "s3" {
    bucket = "fedcloud-catchall-ops"
    endpoints = {
      s3 = "https://object-store.brno.openstack.cloud.e-infra.cz/"
    }
    key = "cloud-info.tfstate" # Name of the tfstate file
    # settings to make this work in a non AWS endpoint
    region                      = "main"
    skip_region_validation      = true
    skip_credentials_validation = true
    skip_requesting_account_id  = true
    skip_metadata_api_check     = true
    use_path_style              = true
  }
}

# The provider where the deployment is actually performed
provider "openstack" {
  cloud = "deploy"
}
