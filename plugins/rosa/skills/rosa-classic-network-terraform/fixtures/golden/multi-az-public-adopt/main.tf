locals {
  common_tags = merge(var.common_tags, { "Project" : "demo", "ManagedBy" : "rosa-classic-network-terraform", "NamePrefix" : "demo-multi-classic" })
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = merge(var.common_tags, {
    "Name"    = "demo-multi-classic"
    "Project" = "demo"
  })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags = merge(var.common_tags, {
    "Name" = "demo-multi-classic"
  })
}

resource "aws_subnet" "private_1a" {
  vpc_id                  = aws_vpc.this.id
  availability_zone       = "us-east-1a"
  cidr_block              = "10.0.0.0/20"
  map_public_ip_on_launch = false
  tags = merge(var.common_tags, {
    "Name" = "demo-multi-classic-private-us-east-1a"
  })
}

resource "aws_subnet" "public_1a" {
  vpc_id                  = aws_vpc.this.id
  availability_zone       = "us-east-1a"
  cidr_block              = "10.0.48.0/20"
  map_public_ip_on_launch = true
  tags = merge(var.common_tags, {
    "Name"                   = "demo-multi-classic-public-us-east-1a"
    "kubernetes.io/role/elb" = "1"
  })
}

resource "aws_subnet" "private_1b" {
  vpc_id                  = aws_vpc.this.id
  availability_zone       = "us-east-1b"
  cidr_block              = "10.0.16.0/20"
  map_public_ip_on_launch = false
  tags = merge(var.common_tags, {
    "Name" = "demo-multi-classic-private-us-east-1b"
  })
}

resource "aws_subnet" "public_1b" {
  vpc_id                  = aws_vpc.this.id
  availability_zone       = "us-east-1b"
  cidr_block              = "10.0.64.0/20"
  map_public_ip_on_launch = true
  tags = merge(var.common_tags, {
    "Name"                   = "demo-multi-classic-public-us-east-1b"
    "kubernetes.io/role/elb" = "1"
  })
}

resource "aws_subnet" "private_1c" {
  vpc_id                  = aws_vpc.this.id
  availability_zone       = "us-east-1c"
  cidr_block              = "10.0.32.0/20"
  map_public_ip_on_launch = false
  tags = merge(var.common_tags, {
    "Name" = "demo-multi-classic-private-us-east-1c"
  })
}

resource "aws_subnet" "public_1c" {
  vpc_id                  = aws_vpc.this.id
  availability_zone       = "us-east-1c"
  cidr_block              = "10.0.80.0/20"
  map_public_ip_on_launch = true
  tags = merge(var.common_tags, {
    "Name"                   = "demo-multi-classic-public-us-east-1c"
    "kubernetes.io/role/elb" = "1"
  })
}

resource "aws_eip" "nat_1" {
  domain = "vpc"
  tags   = var.common_tags
}

resource "aws_nat_gateway" "nat_1" {
  allocation_id = aws_eip.nat_1.id
  subnet_id     = aws_subnet.public_1a.id
  tags          = var.common_tags
}

resource "aws_eip" "nat_2" {
  domain = "vpc"
  tags   = var.common_tags
}

resource "aws_nat_gateway" "nat_2" {
  allocation_id = aws_eip.nat_2.id
  subnet_id     = aws_subnet.public_1b.id
  tags          = var.common_tags
}

resource "aws_eip" "nat_3" {
  domain = "vpc"
  tags   = var.common_tags
}

resource "aws_nat_gateway" "nat_3" {
  allocation_id = aws_eip.nat_3.id
  subnet_id     = aws_subnet.public_1c.id
  tags          = var.common_tags
}

resource "aws_route_table" "rt_public_us_east_1a" {
  vpc_id = aws_vpc.this.id
  tags = merge(var.common_tags, {
    "Name" = "demo-multi-classic-public-us-east-1a"
  })
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_route" "route_public_us_east_1a" {
  route_table_id         = aws_route_table.rt_public_us_east_1a.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "assoc_public_us_east_1a" {
  subnet_id      = aws_subnet.public_1a.id
  route_table_id = aws_route_table.rt_public_us_east_1a.id
}

resource "aws_route_table" "rt_public_us_east_1b" {
  vpc_id = aws_vpc.this.id
  tags = merge(var.common_tags, {
    "Name" = "demo-multi-classic-public-us-east-1b"
  })
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_route" "route_public_us_east_1b" {
  route_table_id         = aws_route_table.rt_public_us_east_1b.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "assoc_public_us_east_1b" {
  subnet_id      = aws_subnet.public_1b.id
  route_table_id = aws_route_table.rt_public_us_east_1b.id
}

resource "aws_route_table" "rt_public_us_east_1c" {
  vpc_id = aws_vpc.this.id
  tags = merge(var.common_tags, {
    "Name" = "demo-multi-classic-public-us-east-1c"
  })
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_route" "route_public_us_east_1c" {
  route_table_id         = aws_route_table.rt_public_us_east_1c.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "assoc_public_us_east_1c" {
  subnet_id      = aws_subnet.public_1c.id
  route_table_id = aws_route_table.rt_public_us_east_1c.id
}

resource "aws_route_table" "rt_private_us_east_1a" {
  vpc_id = aws_vpc.this.id
  tags = merge(var.common_tags, {
    "Name" = "demo-multi-classic-private-us-east-1a"
  })
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_route" "route_private_us_east_1a" {
  route_table_id         = aws_route_table.rt_private_us_east_1a.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat_1.id
}

resource "aws_route_table_association" "assoc_private_us_east_1a" {
  subnet_id      = aws_subnet.private_1a.id
  route_table_id = aws_route_table.rt_private_us_east_1a.id
}

resource "aws_route_table" "rt_private_us_east_1b" {
  vpc_id = aws_vpc.this.id
  tags = merge(var.common_tags, {
    "Name" = "demo-multi-classic-private-us-east-1b"
  })
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_route" "route_private_us_east_1b" {
  route_table_id         = aws_route_table.rt_private_us_east_1b.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat_2.id
}

resource "aws_route_table_association" "assoc_private_us_east_1b" {
  subnet_id      = aws_subnet.private_1b.id
  route_table_id = aws_route_table.rt_private_us_east_1b.id
}

resource "aws_route_table" "rt_private_us_east_1c" {
  vpc_id = aws_vpc.this.id
  tags = merge(var.common_tags, {
    "Name" = "demo-multi-classic-private-us-east-1c"
  })
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_route" "route_private_us_east_1c" {
  route_table_id         = aws_route_table.rt_private_us_east_1c.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat_3.id
}

resource "aws_route_table_association" "assoc_private_us_east_1c" {
  subnet_id      = aws_subnet.private_1c.id
  route_table_id = aws_route_table.rt_private_us_east_1c.id
}
