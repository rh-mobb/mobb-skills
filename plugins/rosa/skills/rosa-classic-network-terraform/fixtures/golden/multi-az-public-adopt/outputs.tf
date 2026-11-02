output "vpc_id" {
  value = aws_vpc.this.id
}

output "vpc_cidr" {
  value = aws_vpc.this.cidr_block
}

output "aws_subnet_ids" {
  description = "Subnet IDs in ROSA HCP order (private per AZ, then public per AZ when not private)."
  value       = ["subnet-private-a", "subnet-private-b", "subnet-private-c", "subnet-public-a", "subnet-public-b", "subnet-public-c"]
}

output "private_subnet_ids_by_az" {
  value = {
    "us-east-1a" = "subnet-private-a"
    "us-east-1b" = "subnet-private-b"
    "us-east-1c" = "subnet-private-c"
  }
}
