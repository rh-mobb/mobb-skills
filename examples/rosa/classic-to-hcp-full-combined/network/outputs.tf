output "vpc_id" {
  value = aws_vpc.this.id
}

output "vpc_cidr" {
  value = aws_vpc.this.cidr_block
}

output "aws_subnet_ids" {
  description = "Subnet IDs in ROSA HCP order (private per AZ, then public per AZ when not private)."
  value       = concat([aws_subnet.private_2a.id, aws_subnet.private_2b.id, aws_subnet.private_2c.id], [aws_subnet.public_2a.id, aws_subnet.public_2b.id, aws_subnet.public_2c.id])
}

output "private_subnet_ids_by_az" {
  value = {
    "ap-southeast-2a" = aws_subnet.private_2a.id
    "ap-southeast-2b" = aws_subnet.private_2b.id
    "ap-southeast-2c" = aws_subnet.private_2c.id
  }
}
