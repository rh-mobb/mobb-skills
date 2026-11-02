import {
  to = aws_vpc.this
  id = "vpc-fixture001"
}

import {
  to = aws_internet_gateway.this
  id = "igw-fixture001"
}

import {
  to = aws_subnet.private_1a
  id = "subnet-private-a"
}

import {
  to = aws_subnet.public_1a
  id = "subnet-public-a"
}

import {
  to = aws_subnet.private_1b
  id = "subnet-private-b"
}

import {
  to = aws_subnet.public_1b
  id = "subnet-public-b"
}

import {
  to = aws_subnet.private_1c
  id = "subnet-private-c"
}

import {
  to = aws_subnet.public_1c
  id = "subnet-public-c"
}

import {
  to = aws_eip.nat_1
  id = "eipalloc-fixture-a"
}

import {
  to = aws_nat_gateway.nat_1
  id = "nat-fixture-a"
}

import {
  to = aws_eip.nat_2
  id = "eipalloc-fixture-b"
}

import {
  to = aws_nat_gateway.nat_2
  id = "nat-fixture-b"
}

import {
  to = aws_eip.nat_3
  id = "eipalloc-fixture-c"
}

import {
  to = aws_nat_gateway.nat_3
  id = "nat-fixture-c"
}

import {
  to = aws_route_table.rt_public_us_east_1a
  id = "rtb-public-a"
}

import {
  to = aws_route.route_public_us_east_1a
  id = "rtb-public-a_0.0.0.0/0"
}

import {
  to = aws_route_table_association.assoc_public_us_east_1a
  id = "subnet-public-a/rtb-public-a"
}

import {
  to = aws_route_table.rt_public_us_east_1b
  id = "rtb-public-b"
}

import {
  to = aws_route.route_public_us_east_1b
  id = "rtb-public-b_0.0.0.0/0"
}

import {
  to = aws_route_table_association.assoc_public_us_east_1b
  id = "subnet-public-b/rtb-public-b"
}

import {
  to = aws_route_table.rt_public_us_east_1c
  id = "rtb-public-c"
}

import {
  to = aws_route.route_public_us_east_1c
  id = "rtb-public-c_0.0.0.0/0"
}

import {
  to = aws_route_table_association.assoc_public_us_east_1c
  id = "subnet-public-c/rtb-public-c"
}

import {
  to = aws_route_table.rt_private_us_east_1a
  id = "rtb-private-a"
}

import {
  to = aws_route.route_private_us_east_1a
  id = "rtb-private-a_0.0.0.0/0"
}

import {
  to = aws_route_table_association.assoc_private_us_east_1a
  id = "subnet-private-a/rtb-private-a"
}

import {
  to = aws_route_table.rt_private_us_east_1b
  id = "rtb-private-b"
}

import {
  to = aws_route.route_private_us_east_1b
  id = "rtb-private-b_0.0.0.0/0"
}

import {
  to = aws_route_table_association.assoc_private_us_east_1b
  id = "subnet-private-b/rtb-private-b"
}

import {
  to = aws_route_table.rt_private_us_east_1c
  id = "rtb-private-c"
}

import {
  to = aws_route.route_private_us_east_1c
  id = "rtb-private-c_0.0.0.0/0"
}

import {
  to = aws_route_table_association.assoc_private_us_east_1c
  id = "subnet-private-c/rtb-private-c"
}

