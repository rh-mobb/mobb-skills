# Replicated from Classic (--idps-json). Passwords are new random values.
locals {
  identity_providers_classic = {
    developer = {
      name               = "developer"
      idp_type           = "htpasswd"
      mapping_method     = "claim"
      htpasswd_idp_users = jsonencode([{ username = "dev-user", password = random_password.idp_developer_dev_user.result }, { username = "qa-user", password = random_password.idp_developer_qa_user.result }])
    }
  }
}
