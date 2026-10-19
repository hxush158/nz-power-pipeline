# 远程状态：存放在 Azure 存储账号的 tfstate 容器里。
# 后端配置里不能用变量；下面都是资源名，不是机密，可以提交。
# 认证不写在这里：用 `az login` 的身份，Terraform 自己去取存储账号的访问密钥。
# 订阅 ID 通过环境变量 ARM_SUBSCRIPTION_ID 提供（见 README）。
terraform {
  backend "azurerm" {
    resource_group_name  = "rg_nz_power"
    storage_account_name = "nzpowerhxu"
    container_name       = "tfstate"
    key                  = "nz-power.tfstate"
  }
}
