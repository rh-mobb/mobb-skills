output "vpc_id" {
  value = aws_vpc.this.id
}

output "vpc_cidr" {
  value = aws_vpc.this.cidr_block
}

output "aws_subnet_ids" {
  description = "Subnet IDs in ROSA HCP order (private per AZ, then public per AZ when not private)."
  value       = ["subnet-0aaa1111private2a", "subnet-0bbb2222public2a"]
}

output "private_subnet_ids_by_az" {
  value = {
    "ap-southeast-2a" = "subnet-0aaa1111private2a"
  }
}
