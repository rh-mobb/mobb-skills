# Optional Classic IdPs — uncomment and complete secrets after coordinating with the provider.
# OAuth redirect (public cluster):
#   https://oauth-openshift.apps.<apps-domain>/oauth2callback/<idp-name>
# Replace <apps-domain> once the HCP cluster exists (rosa describe cluster / console URL).

# Merge into module.roa_hcp identity_providers or var.identity_providers, e.g.:
# identity_providers = merge(var.identity_providers, { ... })

# --- corp-oidc (openid) ---
# corp_oidc = {
#   name         = "corp-oidc"
#   idp_type     = "openid"
#   mapping_method = "claim"
#   openid_idp_issuer = "https://login.example.com/oauth2/default"
#   openid_idp_client_id = "rosa-classic-client-id"
#   openid_idp_client_secret = "<from IdP admin / vault>"
#   openid_idp_claims_email = ["email"]
#   openid_idp_claims_preferred_username = ["preferred_username"]
#   openid_idp_claims_groups = ["groups"]
# }

# --- github-org (github) ---
# github_org = {
#   name         = "github-org"
#   idp_type     = "github"
#   mapping_method = "claim"
#   github_idp_client_id = "Iv1.abcdef123456"
#   github_idp_client_secret = "<from GitHub OAuth app>"
#   github_idp_hostname = "github.com"
# }

