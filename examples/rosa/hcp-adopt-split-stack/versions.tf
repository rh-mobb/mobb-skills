terraform {
  required_version = ">= 1.5.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.51.0"
    }
    rhcs = {
      source  = "terraform-redhat/rhcs"
      version = ">= 1.7.8"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "rhcs" {
  # Set RHCS_TOKEN in the environment (from console.redhat.com/openshift/token).
}
