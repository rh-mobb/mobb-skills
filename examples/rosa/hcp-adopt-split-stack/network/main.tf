locals {
  common_tags = merge(var.common_tags, {"Project": "demo-workshop", "ManagedBy": "rosa-classic-network-terraform", "NamePrefix": "demo-hcp-public"})
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = merge(var.common_tags, {
    "Act" = "3"
    "ManagedBy" = "Terraform"
    "Name" = "demo-hcp-public-vpc"
    "Project" = "demo-workshop"
  })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = merge(var.common_tags, {
    "Act" = "3"
    "ManagedBy" = "Terraform"
    "Name" = "demo-hcp-public-igw"
    "Project" = "demo-workshop"
  })
}

resource "aws_subnet" "private_2a" {
  vpc_id                  = aws_vpc.this.id
  availability_zone       = "ap-southeast-2a"
  cidr_block              = "10.2.0.0/17"
  map_public_ip_on_launch = false
  tags = merge(var.common_tags, {
    "Act" = "3"
    "ManagedBy" = "Terraform"
    "Name" = "demo-hcp-public-private-ap-southeast-2a"
    "Project" = "demo-workshop"
    "Type" = "private"
    "kubernetes.io/cluster/01234567-89ab-cdef-0123-456789abcd01" = "shared"
    "kubernetes.io/role/internal-elb" = "1"
  })
}

resource "aws_subnet" "public_2a" {
  vpc_id                  = aws_vpc.this.id
  availability_zone       = "ap-southeast-2a"
  cidr_block              = "10.2.128.0/17"
  map_public_ip_on_launch = true
  tags = merge(var.common_tags, {
    "Act" = "3"
    "ManagedBy" = "Terraform"
    "Name" = "demo-hcp-public-public-ap-southeast-2a"
    "Project" = "demo-workshop"
    "Type" = "public"
    "kubernetes.io/cluster/01234567-89ab-cdef-0123-456789abcd01" = "shared"
    "kubernetes.io/role/elb" = "1"
  })
}

resource "aws_eip" "nat_1" {
  domain = "vpc"
  tags   = merge(var.common_tags, {
    "Act" = "3"
    "ManagedBy" = "Terraform"
    "Name" = "demo-hcp-public-nat-ap-southeast-2a"
    "Project" = "demo-workshop"
  })
}

resource "aws_nat_gateway" "nat_1" {
  allocation_id = aws_eip.nat_1.id
  subnet_id     = aws_subnet.public_2a.id
  tags          = merge(var.common_tags, {
    "Act" = "3"
    "ManagedBy" = "Terraform"
    "Name" = "demo-hcp-public-nat-ap-southeast-2a"
    "Project" = "demo-workshop"
  })
}

resource "aws_route_table" "rt_public_ap_southeast_2a" {
  vpc_id = aws_vpc.this.id
  tags = merge(var.common_tags, {
    "Act" = "3"
    "ManagedBy" = "Terraform"
    "Name" = "demo-hcp-public-public-rt"
    "Project" = "demo-workshop"
  })
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_route" "route_public_ap_southeast_2a" {
  route_table_id         = aws_route_table.rt_public_ap_southeast_2a.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "assoc_public_ap_southeast_2a" {
  subnet_id      = aws_subnet.public_2a.id
  route_table_id = aws_route_table.rt_public_ap_southeast_2a.id
}

resource "aws_route_table" "rt_private_ap_southeast_2a" {
  vpc_id = aws_vpc.this.id
  tags = merge(var.common_tags, {
    "Act" = "3"
    "ManagedBy" = "Terraform"
    "Name" = "demo-hcp-public-private-rt-ap-southeast-2a"
    "Project" = "demo-workshop"
  })
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_route" "route_private_ap_southeast_2a" {
  route_table_id         = aws_route_table.rt_private_ap_southeast_2a.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat_1.id
}

resource "aws_route_table_association" "assoc_private_ap_southeast_2a" {
  subnet_id      = aws_subnet.private_2a.id
  route_table_id = aws_route_table.rt_private_ap_southeast_2a.id
}
