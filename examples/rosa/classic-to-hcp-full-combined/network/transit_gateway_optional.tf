# Optional Transit Gateway wiring — Classic pattern reference only.
# The TGW itself and many route table updates are usually owned by a central network team.
# Coordinate before uncommenting: attachment approval, propagation, and return paths.
#
# Classic VPC reference:
#   vpc-036a76adeadc2472f (10.0.0.0/16)

# --- TGW VPC attachment (Classic: tgw-attach-0f00b9ab0f38cbbe4) ---
# resource "aws_ec2_transit_gateway_vpc_attachment" "hcp" {
#   transit_gateway_id = "tgw-07a873ec2b3106719"
#   vpc_id             = aws_vpc.this.id
#   subnet_ids         = [aws_subnet.private_2a.id, aws_subnet.private_2b.id, aws_subnet.private_2c.id]
#   dns_support        = "enable"
#   ipv6_support       = "disable"
#   tags = {
#     Name = "demo-classic-tgw-attachment"
#   }
# }

# --- VPC routes via TGW (mirror on each affected route table) ---
# Classic example route table: rtb-0e359c950e993e3d9 → 10.1.0.0/16 via tgw-07a873ec2b3106719
# resource "aws_route" "tgw_1" {
#   route_table_id         = aws_route_table.rt_private_a.id  # repeat per private RT / AZ
#   destination_cidr_block = "10.1.0.0/16"
#   transit_gateway_id     = "tgw-07a873ec2b3106719"
# }

# TGW *route table* entries (hub side) are not in this VPC stack — network team only.
