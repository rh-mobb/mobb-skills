locals {
  common_tags = merge(var.common_tags, {"Project": "demo-workshop", "ManagedBy": "rosa-classic-network-terraform", "NamePrefix": "demo-classic"})
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = merge(local.common_tags, { Name = var.name_prefix != "" ? var.name_prefix : "rosa-vpc" })
}

resource "aws_subnet" "private_2a" {
  vpc_id                  = aws_vpc.this.id
  availability_zone       = "ap-southeast-2a"
  cidr_block              = "10.1.0.0/20"
  map_public_ip_on_launch = false
  tags = merge(local.common_tags, { Name = "${var.name_prefix}-ap_southeast_2a-private" })
}

resource "aws_subnet" "public_2a" {
  vpc_id                  = aws_vpc.this.id
  availability_zone       = "ap-southeast-2a"
  cidr_block              = "10.1.48.0/20"
  map_public_ip_on_launch = true
  tags = merge(local.common_tags, { Name = "${var.name_prefix}-ap_southeast_2a-public" })
}

resource "aws_subnet" "private_2b" {
  vpc_id                  = aws_vpc.this.id
  availability_zone       = "ap-southeast-2b"
  cidr_block              = "10.1.16.0/20"
  map_public_ip_on_launch = false
  tags = merge(local.common_tags, { Name = "${var.name_prefix}-ap_southeast_2b-private" })
}

resource "aws_subnet" "public_2b" {
  vpc_id                  = aws_vpc.this.id
  availability_zone       = "ap-southeast-2b"
  cidr_block              = "10.1.64.0/20"
  map_public_ip_on_launch = true
  tags = merge(local.common_tags, { Name = "${var.name_prefix}-ap_southeast_2b-public" })
}

resource "aws_subnet" "private_2c" {
  vpc_id                  = aws_vpc.this.id
  availability_zone       = "ap-southeast-2c"
  cidr_block              = "10.1.32.0/20"
  map_public_ip_on_launch = false
  tags = merge(local.common_tags, { Name = "${var.name_prefix}-ap_southeast_2c-private" })
}

resource "aws_subnet" "public_2c" {
  vpc_id                  = aws_vpc.this.id
  availability_zone       = "ap-southeast-2c"
  cidr_block              = "10.1.80.0/20"
  map_public_ip_on_launch = true
  tags = merge(local.common_tags, { Name = "${var.name_prefix}-ap_southeast_2c-public" })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.common_tags, { Name = var.name_prefix })
}

resource "aws_eip" "nat_1" {
  domain = "vpc"
  tags   = merge(local.common_tags, { Name = "${var.name_prefix}-nat-eip-1" })
}

resource "aws_nat_gateway" "nat_1" {
  allocation_id = aws_eip.nat_1.id
  subnet_id     = aws_subnet.public_2b.id
  tags          = merge(local.common_tags, { Name = "${var.name_prefix}-nat-1" })
}

resource "aws_eip" "nat_2" {
  domain = "vpc"
  tags   = merge(local.common_tags, { Name = "${var.name_prefix}-nat-eip-2" })
}

resource "aws_nat_gateway" "nat_2" {
  allocation_id = aws_eip.nat_2.id
  subnet_id     = aws_subnet.public_2c.id
  tags          = merge(local.common_tags, { Name = "${var.name_prefix}-nat-2" })
}

resource "aws_eip" "nat_3" {
  domain = "vpc"
  tags   = merge(local.common_tags, { Name = "${var.name_prefix}-nat-eip-3" })
}

resource "aws_nat_gateway" "nat_3" {
  allocation_id = aws_eip.nat_3.id
  subnet_id     = aws_subnet.public_2a.id
  tags          = merge(local.common_tags, { Name = "${var.name_prefix}-nat-3" })
}

resource "aws_route_table" "rt_public_ap_southeast_2a" {
  vpc_id = aws_vpc.this.id
  tags = merge(local.common_tags, { Name = "${var.name_prefix}-public-ap-southeast-2a" })
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

resource "aws_route_table" "rt_public_ap_southeast_2b" {
  vpc_id = aws_vpc.this.id
  tags = merge(local.common_tags, { Name = "${var.name_prefix}-public-ap-southeast-2b" })
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_route" "route_public_ap_southeast_2b" {
  route_table_id         = aws_route_table.rt_public_ap_southeast_2b.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "assoc_public_ap_southeast_2b" {
  subnet_id      = aws_subnet.public_2b.id
  route_table_id = aws_route_table.rt_public_ap_southeast_2b.id
}

resource "aws_route_table" "rt_public_ap_southeast_2c" {
  vpc_id = aws_vpc.this.id
  tags = merge(local.common_tags, { Name = "${var.name_prefix}-public-ap-southeast-2c" })
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_route" "route_public_ap_southeast_2c" {
  route_table_id         = aws_route_table.rt_public_ap_southeast_2c.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "assoc_public_ap_southeast_2c" {
  subnet_id      = aws_subnet.public_2c.id
  route_table_id = aws_route_table.rt_public_ap_southeast_2c.id
}

resource "aws_route_table" "rt_private_ap_southeast_2a" {
  vpc_id = aws_vpc.this.id
  tags = merge(local.common_tags, { Name = "${var.name_prefix}-private-ap-southeast-2a" })
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_route" "route_private_ap_southeast_2a" {
  route_table_id         = aws_route_table.rt_private_ap_southeast_2a.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat_3.id
}

resource "aws_route_table_association" "assoc_private_ap_southeast_2a" {
  subnet_id      = aws_subnet.private_2a.id
  route_table_id = aws_route_table.rt_private_ap_southeast_2a.id
}

resource "aws_route_table" "rt_private_ap_southeast_2b" {
  vpc_id = aws_vpc.this.id
  tags = merge(local.common_tags, { Name = "${var.name_prefix}-private-ap-southeast-2b" })
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_route" "route_private_ap_southeast_2b" {
  route_table_id         = aws_route_table.rt_private_ap_southeast_2b.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat_1.id
}

resource "aws_route_table_association" "assoc_private_ap_southeast_2b" {
  subnet_id      = aws_subnet.private_2b.id
  route_table_id = aws_route_table.rt_private_ap_southeast_2b.id
}

resource "aws_route_table" "rt_private_ap_southeast_2c" {
  vpc_id = aws_vpc.this.id
  tags = merge(local.common_tags, { Name = "${var.name_prefix}-private-ap-southeast-2c" })
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_route" "route_private_ap_southeast_2c" {
  route_table_id         = aws_route_table.rt_private_ap_southeast_2c.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat_2.id
}

resource "aws_route_table_association" "assoc_private_ap_southeast_2c" {
  subnet_id      = aws_subnet.private_2c.id
  route_table_id = aws_route_table.rt_private_ap_southeast_2c.id
}
