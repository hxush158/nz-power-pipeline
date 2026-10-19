# Terraform (Azure)

Manages the resource group, the ADLS Gen2 storage account, the `raw` and `tfstate`
containers, and a monthly subscription budget with email alerts.

State is stored remotely in the `tfstate` container (see `backend.tf`).
Nothing secret is committed: the subscription ID and the alert email come from
environment variables.

```bash
az login
export TF_VAR_subscription_id="<subscription id>"
export ARM_SUBSCRIPTION_ID="$TF_VAR_subscription_id"
export TF_VAR_alert_email="<your email>"

terraform -chdir=terraform init
terraform -chdir=terraform plan
terraform -chdir=terraform apply   # review the plan, then type yes
```

`prevent_destroy` is set on the resource group, storage account and state container.
