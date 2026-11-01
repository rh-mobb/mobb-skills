import {
  to = aws_vpc.this
  id = "vpc-0a1b2c3d4e5f67890"
}

import {
  to = aws_internet_gateway.this
  id = "igw-0example00000001"
}

import {
  to = aws_subnet.private_2a
  id = "subnet-0aaa1111private2a"
}

import {
  to = aws_subnet.public_2a
  id = "subnet-0bbb2222public2a"
}

import {
  to = aws_eip.nat_1
  id = "eipalloc-0example00001"
}

import {
  to = aws_nat_gateway.nat_1
  id = "nat-0example00000001"
}

import {
  to = aws_route_table.rt_public_ap_southeast_2a
  id = "rtb-0d6da9f02753e0987"
}

import {
  to = aws_route.route_public_ap_southeast_2a
  id = "rtb-0d6da9f02753e0987_0.0.0.0/0"
}

import {
  to = aws_route_table_association.assoc_public_ap_southeast_2a
  id = "subnet-0bbb2222public2a/rtb-0d6da9f02753e0987"
}

import {
  to = aws_route_table.rt_private_ap_southeast_2a
  id = "rtb-0e291a647d4a71ace"
}

import {
  to = aws_route.route_private_ap_southeast_2a
  id = "rtb-0e291a647d4a71ace_0.0.0.0/0"
}

import {
  to = aws_route_table_association.assoc_private_ap_southeast_2a
  id = "subnet-0aaa1111private2a/rtb-0e291a647d4a71ace"
}

