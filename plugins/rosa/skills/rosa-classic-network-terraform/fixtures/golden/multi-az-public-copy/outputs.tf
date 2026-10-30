output "vpc_id" {
  value = aws_vpc.this.id
}

output "vpc_cidr" {
  value = aws_vpc.this.cidr_block
}

output "aws_subnet_ids" {
  description = "Subnet IDs in ROSA HCP order (private per AZ, then public per AZ when not private)."
  value       = concat([aws_subnet.private_1a.id, aws_subnet.private_1b.id, aws_subnet.private_1c.id], [aws_subnet.public_1a.id, aws_subnet.public_1b.id, aws_subnet.public_1c.id])
}

output "private_subnet_ids_by_az" {
  value = {
    "us-east-1a" = aws_subnet.private_1a.id
    "us-east-1b" = aws_subnet.private_1b.id
    "us-east-1c" = aws_subnet.private_1c.id
  }
}
